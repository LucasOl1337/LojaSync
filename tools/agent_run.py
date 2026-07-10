from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "DocsDev" / "agent" / "actions-index.json"
DEFAULT_BASE = "http://127.0.0.1:8800"


def load_index() -> dict[str, Any]:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def request_json(base: str, method: str, path: str, body: Any | None = None, dry_run: bool = False) -> tuple[int, Any]:
    url = base.rstrip("/") + path
    if dry_run and method.upper() in {"GET", "DELETE"}:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}dry_run=true"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        if dry_run and isinstance(body, dict):
            body = {**body, "dry_run": True}
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif dry_run and method.upper() == "POST":
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}dry_run=true"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw.strip() else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return 0, {"detail": f"Request failed: {reason}"}


def cmd_list(index: dict[str, Any]) -> int:
    for action in index["actions"]:
        dry = " dry-run" if action.get("dry_run") else ""
        risk = action.get("risk", "?")
        print(f"{action['name']:32} {action['method']:6} {action['path']:40} risk={risk}{dry}")
    return 0


def cmd_health(base: str) -> int:
    status, payload = request_json(base, "GET", "/health")
    print(json.dumps({"http": status, "body": payload}, ensure_ascii=False, indent=2))
    return 0 if status == 200 and isinstance(payload, dict) and payload.get("status") == "ok" else 1


def find_action(index: dict[str, Any], name: str) -> dict[str, Any] | None:
    for action in index["actions"]:
        if action["name"] == name:
            return action
    return None


def cmd_run(
    base: str,
    index: dict[str, Any],
    name: str,
    dry_run: bool,
    body_json: str | None,
    path_override: str | None = None,
) -> int:
    action = find_action(index, name)
    if action is None:
        print(f"Unknown action: {name}", file=sys.stderr)
        return 2
    if action.get("needs_human") and not dry_run:
        print(f"Action {name} needs human confirmation (desktop automation). Aborting.", file=sys.stderr)
        return 3
    body = None
    if body_json:
        try:
            body = json.loads(body_json)
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON body: {exc.msg}", file=sys.stderr)
            return 2
    elif isinstance(action.get("body"), dict):
        body = {k: v for k, v in action["body"].items() if k != "dry_run"}
    path = path_override or action["path"]
    if path_override and not path_override.startswith("/"):
        print(f"Concrete path must start with '/': {path_override}", file=sys.stderr)
        return 2
    if "{" in path:
        print(f"Path has placeholders: {path}. Pass a concrete path via --path.", file=sys.stderr)
        return 2
    status, payload = request_json(base, action["method"], path, body=body, dry_run=dry_run)
    print(json.dumps({"action": name, "http": status, "body": payload}, ensure_ascii=False, indent=2))
    return 0 if 200 <= status < 300 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="LojaSync agent action runner")
    parser.add_argument("--base", default=DEFAULT_BASE)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List catalog actions")
    sub.add_parser("health", help="Check GET /health")

    run_p = sub.add_parser("run", help="Run a catalog action")
    run_p.add_argument("name")
    run_p.add_argument("--dry-run", action="store_true")
    run_p.add_argument("--body", default=None, help="JSON body override")
    run_p.add_argument("--path", default=None, help="Concrete path for catalog actions with placeholders")

    args = parser.parse_args()
    index = load_index()
    if args.cmd == "list":
        return cmd_list(index)
    if args.cmd == "health":
        return cmd_health(args.base)
    if args.cmd == "run":
        return cmd_run(args.base, index, args.name, args.dry_run, args.body, args.path)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
