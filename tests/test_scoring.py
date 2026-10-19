from muralha.scoring import score_diagnosis


def test_correct_fields_receive_all_diagnostic_points():
    golden = {
        "cwe": "CWE-863",
        "severity": "high",
        "file": "src/access_control.py",
        "line_range": [5, 5],
        "root_cause_phrases": ["condição sempre verdadeira"],
        "fix_phrases": ["comparar o papel explicitamente"],
    }
    finding = {
        "cwe": "CWE-863",
        "severity": "high",
        "file": "src/access_control.py",
        "line": 5,
        "description": "O problema é uma condição sempre verdadeira.",
        "fix_summary": "A correção é comparar o papel explicitamente.",
    }
    result = score_diagnosis(finding, golden)
    assert result["diagnostic_score"] == 70
    assert result["diagnostic_max"] == 70


def test_wrong_diagnosis_does_not_get_full_score():
    golden = {
        "cwe": "CWE-863",
        "severity": "high",
        "file": "src/access_control.py",
        "line_range": [5, 5],
        "root_cause_phrases": ["condição sempre verdadeira"],
        "fix_phrases": ["comparar o papel explicitamente"],
    }
    finding = {
        "cwe": "CWE-79",
        "severity": "low",
        "file": "README.md",
        "line": 1,
        "description": "Problema de CSS.",
        "fix_summary": "Mude a cor.",
    }
    assert score_diagnosis(finding, golden)["diagnostic_score"] == 0
