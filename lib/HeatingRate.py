class HeatingRate:
    def __init__(self):
        self.temp_times = []
        self.heating_rate = -1  # a clue there is no data

    def reset(self):
        self.temp_times = []
        self.heating_rate = -1  # a clue there is no data

    def get_heating_rate(self):
        return self.heating_rate

    def update_heating_rate(self, runtime, temp):
        # heating rate is the heating rate in degrees/hour

        self.temp_times.append((runtime, temp))

        length = len(self.temp_times)
        while length > 20:
            self.temp_times.pop(0)
            length = len(self.temp_times)

        if length > 1:
            delta_t = self.temp_times[length - 1][0] - self.temp_times[0][0]
            if delta_t > 2:  #More than two seconds, try it
                delta_temp = self.temp_times[length - 1][1] - self.temp_times[0][1]
                rate = delta_temp / delta_t * 3600
                self.heating_rate = round(rate)

    # # drop old temps off the list
    # if len(self.heat_rate_temps) > numtemps:
    #     self.heat_rate_temps = self.heat_rate_temps[-1 * numtemps:]
    # time2 = self.heat_rate_temps[-1][0]
    # time1 = self.heat_rate_temps[0][0]
    # temp2 = self.heat_rate_temps[-1][1]
    # temp1 = self.heat_rate_temps[0][1]
    # if time2 > time1:
    #     self.heat_rate = ((temp2 - temp1) / (time2 - time1)) * 3600
