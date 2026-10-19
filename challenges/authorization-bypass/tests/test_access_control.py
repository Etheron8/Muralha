import sys

sys.path.insert(0, "/candidate/src")

from access_control import can_access_document


def test_admin_can_access_document_owned_by_another_user():
    assert can_access_document(
        requester_id=99,
        role="admin",
        document={"owner_id": 7},
    ) is True


def test_user_can_access_own_document():
    assert can_access_document(
        requester_id=7,
        role="user",
        document={"owner_id": 7},
    ) is True


def test_user_cannot_access_another_users_document():
    assert can_access_document(
        requester_id=99,
        role="user",
        document={"owner_id": 7},
    ) is False


def test_unknown_role_is_denied_even_if_document_owner():
    assert can_access_document(
        requester_id=7,
        role="guest",
        document={"owner_id": 7},
    ) is False


def test_document_without_owner_is_not_accessible_to_regular_user():
    assert can_access_document(
        requester_id=7,
        role="user",
        document={},
    ) is False
