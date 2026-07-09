# Curated Skills Marketplace

A repo-ready Codex marketplace containing `skills-audit`, a privacy-safe inventory and token-footprint reporter for Skills and Plugins.

## Install

The repository is private, so authenticate Git/GitHub access before installing. The audit script requires Python 3.9 or newer and has no third-party Python dependencies.

### Codex — marketplace plugin

Codex supports this repository as a Git marketplace. The commands below were verified against the installed `codex plugin` help:

```bash
codex plugin marketplace add adibirzu/curated-skills-marketplace --ref v0.1.1
codex plugin add skills-audit@curated-skills
codex plugin list
```

Start a new Codex thread after installation so the new skill is discovered. Ask Codex to `Use $audit-skills-plugins to audit my installed skills and plugins.`

For a local checkout instead of the Git marketplace:

```bash
codex plugin marketplace add /absolute/path/to/curated-skills-marketplace
codex plugin add skills-audit@curated-skills
```

### Cursor — portable Agent Skill

This repository is not published as a native Cursor Marketplace plugin. Install its portable skill directory at user scope:

```bash
gh repo clone adibirzu/curated-skills-marketplace
cd curated-skills-marketplace
mkdir -p ~/.cursor/skills
cp -R plugins/skills-audit/skills/audit-skills-plugins ~/.cursor/skills/
```

For project-only installation, copy it to the target repository instead:

```bash
mkdir -p /path/to/project/.cursor/skills
cp -R plugins/skills-audit/skills/audit-skills-plugins \
  /path/to/project/.cursor/skills/
```

Reopen the workspace or start a new Agent chat, then invoke `/audit-skills-plugins` or ask Cursor to audit your skills and plugins. Cursor also supports the equivalent `.agents/skills/` locations. See the official [Cursor Agent Skills documentation](https://cursor.com/docs/skills).

### Claude Code — portable standalone Skill

This repository does not currently include a Claude plugin-marketplace manifest. Install the portable skill at personal scope:

```bash
gh repo clone adibirzu/curated-skills-marketplace
cd curated-skills-marketplace
mkdir -p ~/.claude/skills
cp -R plugins/skills-audit/skills/audit-skills-plugins ~/.claude/skills/
```

For project-only installation:

```bash
mkdir -p /path/to/project/.claude/skills
cp -R plugins/skills-audit/skills/audit-skills-plugins \
  /path/to/project/.claude/skills/
```

Invoke `/audit-skills-plugins` in Claude Code. If the top-level `skills` directory did not exist when Claude started, restart Claude Code once so it can watch the directory. See Anthropic's official [Claude Code Skills documentation](https://code.claude.com/docs/en/slash-commands).

### Updating Cursor or Claude copies

Pull the reviewed repository update, inspect the diff, and replace the copied skill directory. Do not overwrite a locally modified copy without reviewing or backing up those changes.

The full plugin format is currently Codex-specific. Cursor and Claude receive the same `SKILL.md`, script, and curation policy through their standard portable-skill directories.

By default, the reporter scans standard user and current-project skill locations for Codex, Cursor, Claude, and the shared `.agents/skills/` convention. Measured session-token totals remain Codex-specific because only Codex session logs are parsed.

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
