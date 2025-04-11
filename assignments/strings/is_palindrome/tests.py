def test_solution(solution):
    assert solution("racecar") is True
    assert solution("RaceCar") is True
    assert solution("hello") is False
    assert solution("A man a plan a canal Panama") is True
    assert solution("Python") is False
    assert solution("Was it a car or a cat I saw") is True
