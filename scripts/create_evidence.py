"""Create an evidence directory without contacting external systems."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--root", type=Path, default=Path("evidence"))
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = args.root / f"{stamp}-{args.scenario}"
    destination.mkdir(parents=True, exist_ok=False)
    metadata = {
        "scenario_id": args.scenario,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "INCONCLUSIVE",
        "note": "Evidence directory initialized; no experiment has been run.",
    }
    (destination / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "scenario.yaml").write_text(f"scenario_id: {args.scenario}\n", encoding="utf-8")
    (destination / "summary.md").write_text(
        "# Evidence summary\n\nStatus: INCONCLUSIVE\n\nNo experiment has been run.\n",
        encoding="utf-8",
    )
    checksum = hashlib.sha256((destination / "scenario.yaml").read_bytes()).hexdigest()
    (destination / "checksums.sha256").write_text(f"{checksum}  scenario.yaml\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
