import busio
import statistics
import logging
import config
import threading
import digitalio
import time

log = logging.getLogger(__name__)


class Board(object):
    '''This represents a blinka board where this code
    runs.
    '''

    def __init__(self):
        log.info("board: %s" % (self.name))

        for sensor in self.temp_sensors:
            sensor.start()


class RealBoard(Board):
    '''Each board has a thermocouple board attached to it.
    Any blinka board that supports SPI can be used. The
    board is automatically detected by blinka.
    '''

    def __init__(self):
        self.name = None
        self.load_libs()
        self.temp_sensors = self.choose_tempsensor()
        Board.__init__(self)

    def load_libs(self):
        import board
        self.name = board.board_id

    def choose_tempsensor(self):
        # if config.max31855:
        #     return Max31855()
        # if config.max31856:
        return (Max31856(), Max31855())

    def temperatures(self):
        temps = []
        for sensor in self.temp_sensors:
            temps.append(sensor.get_raw_temperature())
        return temps


class SimulatedBoard(Board):
    '''Simulated board used during simulations.
    See config.simulate
    '''

    def __init__(self):
        self.name = "simulated"
        self.temp_sensors = TempSensorSimulated(), TempSensorSimulated()
        Board.__init__(self)

    def temperatures(self):
        self.temp_sensors[0].simulated_temperature += 1
        temps = []
        for sensor in self.temp_sensors:
            temps.append(sensor.get_temperature())
        return temps


class TempSensor(threading.Thread):
    '''Used by the Board class. Each Board must have
    a TempSensor.
    '''

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.time_step = config.sensor_time_wait
        self.status = ThermocoupleTracker()


class TempSensorSimulated(TempSensor):
    '''Simulates a temperature sensor '''

    def __init__(self):
        TempSensor.__init__(self)

        self.noConnection = False
        self.shortToGround = False
        self.shortToVCC = False
        self.unknownError = False
        self.bad_percent = 7

        self.simulated_temperature = config.sim_t_env

    def get_temperature(self):

        return self.simulated_temperature


class TempSensorReal(TempSensor):
    '''real temperature sensor that takes many measurements
       during the time_step
       inputs
           config.temperature_average_samples
    '''

    def __init__(self):
        TempSensor.__init__(self)
        self.sleeptime = self.time_step / float(config.temperature_average_samples)
        self.temptracker = TempTracker()
        self.spi = busio.SPI(config.spi_sclk, config.spi_mosi, config.spi_miso)
        self.cs = digitalio.DigitalInOut(config.spi_cs)

    def get_raw_temperature(self):
        '''read temp from tc and convert if needed'''
        try:
            temp = self.raw_temp()  # raw_temp provided by subclasses
            if config.temp_scale.lower() == "f":
                temp = (temp * 9 / 5) + 32
            self.status.good()
            return temp
        except ThermocoupleError as tce:
            if tce.ignore:
                log.error("Problem reading temp (ignored) %s" % (tce.message))
                self.status.good()
            else:
                log.error("Problem reading temp %s" % (tce.message))
                self.status.bad()
        return None

    def get_temperature(self):
        '''average temp over a duty cycle'''
        return self.temptracker.get_avg_temp()

    def run(self):
        '''use a moving average of config.temperature_average_samples across the time_step'''
        temps = []
        self.bad_stamp = time.time()
        while True:
            temp = self.get_raw_temperature()
            if temp:
                self.temptracker.add(temp)
            time.sleep(1) # self.sleeptime)

############ Marks stuff, '55 only
            # reset error counter if time is up
            # if (time.time() - self.bad_stamp) > (self.time_step * 2):
            #     if self.bad_count + self.ok_count:
            #         self.bad_percent = (self.bad_count / (self.bad_count + self.ok_count)) * 100
            #     else:
            #         self.bad_percent = 0
            #     self.bad_count = 0
            #     self.ok_count = 0
            #     self.bad_stamp = time.time()
            #
            # temp = self.thermocouple.get()
            # self.noConnection = self.thermocouple.noConnection
            # self.shortToGround = self.thermocouple.shortToGround
            # self.shortToVCC = self.thermocouple.shortToVCC
            # self.unknownError = self.thermocouple.unknownError
            #
            # is_bad_value = self.noConnection | self.unknownError
            # if not config.ignore_tc_short_errors:
            #     is_bad_value |= self.shortToGround | self.shortToVCC
            #
            # if not is_bad_value:
            #     temps.append(temp)
            #     if len(temps) > config.temperature_average_samples:
            #         del temps[0]
            #     self.ok_count += 1
            #
            # else:
            #     log.error("Problem reading temp N/C:%s GND:%s VCC:%s ???:%s" % (
            #     self.noConnection, self.shortToGround, self.shortToVCC, self.unknownError))
            #     self.bad_count += 1
            #
            # if len(temps):
            #     self.temperature = self.get_avg_temp(temps)
            #
            # time.sleep(self.sleeptime)
            #

