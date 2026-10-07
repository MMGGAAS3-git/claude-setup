#!/usr/bin/env python3
"""Local token/price report from Claude Code transcripts. Sends nothing anywhere.

Usage: usage-report.py [--days N] [--top N]
Reads ~/.claude/projects/**/*.jsonl (main sessions and subagents/).
Prices are API list prices (USD per million tokens), used only as a relative
yardstick between models; Pro-plan limits are not published per model.
"""
import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import sys

# model-id regex -> (input, cache_write_5m, cache_write_1h, cache_read, output)
PRICES = [
    (r"fable",       (10.0, 12.5, 20.0, 0.25, 50.0)),
    (r"opus-5-5",    (4.0, 5.0, 8.0, 0.20, 20.0)),
    (r"opus",        (5.0, 6.25, 10.0, 0.50, 25.0)),
    (r"sonnet-5",    (2.0, 2.5, 4.0, 0.20, 10.0)),
    (r"haiku",       (1.0, 1.25, 2.0, 0.10, 5.0)),
]
FALLBACK = (3.0, 3.75, 6.0, 0.30, 15.0)


def price(model):
    for pat, p in PRICES:
        if re.search(pat, model or ""):
            return p, True
    return FALLBACK, False


def cost(model, u):
    p, _ = price(model)
    cc = u.get("cache_creation") or {}
    w1h = cc.get("ephemeral_1h_input_tokens", 0)
    w5m = cc.get("ephemeral_5m_input_tokens", 0)
    if not cc:
        w5m = u.get("cache_creation_input_tokens", 0)
    return (u.get("input_tokens", 0) * p[0] + w5m * p[1] + w1h * p[2]
            + u.get("cache_read_input_tokens", 0) * p[3]
            + u.get("output_tokens", 0) * p[4]) / 1e6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.days)
    root = os.path.expanduser("~/.claude/projects")
    files = glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)

    best = {}            # message id -> (out_tokens, record) ; resumed sessions repeat history
    delegations = collections.Counter()
    for f in files:
        try:
            if dt.datetime.fromtimestamp(os.path.getmtime(f), dt.timezone.utc) < since:
                continue
        except OSError:
            continue
        sub = os.sep + "subagents" + os.sep in f
        role = "main"
        if sub:
            role = "unknown-agent"
            meta = f[:-6] + ".meta.json"
            try:
                role = json.load(open(meta)).get("agentType") or role
            except Exception:
                pass
        session = os.path.basename(os.path.dirname(os.path.dirname(f))) if sub else os.path.basename(f)[:-6]
        for line in open(f, encoding="utf-8", errors="ignore"):
            try:
                d = json.loads(line)
            except Exception:
                continue
            ts = d.get("timestamp")
            if ts:
                try:
                    if dt.datetime.fromisoformat(ts.replace("Z", "+00:00")) < since:
                        continue
                except Exception:
                    pass
            m = d.get("message")
            if not isinstance(m, dict):
                continue
            if not sub and isinstance(m.get("content"), list):
                for b in m["content"]:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Agent", "Task"):
                        i = b.get("input") or {}
                        delegations[(i.get("subagent_type") or "general-purpose", i.get("model") or "(agent default)")] += 1
            u = m.get("usage")
            if not isinstance(u, dict) or not m.get("model") or m["model"].startswith("<"):
                continue
            key = m.get("id") or (f, d.get("uuid"))
            out = u.get("output_tokens", 0)
            if key not in best or out >= best[key][0]:
                best[key] = (out, {"model": m["model"], "u": u, "role": role, "session": session})

    by_model = collections.defaultdict(lambda: collections.Counter())
    by_role = collections.defaultdict(lambda: collections.Counter())
    by_session = collections.Counter()
    unknown = set()
    for _, r in best.values():
        u, model = r["u"], r["model"]
        c = cost(model, u)
        if not price(model)[1]:
            unknown.add(model)
        cc = u.get("cache_creation_input_tokens", 0)
        for bucket in (by_model[model], by_role[(r["role"], model)]):
            bucket["turns"] += 1
            bucket["fresh_in"] += u.get("input_tokens", 0)
            bucket["cache_write"] += cc
            bucket["cache_read"] += u.get("cache_read_input_tokens", 0)
            bucket["out"] += u.get("output_tokens", 0)
            bucket["usd_micro"] += int(c * 1e6)
        by_session[r["session"]] += c

    total = sum(b["usd_micro"] for b in by_model.values()) / 1e6
    print(f"Period: last {a.days} days, {len(best)} model turns, {len(files)} transcript files scanned")
    print(f"API-list-price equivalent: ${total:.2f}  (relative yardstick only; Pro limits are not billed per token)\n")

    def row(name, b):
        usd = b["usd_micro"] / 1e6
        share = 100 * usd / total if total else 0
        return f"{name:<34} {b['turns']:>6} {b['fresh_in']:>9,} {b['cache_write']:>11,} {b['cache_read']:>13,} {b['out']:>9,} {usd:>8.2f} {share:>5.0f}%"
    head = f"{'':<34} {'turns':>6} {'fresh_in':>9} {'cache_write':>11} {'cache_read':>13} {'output':>9} {'USD~':>8} {'share':>6}"
    print("BY MODEL\n" + head)
    for model, b in sorted(by_model.items(), key=lambda x: -x[1]["usd_micro"]):
        print(row(model, b))
    print("\nBY ROLE x MODEL (main session vs subagent type)\n" + head)
    for (role, model), b in sorted(by_role.items(), key=lambda x: -x[1]["usd_micro"])[:12]:
        print(row(f"{role} / {model}", b))
    print("\nDELEGATIONS (Agent tool calls in main sessions: subagent_type, model param)")
    if not delegations:
        print("  none")
    for (t, mo), n in delegations.most_common(12):
        print(f"  {n:>4}  {t}  [{mo}]")
    print(f"\nTOP {a.top} SESSIONS BY USD~")
    for s, c in by_session.most_common(a.top):
        print(f"  ${c:>7.2f}  {s}")
    if unknown:
        print("\nNote: no price entry for", ", ".join(sorted(unknown)), "- Sonnet 4.x price assumed.")


if __name__ == "__main__":
    sys.exit(main())
