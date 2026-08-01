"""Persistiert offene Positionen in einer lokalen JSON-Datei, damit ein Neustart
des Bots keine offenen Positionen 'vergisst'."""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

DEFAULT_STATE_PATH = os.path.join(os.path.dirname(__file__), "state", "positions.json")


@dataclass
class Position:
    product_id: str
    base_size: float
    entry_price: float
    opened_at: str
    client_order_id: str


class StateStore:
    def __init__(self, path=DEFAULT_STATE_PATH):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.positions = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r") as f:
            raw = json.load(f)
        return {k: Position(**v) for k, v in raw.items()}

    def _save(self):
        with open(self.path, "w") as f:
            json.dump({k: asdict(v) for k, v in self.positions.items()}, f, indent=2)

    def open_position(self, product_id, base_size, entry_price, client_order_id):
        self.positions[product_id] = Position(
            product_id=product_id,
            base_size=base_size,
            entry_price=entry_price,
            opened_at=datetime.now(timezone.utc).isoformat(),
            client_order_id=client_order_id,
        )
        self._save()

    def close_position(self, product_id):
        self.positions.pop(product_id, None)
        self._save()

    def get(self, product_id):
        return self.positions.get(product_id)

    def all(self):
        return dict(self.positions)
