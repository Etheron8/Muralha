from muralha.catalog import load_catalog, public_challenge


def test_catalog_has_unique_ids_and_safe_relative_paths():
    catalog = load_catalog()
    ids = [item["id"] for item in catalog]
    assert ids
    assert len(ids) == len(set(ids))
    for item in catalog:
        assert all(".." not in rel.split("/") for rel in item["files"])


def test_public_challenge_does_not_return_golden_fields():
    item = load_catalog()[0]
    response = public_challenge(item, include_files=True)
    assert "files" in response
    assert "answer" not in response
    assert "golden" not in response
    assert "root_cause_phrases" not in response
