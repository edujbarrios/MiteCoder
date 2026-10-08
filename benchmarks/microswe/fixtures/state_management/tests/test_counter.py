from counter import Counter

def test_instances_are_independent():
    first, second = Counter(), Counter()
    first.increment(); second.increment(); second.increment(); first.reset()
    assert first.value == 0
    assert second.value == 2
