import lib.oven_monitor as oven_monitor
import time


def test_this():
    om = oven_monitor.OvenMonitor()

    temp = om.get_temperature()

    assert temp == 150

    time.sleep(2)
    om.stop()

    temp = om.get_temperature()

    assert temp == 160


