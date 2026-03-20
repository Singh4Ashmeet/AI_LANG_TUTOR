from backend.routers.lessons import _grade_answer


def test_grade_answer_accepts_close_spelling():
    exercise = {"type": 9, "correct_answer": "Me llamo Sofia"}
    result = _grade_answer(exercise, "Me llamo Sofis")

    assert result["is_correct"] is True
    assert result["accepted_with_typo"] is True
    assert result["almost_correct"] is True


def test_grade_answer_marks_near_miss_without_accepting():
    exercise = {"type": 4, "correct_answer": "Estoy feliz"}
    result = _grade_answer(exercise, "Estoi feli")

    assert result["is_correct"] is False
    assert result["almost_correct"] is True
    assert result["accepted_with_typo"] is False


def test_grade_answer_exact_match_for_lists():
    exercise = {"type": 8, "correct_answer": ["yo", "estudio", "espanol"]}
    result = _grade_answer(exercise, ["yo", "estudio", "espanol"])

    assert result["is_correct"] is True
    assert result["accepted_with_typo"] is False
