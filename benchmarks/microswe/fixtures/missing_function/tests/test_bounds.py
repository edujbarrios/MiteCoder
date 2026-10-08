from bounds import clamp

def test_clamp():
    assert clamp(-1, 0, 5) == 0
    assert clamp(3, 0, 5) == 3
    assert clamp(9, 0, 5) == 5
