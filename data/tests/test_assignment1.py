def test_solution(solution):
    assert solution(5) == 15, "При n=5 должно быть 15"
    assert solution(10) == 55, "При n=10 должно быть 55"
    assert solution(1) == 1, "При n=1 должно быть 1"
