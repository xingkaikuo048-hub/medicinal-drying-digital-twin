"""Resumable sequential batch runner for generated simulation cases."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path,
                        default=PROJECT_ROOT / "outputs" / "designs" / "validation" / "manifest.csv",
                        nargs="?")
    parser.add_argument("--output-root", type=Path,
                        default=PROJECT_ROOT / "outputs" / "simulations")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--smoke", action="store_true",
                        help="run each case with the short validation numerics")
    parser.add_argument("--include-fixed", action="store_true",
                        help="run fixed scenarios when a fixed_scenarios manifest is supplied")
    args = parser.parse_args()
    rows = read_manifest(args.manifest)
    if args.max_cases is not None:
        rows = rows[: max(0, args.max_cases)]
    summary = {"started_utc": now(), "manifest": str(args.manifest),
               "requested": len(rows), "skipped": 0, "succeeded": 0, "failed": 0,
               "cases": []}
    for row in rows:
        case_file = PROJECT_ROOT / row["case_file"]
        payload = json.loads(case_file.read_text(encoding="utf-8"))
        case_config = payload.get("configuration", payload)
        if args.smoke:
            sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
            from run_case import make_smoke_config
            case_config = make_smoke_config(case_config)
        from importlib.util import spec_from_file_location, module_from_spec
        config_spec = spec_from_file_location("drying_config", PROJECT_ROOT / "src" / "drying_twin" / "config.py")
        assert config_spec and config_spec.loader
        config_module = module_from_spec(config_spec)
        config_spec.loader.exec_module(config_module)
        identifier = config_module.case_id(case_config, prefix="simulation")
        case_output = args.output_root / identifier
        status_path = case_output / "status.json"
        if status_path.is_file():
            try:
                previous = json.loads(status_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                previous = {}
            if previous.get("status") == "SUCCEEDED":
                summary["skipped"] += 1
                summary["cases"].append({"case_id": identifier, "status": "SKIPPED"})
                continue
        command = [str(PYTHON), str(PROJECT_ROOT / "scripts" / "run_case.py"),
                   str(case_file), "--output-root", str(args.output_root)]
        if args.smoke:
            command.append("--smoke")
        result = subprocess.run(command, cwd=PROJECT_ROOT, text=True,
                                capture_output=True)
        if result.returncode == 0:
            summary["succeeded"] += 1
            state = "SUCCEEDED"
        else:
            summary["failed"] += 1
            state = "FAILED"
            print(result.stderr, file=sys.stderr)
        summary["cases"].append({"case_id": identifier, "status": state,
                                 "returncode": result.returncode})
    summary["finished_utc"] = now()
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "batch_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if summary["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
