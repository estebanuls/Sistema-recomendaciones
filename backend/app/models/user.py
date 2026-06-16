"""User model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class User:
    id: int
    username: str
    display_name: str
    created_at: str
    is_admin: bool

    @classmethod
    def from_row(cls, row: dict[str, object]) -> "User":
        return cls(
            id=int(row["id"]),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            created_at=str(row["created_at"]),
            is_admin=bool(row.get("is_admin", 0)),
        )

    def to_public_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "is_admin": self.is_admin,
        }