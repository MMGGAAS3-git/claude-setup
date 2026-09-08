# claude-setup

Личная настройка Claude Code, которая разворачивается на новой машине одной командой.

```bash
curl -fsSL https://raw.githubusercontent.com/MMGGAAS3-git/claude-setup/main/install.sh | bash
```

## Что внутри

```
.claude-plugin/marketplace.json     маркетплейс dmitry-claude-setup
plugins/dmitry-core/
├── .claude-plugin/plugin.json      манифест + зависимость на taches-cc-resources
├── rules/RULES.md                  ← единственный источник правды для правил
├── hooks/hooks.json                SessionStart-хук
├── scripts/inject-rules.py         отдаёт RULES.md как additionalContext
└── .mcp.json                       MCP-сервер context7
install.sh                          установщик
```

## Как это работает

Правила не лежат в `~/.claude/CLAUDE.md` и никуда не копируются. Они живут в
`rules/RULES.md` внутри плагина. На старте каждой сессии хук `SessionStart`
читает этот файл и отдаёт его содержимое как `additionalContext` — Claude
Code подставляет его в системный промпт.

Поэтому чтобы изменить правила на всех машинах, достаточно поправить
`rules/RULES.md`, закоммитить и запушить. Машины подхватят при обновлении
плагина.

## Обновление

```bash
# на машине, где правишь
git commit -am "правила: ..." && git push

# на остальных машинах
claude plugin update dmitry-core
```

Либо включить авто-обновление маркетплейса в `/plugin`.

## Проверка

```bash
claude plugin list                        # dmitry-core + taches-cc-resources
claude plugin details dmitry-core         # состав и цена в токенах
python3 plugins/dmitry-core/scripts/inject-rules.py </dev/null   # сырой JSON хука
```

## Полезное

- Отключить всё разом: `claude plugin disable dmitry-core`
- Убрать совсем: `claude plugin uninstall dmitry-core --prune`
- Настройки, которые правит `install.sh`: модель opus, effortLevel xhigh,
  allow-список прав, `Bash(sudo *)` с подтверждением, пуш-уведомления агентов.
