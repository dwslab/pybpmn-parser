from pybpmn.util import split_camel_case


def test_split_camel_case():
    test_cases = {
        "timerStartEvent": "Timer Start Event",
        "pool": "Pool",
    }
    for k, expected in test_cases.items():
        actual = split_camel_case(k)
        assert actual == expected
