---
name: routing-review
description: Review how model routing and subagents performed over recent sessions (token and price mix per model, agent usage, long-context cost) and propose tweaks to the routing rules. Manual only.
disable-model-invocation: true
---

# Routing review

Runs only when Dmitry asks for it. Reads local transcripts; sends nothing anywhere.

1. Run `python3 ${CLAUDE_SKILL_DIR}/usage-report.py --days 7` (use `--days 1` right after a change to compare). Add `--top 5` for more sessions.
2. Read the tables against these questions:
   - **Cache-read share.** If cache-read dominates the USD column, the cost driver is long contexts re-read every turn, not model choice. Look at the top sessions: which ones ran long, and should they have been split with /clear or /compact?
   - **Model mix.** Is Opus used where a plan or a hard decision justified it, and not for routine work? Is Haiku used for lookups at all (delegations to `quick` or Explore)?
   - **Subagents.** Delegations to `general-purpose` with `(agent default)` model are unrouted; they should have gone to `quick`, `coder`, `reviewer` or `architect`. Note agents that were called but rarely helped.
   - **Escalations.** Many `architect` calls after `coder` runs suggest the plan step was skipped; none at all suggests hard tasks are being ground out on Sonnet.
3. Propose at most five concrete changes to `rules/RULES.md` or the agent files, each with the evidence line it rests on. Do not apply anything without Dmitry's go-ahead.
4. If he approves a change, edit the working clone at `~/.local/share/claude-setup`, commit there, and tell him the push is pending his word.
