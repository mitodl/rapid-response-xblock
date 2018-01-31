"""Just here to verify tests are running"""
from rapid_response_datastore.func import add


def test_thing():
    assert add(2, 2) == 4
