from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_policy() -> Dict[str, Any]:
    policy_path = Path(__file__).resolve().parent.parent / "config" / "policy.json"
    with open(policy_path, "r", encoding="utf-8") as f:
        return json.load(f)
