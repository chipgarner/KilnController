import lib.HeatingRate


def test_init():
    hr = lib.HeatingRate.HeatingRate()

    rate = hr.get_heating_rate()

    assert rate == -1


def test_positive_rate():
    hr = lib.HeatingRate.HeatingRate()

    hr.update_heating_rate(0, 21)
    hr.update_heating_rate(2.1, 21.02)

    rate = hr.get_heating_rate()

    assert rate == 34


def test_negative_rate():
    hr = lib.HeatingRate.HeatingRate()

    hr.update_heating_rate(0, 21.02)
    hr.update_heating_rate(2.1, 21.0)

    rate = hr.get_heating_rate()

    assert rate == -34

    hr.reset()
    rate = hr.get_heating_rate()
    assert rate == -1

def test_zero_rate():
    hr = lib.HeatingRate.HeatingRate()

    hr.update_heating_rate(0, 21.0002)
    hr.update_heating_rate(2.1, 21.0)

    rate = hr.get_heating_rate()

    assert rate == 0
