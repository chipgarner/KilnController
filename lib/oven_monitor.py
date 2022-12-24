import time

from lib.oven import SimulatedBoard
from lib.oven import RealBoard


class OvenMonitor:
    def __init__(self):
        try:
            self.board = RealBoard()
        except NotImplementedError:
            self.board = SimulatedBoard()

        self.start_time = time.time()

    def get_temperature(self):
        return self.board.temp_sensor.temperature()

    def get_state(self):

        state = {
            # 'cost': self.cost,
            'runtime': int(time.time() - self.start_time) * 100,
            'temperature': self.get_temperature(),
            # 'target': self.target,
            'state': 'RUNNING',
            # 'heat': self.heat,
            # 'totaltime': self.totaltime,
            # 'kwh_rate': config.kwh_rate,
            # 'currency_type': config.currency_type,
            # 'profile': self.profile.name if self.profile else None,
            # 'pidstats': self.pid.pidstats,
            # 'scheduled_start': scheduled_start,
        }
        return state

    def set_ovenwatcher(self, watcher):
        self.ovenwatcher = watcher