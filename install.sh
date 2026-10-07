#!/usr/bin/env bash
# Полная настройка Claude Code на новой машине — одной командой.
#
#   curl -fsSL https://raw.githubusercontent.com/MMGGAAS3-git/claude-setup/main/install.sh | bash
#
# Что делает:
#   1. находит бинарь claude (PATH, расширение VSCode, npm);
#   2. подключает два маркетплейса и ставит плагин dmitry-core
#      (taches-cc-resources подтягивается как его зависимость);
#   3. аккуратно домешивает нужные ключи в ~/.claude/settings.json,
#      не трогая всё остальное.
#
# Скрипт идемпотентен: повторный запуск ничего не ломает.

set -euo pipefail

SETUP_REPO="${CC_SETUP_REPO:-MMGGAAS3-git/claude-setup}"
SETUP_MARKETPLACE="dmitry-claude-setup"
TACHES_REPO="glittercowboy/taches-cc-prompts"
TACHES_MARKETPLACE="taches-cc-resources"

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

find_claude() {
  if command -v claude >/dev/null 2>&1; then
    command -v claude
    return 0
  fi
  local c
  for c in "$HOME"/.local/bin/claude \
           "$HOME"/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude \
           "$HOME"/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude \
           "$HOME"/.cursor-server/extensions/anthropic.claude-code-*/resources/native-binary/claude \
           "$HOME"/.cursor/extensions/anthropic.claude-code-*/resources/native-binary/claude; do
    [ -x "$c" ] && { echo "$c"; return 0; }
  done
  return 1
}

CLAUDE="$(find_claude)" || die "Не нашёл бинарь claude. Установи Claude Code и запусти снова."
say "claude: $CLAUDE ($("$CLAUDE" --version 2>/dev/null | head -1))"

command -v python3 >/dev/null 2>&1 || die "Нужен python3 (используется хуком правил и слиянием настроек)."

say "Подключаю маркетплейсы"
"$CLAUDE" plugin marketplace add "$TACHES_REPO" 2>&1 | tail -1 || warn "маркетплейс $TACHES_REPO уже подключён или недоступен"
"$CLAUDE" plugin marketplace add "$SETUP_REPO"  2>&1 | tail -1 || warn "маркетплейс $SETUP_REPO уже подключён или недоступен"

say "Ставлю плагины"
"$CLAUDE" plugin install "${TACHES_MARKETPLACE}@${TACHES_MARKETPLACE}" 2>&1 | tail -1 || warn "taches-cc-resources уже стоит"
"$CLAUDE" plugin install "dmitry-core@${SETUP_MARKETPLACE}" 2>&1 | tail -1 || warn "dmitry-core уже стоит"

say "Правлю ~/.claude/settings.json"
python3 - <<'PYEOF'
import json, os, pathlib

path = pathlib.Path(os.path.expanduser("~/.claude/settings.json"))
path.parent.mkdir(parents=True, exist_ok=True)

try:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("settings.json не объект")
except FileNotFoundError:
    data = {}
except Exception as exc:
    backup = path.with_suffix(".json.broken")
    path.rename(backup)
    print("    прежний settings.json нечитаем (%s), отложен в %s" % (exc, backup))
    data = {}

# opusplan: Sonnet 5.5 в обычной работе, Opus 5.5 в plan mode. Уровни усилия по моделям:
# дефолт «high», а не «xhigh» (xhigh заметно дороже; глубокое мышление — у агента architect).
data["model"] = "opusplan"
data["effortLevel"] = "high"
data["agentPushNotifEnabled"] = True
for _model, _level in (("claude-sonnet-5-5", "high"), ("claude-opus-5-5", "high")):
    data.setdefault("modelSettings", {}).setdefault(_model, {}).setdefault("effortLevel", _level)

perms = data.setdefault("permissions", {})
allow = perms.setdefault("allow", [])
for rule in ["Bash(*)", "Edit(*)", "Write(*)", "Read(*)", "WebSearch(*)", "WebFetch(*)"]:
    if rule not in allow:
        allow.append(rule)
ask = perms.setdefault("ask", [])
if "Bash(sudo *)" not in ask:
    ask.append("Bash(sudo *)")

path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("    записано:", path)
PYEOF

say "Готово."
cat <<'TXT'

Что дальше:
  • Перезапусти Claude Code (или /reload-plugins) — правила и скиллы
    подхватываются на старте сессии.
  • Проверка: claude plugin list  — должны быть dmitry-core и taches-cc-resources.
  • Скиллы из claude.ai (если заливал их туда) один раз подтянуть:
        CLAUDE_CODE_SYNC_SKILLS=1 claude -p "list skills"

TXT
