def test_solution(solution):
    assert solution(2) == True, "Тест 1 не пройден"
    assert solution(4) == False, "Тест 2 не пройден"
    assert solution(17) == True, "Тест 3 не пройден"
    print("Все тесты пройдены!")
