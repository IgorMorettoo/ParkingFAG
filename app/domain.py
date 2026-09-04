from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ParkingReading:
    total_spaces: int
    free_spaces: int
    occupied_spaces: int
    spaces: list[dict[str, Any]]
    source: str
    captured_at: str

    @classmethod
    def create(
        cls,
        *,
        total_spaces: int,
        free_spaces: int,
        spaces: list[dict[str, Any]] | None = None,
        source: str = "detector",
        captured_at: str | None = None,
    ) -> "ParkingReading":
        if total_spaces < 0:
            raise ValueError("total_spaces nao pode ser negativo")
        if not 0 <= free_spaces <= total_spaces:
            raise ValueError("free_spaces deve estar entre zero e total_spaces")
        normalized_spaces = spaces or []
        if normalized_spaces and len(normalized_spaces) != total_spaces:
            raise ValueError("a quantidade de vagas detalhadas deve ser igual a total_spaces")
        return cls(
            total_spaces=total_spaces,
            free_spaces=free_spaces,
            occupied_spaces=total_spaces - free_spaces,
            spaces=normalized_spaces,
            source=(source.strip() or "detector")[:100],
            captured_at=captured_at or datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ParkingReading":
        return cls.create(
            total_spaces=int(payload["total_spaces"]),
            free_spaces=int(payload["free_spaces"]),
            spaces=payload.get("spaces") or [],
            source=str(payload.get("source", "detector")),
            captured_at=payload.get("captured_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_counts(counts: list[int], threshold: int = 900) -> list[dict[str, Any]]:
    """Converte contagens de pixels em estados testaveis de vaga."""
    if threshold <= 0:
        raise ValueError("threshold deve ser positivo")
    return [
        {"index": index, "pixel_count": count, "is_free": count < threshold}
        for index, count in enumerate(counts, start=1)
    ]

