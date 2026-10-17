from pilot import observe, transfer


def test_float_pilot_and_decimal_transfer():
    assert observe()["result"] == 0.30000000000000004
    assert observe()["exact_decimal"] is False
    assert transfer()["exact_decimal_result"] == "0.8"
