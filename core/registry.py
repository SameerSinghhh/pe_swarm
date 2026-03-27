"""
Document type registry. Schemas register themselves on import.
"""


class DocumentTypeRegistry:
    _schemas: dict = {}

    @classmethod
    def register(cls, schema):
        cls._schemas[schema.doc_type_id] = schema

    @classmethod
    def get(cls, doc_type_id: str):
        return cls._schemas.get(doc_type_id)

    @classmethod
    def all_schemas(cls) -> list:
        return list(cls._schemas.values())

    @classmethod
    def all_type_ids(cls) -> list[str]:
        return list(cls._schemas.keys())

    @classmethod
    def summary(cls) -> str:
        lines = []
        for s in cls._schemas.values():
            lines.append(f"- {s.doc_type_id}: {s.doc_type_name}")
        return "\n".join(lines)
