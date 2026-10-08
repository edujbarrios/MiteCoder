from users import valid_username

def test_boundaries():
    assert not valid_username("")
    assert valid_username("a")
    assert not valid_username("a" * 13)
