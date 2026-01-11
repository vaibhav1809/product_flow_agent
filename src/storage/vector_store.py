from __future__ import annotations


class VectorStore:
    def __init__(self) -> None:
        self._data: list[tuple[str, list[float]]] = []

    def add(self, item_id: str, embedding: list[float]) -> None:
        self._data.append((item_id, embedding))

    def query(self, embedding: list[float], top_k: int = 5) -> list[str]:
        return [item_id for item_id, _ in self._data[:top_k]]
