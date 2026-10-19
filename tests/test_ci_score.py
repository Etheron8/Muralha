from scripts.score_ci_result import build_result


def test_score_is_proportional_to_passed_cases():
    result = build_result(
        passed_count=3,
        total_count=5,
        failed_tests=["case-4", "case-5"],
        runner_status="completed",
    )
    assert result["score"] == 60
    assert result["score_max"] == 100
    assert result["status"] == "failed"
    assert result["evaluation"]["tests_passed"] == 3
    assert result["evaluation"]["failed_test_names"] == ["case-4", "case-5"]


def test_no_final_score_when_runner_is_unavailable():
    result = build_result(
        passed_count=0,
        total_count=5,
        runner_status="not_configured",
        runner_message="Docker indisponível.",
    )
    assert result["score"] is None
    assert result["status"] == "not_configured"
    assert result["evaluation"]["tests_executed"] == 0
