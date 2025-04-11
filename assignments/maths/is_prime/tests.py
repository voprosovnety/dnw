def test_solution(solution):
    assert solution(2) is True
    assert solution(3) is True
    assert solution(4) is False
    assert solution(17) is True
    assert solution(100) is False
