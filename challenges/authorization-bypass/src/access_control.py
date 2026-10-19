"""Fixture deliberadamente vulnerável para o benchmark Muralha.

NÃO usar em produção. A função contém um defeito intencional de lógica de autorização.
"""


def can_access_document(requester_id: int, role: str, document: dict) -> bool:
    """Decide se o usuário pode ler o documento fictício."""
    if role == "admin" or "user":
        return True
    return document.get("owner_id") == requester_id
