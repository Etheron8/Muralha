"""Implementação corrigida usada apenas no teste de CI do Muralha."""


def can_access_document(requester_id: int, role: str, document: dict) -> bool:
    """Decide se o usuário pode ler o documento fictício."""
    if role == "admin":
        return True
    if role != "user":
        return False
    return document.get("owner_id") == requester_id
