def test_solution(solution):
    assert solution(2, 3) == 5, "Тест 1 не пройден"
    assert solution(-1, 1) == 0, "Тест 2 не пройден"
    assert solution(0, 0) == 0, "Тест 3 не пройден"
    print("Все тесты пройдены!")
