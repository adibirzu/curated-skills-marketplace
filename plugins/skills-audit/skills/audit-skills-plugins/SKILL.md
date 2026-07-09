---
name: audit-skills-plugins
description: Inventory installed Codex skills, plugins, and marketplaces; estimate each skill's static prompt size; summarize measured session token totals without reading prompt bodies; and create a review-only catalog of reusable external projects. Use for skills governance, plugin audits, token-footprint reports, migration planning, marketplace curation, or pre-publication safety checks.
---

# Audit Skills and Plugins

Generate a deterministic, privacy-safe inventory before copying, publishing, or installing skills and plugins.

## Run the audit

Execute the bundled script from this skill directory:

```bash
python3 scripts/skills_report.py --output ./reports
```

The script scans the standard Codex skill, plugin, marketplace, and session locations. Override any location with repeatable `--skill-root` and `--plugin-root` options. Use `--session-limit 0` to omit session totals.

## Interpret token metrics

Keep these metrics distinct:

- `estimated_static_prompt_tokens` is `ceil(UTF-8 bytes / 4)` for a `SKILL.md`. It estimates the context footprint when loaded; it is not billed usage.
- `session_token_usage` comes from Codex `token_count` events and is measured for the session.
- `skill_attribution: unavailable` means the session format does not identify which tokens belong to a skill. Never infer or allocate measured session totals to individual skills.

The script does not export prompts, messages, reasoning, tool inputs or outputs, environment values, or credentials.

## Curate external projects

Read [references/curation-policy.md](references/curation-policy.md) before promoting a candidate. Treat `external-project-candidates.json` as a review queue, not an install list.

Require a public HTTPS repository, immutable commit pin, recognized license, manifest validation, source review, and explicit human approval. Keep remote projects outside the executable marketplace until all gates pass. Do not automatically clone, install, execute, commit, push, or publish candidates.

## Validate the result

Confirm all of the following:

1. The Markdown report labels per-skill tokens as estimates.
2. Session identifiers are hashed and no prompt text appears.
3. Absolute local marketplace paths are redacted.
4. Every external project is either `review-required` or `eligible-for-review`; neither status means approved.
5. Plugin and skill validators pass before marketplace publication.
