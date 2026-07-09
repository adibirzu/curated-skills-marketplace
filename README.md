# Curated Skills Marketplace

A repo-ready Codex marketplace containing `skills-audit`, a privacy-safe inventory and token-footprint reporter for Skills and Plugins.

## Generate a local report

```bash
python3 plugins/skills-audit/skills/audit-skills-plugins/scripts/skills_report.py \
  --output ./reports
```

Generated reports are intentionally ignored by Git. Review them locally before sharing: they contain skill/plugin names and measured token totals, but never prompt or message bodies.

The report distinguishes:

- measured session token totals from Codex `token_count` events;
- per-skill static prompt-size estimates using `ceil(UTF-8 bytes / 4)`;
- unavailable per-skill measured attribution, which Codex session logs do not provide.

## Marketplace safety model

`external-project-candidates.json` is a review queue, not an executable dependency list. Remote projects are not added to `.agents/plugins/marketplace.json` until their repository, commit pin, license, code, permissions, manifests, and tests have been reviewed and explicitly approved.

The repository-level [`catalog/external-projects.json`](catalog/external-projects.json) contains a deliberately small, commit-pinned snapshot of external projects currently in use. Every entry remains `review-required`; catalog presence never grants installation or execution approval.

## Validate

```bash
python3 -m unittest discover -s tests -v
python3 /path/to/plugin-creator/scripts/validate_plugin.py plugins/skills-audit
python3 /path/to/skill-creator/scripts/quick_validate.py \
  plugins/skills-audit/skills/audit-skills-plugins
```
