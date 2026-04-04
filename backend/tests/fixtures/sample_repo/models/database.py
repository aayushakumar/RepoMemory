"""Database models and operations."""


class Database:
    """Simple in-memory database for demonstration."""

    def __init__(self):
        self._tables: dict[str, list[dict]] = {}

    def create_table(self, name: str) -> None:
        if name not in self._tables:
            self._tables[name] = []

    def insert(self, table: str, record: dict) -> int:
        if table not in self._tables:
            self.create_table(table)
        self._tables[table].append(record)
        return len(self._tables[table]) - 1

    def find(self, table: str, **kwargs) -> list[dict]:
        if table not in self._tables:
            return []
        results = []
        for record in self._tables[table]:
            if all(record.get(k) == v for k, v in kwargs.items()):
                results.append(record)
        return results

    def update(self, table: str, index: int, data: dict) -> bool:
        if table not in self._tables or index >= len(self._tables[table]):
            return False
        self._tables[table][index].update(data)
        return True

    def delete(self, table: str, index: int) -> bool:
        if table not in self._tables or index >= len(self._tables[table]):
            return False
        self._tables[table].pop(index)
        return True
