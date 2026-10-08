from chunks import chunks

def test_exact_chunks(): assert chunks([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]
