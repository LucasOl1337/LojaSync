"""Benchmark ALL 9router models on nota3.jpeg for LojaSync extraction.

Reports latency, item count, sum, tokens, and estimated cost.
Usage:
  python scripts/bench_9router_romaneio.py
  python scripts/bench_9router_romaneio.py --vision-only
  python scripts/bench_9router_romaneio.py --workers 2 --timeout 180
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE = os.environ.get("NINE_ROUTER_BASE_URL") or "http://68.183.26.96:20128/v1"
DEFAULT_IMAGE = Path(r"C:\Users\user\Downloads\SuperRomaneios\notas\nota3.jpeg")
OUT_DIR = Path(r"C:\Users\user\AppData\Local\Temp\lojasync_9router_bench")

SYSTEM = (
    "You are LojaSync invoice extractor. Return ONLY valid JSON with items from the product table. "
    'Schema: {"items":[{"codigo":"","descricao_original":"","nome_curto":"","quantidade":0,"preco":0,"tamanho":""}],'
    '"document_total_products":null,"document_total_note":null} '
    "preco = unit price. One item per product row. No markdown."
)
USER = "Extract EVERY product row visible in this Brazilian NF-e/romaneio photo into the JSON schema. Return JSON only."

# Approximate public USD per 1M tokens (input/output). Used only when gateway omits pricing.
# Sources: public list prices mid-2026 ballpark — not a quote.
APPROX_USD_PER_M = {
    "gpt-5.5": (2.5, 15.0),
    "gpt-5.4": (2.0, 12.0),
    "gpt-5.4-mini": (0.4, 1.6),
    "gpt-5.2": (1.5, 10.0),
    "gpt-5.1": (1.25, 10.0),
    "gpt-5": (1.25, 10.0),
    "claude-opus": (15.0, 75.0),
    "claude-sonnet": (3.0, 15.0),
    "claude-haiku": (1.0, 5.0),
    "claude-fable": (3.0, 15.0),
    "gemini-3.1-pro": (1.25, 10.0),
    "gemini-3-flash": (0.15, 0.6),
    "gemini-2.0-flash": (0.1, 0.4),
    "gemma": (0.1, 0.3),
    "grok-4.5": (3.0, 15.0),
    "grok-4.3": (2.0, 10.0),
    "grok-build": (3.0, 15.0),
    "kimi-k3": (1.0, 3.0),
    "kimi-for-coding": (1.0, 3.0),
    "kimi-k2.7": (1.0, 3.0),
    "kimi-k2.6": (0.6, 2.0),
    "kimi-k2.5": (0.6, 2.0),
    "glm": (0.5, 2.0),
    "qwen": (0.4, 1.5),
    "minimax": (0.5, 2.0),
    "mimo": (0.5, 2.0),
    "deepseek": (0.3, 1.2),
}


def api_key() -> str:
    return (
        os.environ.get("BOMBA_LAB_NINE_ROUTER_KEY")
        or os.environ.get("NINE_ROUTER_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()


def http_json(method: str, url: str, headers: dict, body: dict | None = None, timeout: float = 180.0):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        status = e.code
        return status, time.perf_counter() - t0, None, raw
    except Exception as e:
        return 0, time.perf_counter() - t0, None, str(e)
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = None
    return status, time.perf_counter() - t0, parsed, raw


def list_models(base: str) -> list[dict]:
    status, _, parsed, raw = http_json(
        "GET",
        f"{base.rstrip('/')}/models",
        {"Authorization": f"Bearer {api_key()}"},
        timeout=30,
    )
    if status != 200 or not isinstance(parsed, dict):
        raise RuntimeError(f"list models failed status={status} body={raw[:300]}")
    return list(parsed.get("data") or [])


def extract_content(parsed: dict | None, raw: str = "") -> tuple[str, dict | None]:
    usage = None
    if isinstance(parsed, dict):
        if isinstance(parsed.get("usage"), dict):
            usage = parsed["usage"]
        choices = parsed.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message") or {}
            c = msg.get("content")
            if isinstance(c, str) and c.strip():
                return c, usage
            if isinstance(c, list):
                joined = "".join(str(p.get("text") or "") for p in c if isinstance(p, dict))
                if joined.strip():
                    return joined, usage
        if isinstance(parsed.get("output_text"), str) and parsed["output_text"].strip():
            return parsed["output_text"], usage

    # SSE stream (Claude via 9router often streams even without stream:true)
    if "data:" in (raw or ""):
        parts: list[str] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                chunk = json.loads(payload)
            except Exception:
                continue
            if not isinstance(chunk, dict):
                continue
            if isinstance(chunk.get("usage"), dict):
                usage = chunk["usage"]
            choices = chunk.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                if delta.get("content"):
                    parts.append(str(delta["content"]))
                msg = choices[0].get("message") or {}
                if msg.get("content"):
                    parts.append(str(msg["content"]))
        joined = "".join(parts)
        if joined.strip():
            return joined, usage
    return "", usage


def analyze(content: str) -> dict:
    content = (content or "").strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    i = content.find("{")
    j = content.rfind("}")
    blob = content[i : j + 1] if i >= 0 and j > i else content
    try:
        obj = json.loads(blob)
        items = obj.get("items") if isinstance(obj, dict) else None
        if not isinstance(items, list):
            return {"parse": "ok_no_items", "n": 0, "sum": None}
        s = 0.0
        for it in items:
            if not isinstance(it, dict):
                continue
            try:
                s += float(it.get("quantidade") or 0) * float(it.get("preco") or 0)
            except Exception:
                pass
        return {"parse": "ok", "n": len(items), "sum": round(s, 2)}
    except Exception:
        return {"parse": "fail", "n_codigo": content.count('"codigo"'), "n": None, "sum": None}


def estimate_cost_usd(model_id: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    mid = (model_id or "").lower()
    rates = None
    for key, val in APPROX_USD_PER_M.items():
        if key in mid:
            rates = val
            break
    if not rates:
        # generic default
        rates = (1.0, 3.0)
    pin, pout = rates
    return round((prompt_tokens / 1_000_000.0) * pin + (completion_tokens / 1_000_000.0) * pout, 6)


def is_vision_model(m: dict) -> bool:
    caps = m.get("capabilities") if isinstance(m.get("capabilities"), dict) else {}
    if caps.get("vision") is True:
        return True
    if caps.get("vision") is False:
        return False
    mid = str(m.get("id") or "").lower()
    # combo / unknown: try
    return True


def run_one(base: str, model_id: str, data_url: str, timeout: float, max_tokens: int) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": USER},
                ],
            },
        ],
        # Prefer no thinking when supported
        "thinking": {"type": "disabled"},
    }
    status, sec, parsed, raw = http_json("POST", f"{base.rstrip('/')}/chat/completions", headers, body, timeout=timeout)
    if status >= 400 and "thinking" in (raw or "").lower():
        body.pop("thinking", None)
        status, sec, parsed, raw = http_json(
            "POST", f"{base.rstrip('/')}/chat/completions", headers, body, timeout=timeout
        )
    content, usage = extract_content(parsed, raw)
    if usage is None and isinstance(parsed, dict) and isinstance(parsed.get("usage"), dict):
        usage = parsed.get("usage")
    prompt_tokens = int((usage or {}).get("prompt_tokens") or (usage or {}).get("input_tokens") or 0)
    completion_tokens = int((usage or {}).get("completion_tokens") or (usage or {}).get("output_tokens") or 0)
    total_tokens = int((usage or {}).get("total_tokens") or (prompt_tokens + completion_tokens) or 0)
    reasoning = None
    details = (usage or {}).get("completion_tokens_details") if isinstance(usage, dict) else None
    if isinstance(details, dict):
        reasoning = details.get("reasoning_tokens")
    analysis = analyze(content)
    cost = estimate_cost_usd(model_id, prompt_tokens, completion_tokens) if total_tokens else None
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in model_id)[:120]
    out_path = OUT_DIR / f"{safe}.json"
    out_path.write_text(
        json.dumps(
            {
                "model": model_id,
                "status": status,
                "sec": round(sec, 2),
                "content": content[:20000],
                "usage": usage,
                "analysis": analysis,
                "error": raw[:800] if status != 200 else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "model": model_id,
        "status": status,
        "sec": round(sec, 2),
        "parse": analysis.get("parse"),
        "items": analysis.get("n"),
        "n_codigo": analysis.get("n_codigo"),
        "sum": analysis.get("sum"),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "reasoning_tokens": reasoning,
        "est_cost_usd": cost,
        "ok": status == 200 and analysis.get("parse") == "ok" and int(analysis.get("n") or 0) >= 20,
        "error": (raw[:240] if status != 200 else None),
        "saved": str(out_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.environ.get("NINE_ROUTER_BASE_URL") or DEFAULT_BASE)
    parser.add_argument("--image", default=str(DEFAULT_IMAGE))
    parser.add_argument("--vision-only", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-tokens", type=int, default=16384)
    parser.add_argument("--limit", type=int, default=0, help="0 = all models")
    args = parser.parse_args()

    if not api_key():
        print("ERROR: no 9router API key in env")
        return 2
    image_path = Path(args.image)
    if not image_path.is_file():
        print("ERROR: image not found", image_path)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    models = list_models(args.base)
    if args.vision_only:
        models = [m for m in models if is_vision_model(m) and (m.get("capabilities") or {}).get("vision") is not False]
        # Prefer explicit vision True + unknown; drop explicit False
        models = [
            m
            for m in models
            if (m.get("capabilities") or {}).get("vision") is True
            or (m.get("capabilities") or {}).get("vision") is None
        ]
    # Deduplicate by id
    seen = set()
    ordered = []
    for m in models:
        mid = str(m.get("id") or "").strip()
        if not mid or mid in seen:
            continue
        seen.add(mid)
        ordered.append(m)
    if args.limit > 0:
        ordered = ordered[: args.limit]

    data_url = "data:image/jpeg;base64," + base64.b64encode(image_path.read_bytes()).decode("ascii")
    print(f"base={args.base} models={len(ordered)} workers={args.workers} image={image_path.name}")

    results: list[dict] = []
    t_all = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {
            pool.submit(run_one, args.base, str(m["id"]), data_url, args.timeout, args.max_tokens): str(m["id"])
            for m in ordered
        }
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            mid = futs[fut]
            done += 1
            try:
                row = fut.result()
            except Exception as e:
                row = {"model": mid, "status": 0, "sec": None, "parse": "error", "ok": False, "error": str(e)}
            results.append(row)
            print(
                f"[{done}/{len(ordered)}] {row.get('model')} status={row.get('status')} "
                f"sec={row.get('sec')} items={row.get('items')} sum={row.get('sum')} "
                f"tok={row.get('total_tokens')} cost~${row.get('est_cost_usd')} ok={row.get('ok')}",
                flush=True,
            )

    results.sort(key=lambda r: (0 if r.get("ok") else 1, r.get("sec") if r.get("sec") is not None else 9e9))
    summary = {
        "image": str(image_path),
        "base": args.base,
        "total_models": len(ordered),
        "elapsed_sec": round(time.perf_counter() - t_all, 1),
        "ok_count": sum(1 for r in results if r.get("ok")),
        "results": results,
    }
    summary_path = OUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown report
    lines = [
        "# 9router romaneio bench (nota3.jpeg)",
        "",
        f"- models tested: **{len(ordered)}**",
        f"- wall time: **{summary['elapsed_sec']}s**",
        f"- ok (>=20 items parseable JSON): **{summary['ok_count']}**",
        "",
        "| model | sec | items | sum | tokens | est $ | ok | status |",
        "|---|---:|---:|---:|---:|---:|:---:|---:|",
    ]
    for r in results:
        lines.append(
            f"| `{r.get('model')}` | {r.get('sec')} | {r.get('items')} | {r.get('sum')} | "
            f"{r.get('total_tokens')} | {r.get('est_cost_usd')} | {r.get('ok')} | {r.get('status')} |"
        )
    report_path = OUT_DIR / "REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # also copy into repo docs for convenience
    repo_report = Path(__file__).resolve().parents[1] / "docs" / "research" / "bench-9router-romaneio.md"
    repo_report.parent.mkdir(parents=True, exist_ok=True)
    repo_report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nDONE")
    print("summary", summary_path)
    print("report", report_path)
    print("repo_report", repo_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
