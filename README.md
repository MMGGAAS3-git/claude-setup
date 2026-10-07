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
├── agents/                         quick (Haiku), coder, reviewer (Sonnet 5.5), architect (Opus 5.5)
├── skills/routing-review/          ручной разбор маршрутизации + usage-report.py
├── hooks/hooks.json                SessionStart-хук
├── scripts/inject-rules.py         отдаёт RULES.md как additionalContext
└── .mcp.json                       MCP-сервер context7
install.sh                          установщик
NOTICE                              источники заимствований (ECC, MIT)
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
- Настройки, которые правит `install.sh`: модель `opusplan`, effortLevel high
  (+ high для claude-sonnet-5-5 и claude-opus-5-5, если не заданы), allow-список
  прав, `Bash(sudo *)` с подтверждением, пуш-уведомления агентов.

## Маршрутизация моделей

Основная сессия — Sonnet 5.5; `opusplan` включает Opus 5.5 в plan mode. Модель
основной сессии Claude сменить не может, поэтому остальное — делегирование агентам
с зашитой моделью (параметр `model` при вызове не передаётся):

| Ступень | Модель | Агент |
|---|---|---|
| 0 | Haiku 4.5 | `quick`, встроенный Explore |
| 1 | Sonnet 5.5 | основная сессия, `coder`, `reviewer` (только чтение) |
| 2 | Opus 5.5 | plan mode, `architect` (effort xhigh, только чтение) |

Правила выбора ступени, эскалации и делегирования — в `rules/RULES.md`. Fable только
по прямой просьбе; Sonnet 5.0 и Opus 5.0 не используются (Sonnet 5.0 стоит как 5.5).

## Разбор расхода

`/dmitry-core:routing-review` запускает `skills/routing-review/usage-report.py`: по
локальным транскриптам (`~/.claude/projects`) считает токены и цену по API-прайсу
для каждой модели и роли, показывает делегирования и самые дорогие сессии. Ничего не
отправляет, хуков не добавляет, на старте сессии токенов не тратит
(`disable-model-invocation`). Скрипт можно запускать и напрямую:
`python3 plugins/dmitry-core/skills/routing-review/usage-report.py --days 7`.

## Что взято из ECC и что нет

Исследован [affaan-m/ECC](https://github.com/affaan-m/ECC) (MIT). Целиком не ставится:
его 293 скилла, 68 агентов и 94 команды — это порядка 30 тыс. токенов описаний в каждой
сессии, плюс хуки (GateGuard и др.) и собственная система памяти. Взяты идеи: градация
задач по размеру, дисциплина ревью без шума, измерение расхода. Подробности — NOTICE.