class TempTracker(object):
    '''creates a sliding window of N temperatures per
       config.sensor_time_wait
    '''

    def __init__(self):
        self.size = config.temperature_average_samples
        self.temps = [0 for i in range(self.size)]

    def add(self, temp):
        self.temps.append(temp)
        while len(self.temps) > self.size:
            del self.temps[0]

    def get_avg_temp(self, chop=25):
        '''
        take the median of the given values. this used to take an avg
        after getting rid of outliers. median works better.
        '''
        return statistics.median(self.temps)


class ThermocoupleTracker(object):
    '''Keeps sliding window to track successful/failed calls to get temp
       over the last two duty cycles.
    '''

    def __init__(self):
        self.size = config.temperature_average_samples * 2
        self.status = [True for i in range(self.size)]
        self.limit = 30

    def good(self):
        '''True is good!'''
        self.status.append(True)
        del self.status[0]

    def bad(self):
        '''False is bad!'''
        self.status.append(False)
        del self.status[0]

    def error_percent(self):
        errors = sum(i == False for i in self.status)
        return (errors / self.size) * 100

    def over_error_limit(self):
        if self.error_percent() > self.limit:
            return True
        return False


class Max31855(TempSensorReal):
    '''each subclass expected to handle errors and get temperature'''

    def __init__(self):
        TempSensorReal.__init__(self)
        log.info("thermocouple MAX31855")
        import adafruit_max31855
        self.thermocouple = adafruit_max31855.MAX31855(self.spi, self.cs)
        self.last_temp = 0

    def raw_temp(self):
        try:
            temp = self.thermocouple.temperature
            self.last_temp = temp
        except RuntimeError as ex:
            logging.error('Temp2 31855 crash: ' + str(ex))
            temp = self.last_temp

        return temp


class ThermocoupleError(Exception):
    '''
    thermocouple exception parent class to handle mapping of error messages
    and make them consistent across adafruit libraries. Also set whether
    each exception should be ignored based on settings in config.py.
    '''

    def __init__(self, message):
        self.ignore = False
        self.message = message
        self.map_message()
        self.set_ignore()
        super().__init__(self.message)

    def set_ignore(self):
        if self.message == "not connected" and config.ignore_tc_lost_connection == True:
            self.ignore = True
        if self.message == "short circuit" and config.ignore_tc_short_errors == True:
            self.ignore = True
        if self.message == "unknown" and config.ignore_tc_unknown_error == True:
            self.ignore = True
        if self.message == "cold junction range fault" and config.ignore_tc_cold_junction_range_error == True:
            self.ignore = True
        if self.message == "thermocouple range fault" and config.ignore_tc_range_error == True:
            self.ignore = True
        if self.message == "cold junction temp too high" and config.ignore_tc_cold_junction_temp_high == True:
            self.ignore = True
        if self.message == "cold junction temp too low" and config.ignore_tc_cold_junction_temp_low == True:
            self.ignore = True
        if self.message == "thermocouple temp too high" and config.ignore_tc_temp_high == True:
            self.ignore = True
        if self.message == "thermocouple temp too low" and config.ignore_tc_temp_low == True:
            self.ignore = True
        if self.message == "voltage too high or low" and config.ignore_tc_voltage_error == True:
            self.ignore = True

    def map_message(self):
        try:
            self.message = self.map[self.orig_message]
        except KeyError:
            self.message = "unknown"


class Max31855_Error(ThermocoupleError):
    '''
    All children must set self.orig_message and self.map
    '''

    def __init__(self, message):
        self.orig_message = message
        # this purposefully makes "fault reading" and
        # "Total thermoelectric voltage out of range..." unknown errors
        self.map = {
            "thermocouple not connected": "not connected",
            "short circuit to ground": "short circuit",
            "short circuit to power": "short circuit",
        }
        super().__init__(message)


class Max31856_Error(ThermocoupleError):
    def __init__(self, message):
        self.orig_message = message
        self.map = {
            "cj_range": "cold junction range fault",
            "tc_range": "thermocouple range fault",
            "cj_high": "cold junction temp too high",
            "cj_low": "cold junction temp too low",
            "tc_high": "thermocouple temp too high",
            "tc_low": "thermocouple temp too low",
            "voltage": "voltage too high or low",
            "open_tc": "not connected"
        }
        super().__init__(message)


class Max31856(TempSensorReal):
    '''each subclass expected to handle errors and get temperature'''

    def __init__(self):
        TempSensorReal.__init__(self)
        log.info("thermocouple MAX31856")
        import adafruit_max31856
        cs1 = digitalio.DigitalInOut(config.spi_cs_56)
        self.thermocouple = adafruit_max31856.MAX31856(self.spi, cs1,
                                        thermocouple_type=config.thermocouple_type)

        if (config.ac_freq_50hz == True):
            self.thermocouple.noise_rejection = 50
        else:
            self.thermocouple.noise_rejection = 60

    def raw_temp(self):
        # The underlying adafruit library does not throw exceptions
        # for thermocouple errors. Instead, they are stored in
        # dict named self.thermocouple.fault. Here we check that
        # dict for errors and raise an exception.
        # and raise Max31856_Error(message)
        temp = self.thermocouple.temperature

        for k,v in self.thermocouple.fault.items():
            if v:
                logging.error('MAX31856 error: ' + str(k))
                # raise Max31856_Error(k)
        return temp

