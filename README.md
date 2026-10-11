# Curated Skills Marketplace

A repo-ready Codex marketplace containing `skills-audit`, a privacy-safe inventory and token-footprint reporter, and `just-do-it`, a guarded autonomous delivery skill exposed as `$jd`.

## Install

The repository is public. Use its explicit HTTPS URL to avoid SSH host-key and key-distribution requirements. No GitHub credentials are required for installation. The audit script requires Python 3.9 or newer and has no third-party Python dependencies.

### Codex — marketplace plugin

Codex supports this repository as a Git marketplace. The commands below were verified against the installed `codex plugin` help:

```bash
codex plugin marketplace add adibirzu/curated-skills-marketplace --ref v0.2.1
codex plugin add skills-audit@curated-skills
codex plugin add just-do-it@curated-skills
codex plugin list
```

Start a new Codex thread after installation so the new skills are discovered:

- Ask Codex to `Use $audit-skills-plugins to audit my installed skills and plugins.`
- Invoke Just Do It with `$jd`, for example: `Use $jd to deliver this goal through verified completion.`

The marketplace/plugin name is `just-do-it`; the skill name exposed to the agent is `jd`.

For JD execution modes, review requirements, and execution budgets, follow the
[canonical skill contract](plugins/just-do-it/skills/jd/SKILL.md). Before using a current checkout
or portable copy, inspect its [payload provenance](plugins/just-do-it/UPSTREAM.json) and
[release gates](plugins/just-do-it/skills/jd/assets/jd-release.json); a historical reviewed snapshot
does not establish acceptance of changed bytes.

If you previously installed the marketplace at `v0.1.1`, that pinned snapshot cannot contain Just Do It. Move to the reviewed `v0.2.1` snapshot:

```bash
codex plugin marketplace remove curated-skills
codex plugin marketplace add adibirzu/curated-skills-marketplace --ref v0.2.1
codex plugin add just-do-it@curated-skills
```

Installing the plugin is enough to use `$jd`. Its optional named Codex roles are inert templates until you explicitly run their installer from a trusted checkout. That optional installer requires Python 3.11 or newer:

```bash
python3.11 plugins/just-do-it/skills/jd/scripts/install_codex_roles.py check
python3.11 plugins/just-do-it/skills/jd/scripts/install_codex_roles.py install
```

Review the proposed global Codex configuration change before running `install`; the installer creates private backups, refuses unmanaged collisions and symlinks, and writes atomically.

For a local checkout instead of the Git marketplace:

```bash
codex plugin marketplace add /absolute/path/to/curated-skills-marketplace
codex plugin add skills-audit@curated-skills
codex plugin add just-do-it@curated-skills
```

### Cursor — portable Agent Skill

This repository is not published as a native Cursor Marketplace plugin. Install its portable skill directory at user scope:

```bash
git clone https://github.com/adibirzu/curated-skills-marketplace.git
cd curated-skills-marketplace
mkdir -p ~/.cursor/skills
cp -R plugins/skills-audit/skills/audit-skills-plugins ~/.cursor/skills/
cp -R plugins/just-do-it/skills/jd ~/.cursor/skills/
```

For project-only installation, copy it to the target repository instead:

```bash
mkdir -p /path/to/project/.cursor/skills
cp -R plugins/skills-audit/skills/audit-skills-plugins \
  /path/to/project/.cursor/skills/
cp -R plugins/just-do-it/skills/jd /path/to/project/.cursor/skills/
```

Reopen the workspace or start a new Agent chat, then invoke `/audit-skills-plugins` or `/jd`. Cursor also supports the equivalent `.agents/skills/` locations. See the official [Cursor Agent Skills documentation](https://cursor.com/docs/skills).

### Claude Code — HTTPS marketplace plugin

Use the explicit HTTPS Git URL. Do not use the `adibirzu/curated-skills-marketplace` shorthand in environments that default GitHub clones to SSH:

```text
/plugin marketplace add https://github.com/adibirzu/curated-skills-marketplace.git#v0.2.1
/plugin install skills-audit@curated-skills
/plugin install just-do-it@curated-skills
/reload-plugins
```

After reloading, invoke `/just-do-it:jd` for Just Do It or `/skills-audit:audit-skills-plugins` for the audit workflow. Claude namespaces marketplace skills by plugin name.

The SSH error `No ED25519 host key is known for github.com` means the shorthand selected SSH before Claude could read the marketplace. The public HTTPS command above avoids `known_hosts` and does not require GitHub authentication.

For a standalone-skill installation instead of Claude's plugin marketplace, clone over HTTPS and copy the skills at personal scope:

```bash
git clone https://github.com/adibirzu/curated-skills-marketplace.git
cd curated-skills-marketplace
mkdir -p ~/.claude/skills
cp -R plugins/skills-audit/skills/audit-skills-plugins ~/.claude/skills/
cp -R plugins/just-do-it/skills/jd ~/.claude/skills/
```

For project-only installation:

```bash
mkdir -p /path/to/project/.claude/skills
cp -R plugins/skills-audit/skills/audit-skills-plugins \
  /path/to/project/.claude/skills/
cp -R plugins/just-do-it/skills/jd /path/to/project/.claude/skills/
```

Invoke `/audit-skills-plugins` or `/jd` in Claude Code. If the top-level `skills` directory did not exist when Claude started, restart Claude Code once so it can watch the directory. See Anthropic's official [Claude Code Skills documentation](https://code.claude.com/docs/en/slash-commands).

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
python3 /path/to/plugin-creator/scripts/validate_plugin.py plugins/just-do-it
python3 /path/to/skill-creator/scripts/quick_validate.py \
  plugins/skills-audit/skills/audit-skills-plugins
python3 /path/to/skill-creator/scripts/quick_validate.py \
  plugins/just-do-it/skills/jd
```
