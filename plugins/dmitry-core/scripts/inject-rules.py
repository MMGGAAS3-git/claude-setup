#!/usr/bin/env python3
"""SessionStart-хук: отдаёт правила Дмитрия как additionalContext.

jq на машинах не гарантирован, поэтому JSON собираем питоном.
Любая ошибка здесь не должна ронять старт сессии: выходим с кодом 1
(non-blocking error), а не 2.
"""
import json
import os
import sys

try:
    sys.stdin.read()  # хук получает JSON на stdin; не нужен, но читаем, чтобы не ловить SIGPIPE
except Exception:
    pass

root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
rules_path = os.path.join(root, "rules", "RULES.md")

try:
    with open(rules_path, encoding="utf-8") as fh:
        rules = fh.read().strip()
except OSError as exc:
    print("dmitry-core: не прочитал %s: %s" % (rules_path, exc), file=sys.stderr)
    sys.exit(1)

if not rules:
    print("dmitry-core: %s пустой" % rules_path, file=sys.stderr)
    sys.exit(1)

json.dump(
    {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": rules,
        }
    },
    sys.stdout,
    ensure_ascii=False,
)
