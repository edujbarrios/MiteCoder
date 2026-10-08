import pytest
from parser import parse_integer

def test_spaces(): assert parse_integer(" 42 ") == 42
def test_trailing():
    with pytest.raises(ValueError): parse_integer("42 things")
