from ranking import rank

def test_rank():
    rows = [{"name": "zoe", "score": 2}, {"name": "amy", "score": 2}, {"name": "max", "score": 3}]
    assert [row["name"] for row in rank(rows)] == ["max", "amy", "zoe"]
