# Weutil hardware tests (EEPROM/wedge utility)
test_context = {
    "filters": [
        "*WeutilTest*",
    ],
}


def test_t0_weutil_hw_tests(weutil_hw_test_runner):
    assert weutil_hw_test_runner.run_test(test_context)
