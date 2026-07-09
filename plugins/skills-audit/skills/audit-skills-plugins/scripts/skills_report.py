#!/usr/bin/env python3
"""Create privacy-safe skills, plugins, marketplace, and token reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    tomllib = None


REPORT_JSON = "skills-plugins-report.json"
REPORT_MARKDOWN = "skills-plugins-report.md"
CANDIDATES_JSON = "external-project-candidates.json"
TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
SAFE_PLUGIN_FIELDS = (
    "name",
    "version",
    "description",
    "repository",
    "homepage",
    "license",
)
RISKY_PLUGIN_SURFACES = {
    "mcpServers": "mcp-server",
    "apps": "external-app",
    "hooks": "lifecycle-hook",
}
GITHUB_REPOSITORY = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$")
FULL_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def estimate_tokens(text: str) -> int:
    """Return a transparent, tokenizer-free approximation, never billed usage."""
    return math.ceil(len(text.encode("utf-8")) / 4)


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line or line[:1].isspace():
            continue
        key, value = line.split(":", 1)
        clean_value = value.strip().strip("\"'")
        if key.strip() in {"name", "description", "origin"}:
            result[key.strip()] = clean_value
    return result


def relative_display(path: Path, root: Path) -> tuple[str, bool]:
    try:
        return str(path.resolve().relative_to(root.resolve())), False
    except ValueError:
        return path.name, True


def classify_origin(path: Path) -> str:
    value = str(path)
    if "/.codex/skills/.system/" in value:
        return "codex-system"
    if "/.codex/plugins/cache/openai-" in value or "/.codex/.tmp/bundled-marketplaces/" in value:
        return "openai-plugin"
    if "/.codex/plugins/" in value:
        return "installed-plugin"
    if "/.agents/skills/" in value:
        return "personal-or-ecc"
    return "project-or-custom"


def skill_review_reasons(text: str, skill_dir: Path) -> list[str]:
    lowered = text.lower()
    reasons: set[str] = set()
    if re.search(r"\b(curl|wget)\b|https?://", lowered):
        reasons.add("network-instructions")
    if re.search(r"\b(subprocess|os\.system|shell=true|sudo)\b", lowered):
        reasons.add("shell-execution-instructions")
    if re.search(r"rm\s+-rf|git\s+reset\s+--hard", lowered):
        reasons.add("destructive-command-text")
    if re.search(r"api[_ -]?key|access[_ -]?token|password|secret manager", lowered):
        reasons.add("secret-handling-instructions")
    scripts = skill_dir / "scripts"
    if scripts.is_dir() and any(path.is_file() for path in scripts.rglob("*")):
        reasons.add("bundled-executable-code")
    return sorted(reasons)


def inspect_skill(skill_file: Path, root: Path) -> dict[str, Any]:
    data = skill_file.read_bytes()
    text = data.decode("utf-8", errors="replace")
    metadata = parse_frontmatter(text)
    location, escaped_root = relative_display(skill_file, root)
    reasons = skill_review_reasons(text, skill_file.parent)
    if skill_file.is_symlink():
        reasons.append("symbolic-link")
    if escaped_root:
        reasons.append("path-escapes-scan-root")
    return {
        "name": metadata.get("name") or skill_file.parent.name,
        "description": metadata.get("description", ""),
        "origin": metadata.get("origin") or classify_origin(skill_file),
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "lines": len(text.splitlines()),
        "estimated_static_prompt_tokens": estimate_tokens(text),
        "token_metric": "estimated_static_prompt_tokens",
        "location": location,
        "review_reasons": sorted(set(reasons)),
    }


def discover_skills(roots: Iterable[Path]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for skill_file in sorted(root.rglob("SKILL.md")):
            try:
                item = inspect_skill(skill_file, root)
            except (OSError, UnicodeError):
                continue
            key = (item["name"], item["sha256"])
            if key not in grouped:
                item["locations"] = [item.pop("location")]
                item["copy_count"] = 1
                grouped[key] = item
            else:
                grouped[key]["locations"].append(item["location"])
                grouped[key]["copy_count"] += 1
                grouped[key]["review_reasons"] = sorted(
                    set(grouped[key]["review_reasons"]) | set(item["review_reasons"])
                )
    return sorted(grouped.values(), key=lambda item: (item["name"], item["sha256"]))


def git_revision(start: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    revision = result.stdout.strip().lower()
    return revision if result.returncode == 0 and FULL_COMMIT.fullmatch(revision) else None


def inspect_plugin(manifest: Path, root: Path) -> dict[str, Any]:
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    result = {field: raw[field] for field in SAFE_PLUGIN_FIELDS if isinstance(raw.get(field), str)}
    location, escaped_root = relative_display(manifest, root)
    reasons = [reason for field, reason in RISKY_PLUGIN_SURFACES.items() if field in raw]
    if escaped_root:
        reasons.append("path-escapes-scan-root")
    if manifest.is_symlink():
        reasons.append("symbolic-link")
    skills_path = raw.get("skills")
    if isinstance(skills_path, str) and (skills_path.startswith("/") or ".." in Path(skills_path).parts):
        reasons.append("unsafe-skills-path")
    result.update(
        {
            "location": location,
            "revision": git_revision(manifest.parent),
            "review_reasons": sorted(set(reasons)),
            "manifest_sha256": sha256_bytes(manifest.read_bytes()),
        }
    )
    return result


def discover_plugins(roots: Iterable[Path]) -> list[dict[str, Any]]:
    results: dict[tuple[str, str], dict[str, Any]] = {}
    for root in roots:
        if not root.is_dir():
            continue
        manifests = set(root.rglob(".codex-plugin/plugin.json"))
        for manifest in sorted(manifests):
            try:
                item = inspect_plugin(manifest, root)
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            key = (item.get("name", manifest.parent.parent.name), item["manifest_sha256"])
            results[key] = item
    return sorted(results.values(), key=lambda item: (item.get("name", ""), item["manifest_sha256"]))


def inspect_session(session_file: Path) -> dict[str, Any]:
    session_id = session_file.stem
    timestamp = None
    parent_thread_id = None
    best_tokens = {field: 0 for field in TOKEN_FIELDS}
    malformed_rows = 0
    with session_file.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                malformed_rows += 1
                continue
            payload = row.get("payload")
            if not isinstance(payload, dict):
                continue
            if row.get("type") == "session_meta":
                session_id = str(payload.get("session_id") or payload.get("id") or session_id)
                timestamp = payload.get("timestamp") if isinstance(payload.get("timestamp"), str) else timestamp
                parent_thread_id = payload.get("parent_thread_id") or parent_thread_id
            if row.get("type") != "event_msg" or payload.get("type") != "token_count":
                continue
            info = payload.get("info")
            usage = info.get("total_token_usage") if isinstance(info, dict) else None
            if not isinstance(usage, dict):
                continue
            candidate = {
                field: value if isinstance((value := usage.get(field)), int) and value >= 0 else 0
                for field in TOKEN_FIELDS
            }
            if candidate["total_tokens"] >= best_tokens["total_tokens"]:
                best_tokens = candidate
    return {
        "session_id": session_id,
        "session_id_hash": sha256_bytes(session_id.encode("utf-8"))[:16],
        "timestamp": timestamp,
        "parent_thread_id_hash": (
            sha256_bytes(str(parent_thread_id).encode("utf-8"))[:16] if parent_thread_id else None
        ),
        "tokens": best_tokens,
        "skill_attribution": "unavailable",
        "malformed_rows": malformed_rows,
    }


def discover_sessions(root: Path, limit: int) -> list[dict[str, Any]]:
    if not root.is_dir() or limit == 0:
        return []
    files = sorted(root.rglob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    unique: dict[str, dict[str, Any]] = {}
    for session_file in files[:limit]:
        try:
            item = inspect_session(session_file)
        except OSError:
            continue
        session_id = item.pop("session_id")
        previous = unique.get(session_id)
        if previous is None or item["tokens"]["total_tokens"] > previous["tokens"]["total_tokens"]:
            unique[session_id] = item
    return sorted(unique.values(), key=lambda item: item.get("timestamp") or "", reverse=True)


def parse_marketplace_config(text: str) -> dict[str, dict[str, Any]]:
    if tomllib is not None:
        parsed = tomllib.loads(text)
        marketplaces = parsed.get("marketplaces") if isinstance(parsed, dict) else None
        return marketplaces if isinstance(marketplaces, dict) else {}
    results: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        section = re.fullmatch(r"\[marketplaces\.([A-Za-z0-9_.-]+)\]", line)
        if section:
            current = results.setdefault(section.group(1), {})
            continue
        if current is None or not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
            current[key.strip()] = value[1:-1]
    return results


def safe_marketplace_source(source_type: Any, source: Any) -> Any:
    if source_type == "local" and isinstance(source, str) and Path(source).is_absolute():
        return "<LOCAL_PATH>"
    return source


def inspect_marketplaces(config_path: Path, personal_marketplace: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if config_path.is_file():
        try:
            entries = parse_marketplace_config(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            entries = {}
        if isinstance(entries, dict):
            for name, value in sorted(entries.items()):
                if not isinstance(value, dict):
                    continue
                source_type = value.get("source_type")
                results.append(
                    {
                        "name": name,
                        "source_type": source_type,
                        "source": safe_marketplace_source(source_type, value.get("source")),
                        "kind": "configured-marketplace",
                    }
                )
    if personal_marketplace.is_file():
        try:
            data = json.loads(personal_marketplace.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            data = {}
        plugins = []
        for entry in data.get("plugins", []) if isinstance(data, dict) else []:
            if not isinstance(entry, dict):
                continue
            source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
            plugins.append(
                {
                    "name": entry.get("name"),
                    "source_type": source.get("source"),
                    "path": source.get("path"),
                    "category": entry.get("category"),
                }
            )
        results.append(
            {
                "name": data.get("name", "personal") if isinstance(data, dict) else "personal",
                "kind": "personal-marketplace",
                "plugins": plugins,
            }
        )
    return results


def external_project_candidate(plugin: dict[str, Any]) -> dict[str, Any]:
    repository = plugin.get("repository")
    reasons = set(plugin.get("review_reasons") or [])
    if not isinstance(repository, str) or not GITHUB_REPOSITORY.fullmatch(repository):
        reasons.add("missing-or-unsupported-repository")
    if not plugin.get("license"):
        reasons.add("missing-license-metadata")
    if not isinstance(plugin.get("revision"), str) or not FULL_COMMIT.fullmatch(plugin["revision"]):
        reasons.add("unpinned-source")
    status = "eligible-for-review" if not reasons else "review-required"
    return {
        "name": plugin.get("name"),
        "repository": repository,
        "revision": plugin.get("revision"),
        "license": plugin.get("license"),
        "status": status,
        "review_reasons": sorted(reasons),
        "source_manifest_sha256": plugin.get("manifest_sha256"),
    }


def build_report(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    skills = discover_skills([Path(value).expanduser() for value in args.skill_root])
    plugins = discover_plugins([Path(value).expanduser() for value in args.plugin_root])
    sessions = discover_sessions(Path(args.session_root).expanduser(), args.session_limit)
    marketplaces = inspect_marketplaces(
        Path(args.codex_config).expanduser(), Path(args.marketplace).expanduser()
    )
    candidates = [
        external_project_candidate(plugin)
        for plugin in plugins
        if isinstance(plugin.get("repository"), str)
    ]
    report = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "per_skill_token_usage": "estimated",
            "estimate_formula": "ceil(UTF-8 bytes / 4)",
            "measured_session_tokens": "maximum total_token_usage event per unique session",
            "skill_attribution": "unavailable in Codex session logs",
            "privacy": "message, prompt, tool output, environment, and credential contents are not exported",
        },
        "summary": {
            "unique_skills": len(skills),
            "skill_copies": sum(item["copy_count"] for item in skills),
            "plugins": len(plugins),
            "marketplaces": len(marketplaces),
            "sessions_inspected": len(sessions),
            "external_project_candidates": len(candidates),
        },
        "skills": skills,
        "plugins": plugins,
        "marketplaces": marketplaces,
        "session_token_usage": sessions,
    }
    return report, candidates


def render_markdown(report: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    summary = report["summary"]
    lines = [
        "# Skills and Plugins Audit",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Unique skill versions: {summary['unique_skills']}",
        f"- Skill copies discovered: {summary['skill_copies']}",
        f"- Plugins: {summary['plugins']}",
        f"- Marketplaces: {summary['marketplaces']}",
        f"- Sessions inspected: {summary['sessions_inspected']}",
        f"- External project candidates: {summary['external_project_candidates']}",
        "",
        "## Token methodology",
        "",
        "Codex session logs provide measured session totals but no trustworthy per-skill attribution. ",
        "Per-skill values below are static prompt-size estimates using `ceil(UTF-8 bytes / 4)`; ",
        "they are not billed usage. Prompt, message, tool-output, environment, and credential contents are never exported.",
        "",
        "## Largest skill prompts",
        "",
        "| Skill | Estimated tokens | Copies | Review flags |",
        "|---|---:|---:|---|",
    ]
    largest = sorted(
        report["skills"], key=lambda item: item["estimated_static_prompt_tokens"], reverse=True
    )[:50]
    for item in largest:
        flags = ", ".join(item["review_reasons"]) or "none"
        lines.append(
            f"| {item['name']} | {item['estimated_static_prompt_tokens']} | {item['copy_count']} | {flags} |"
        )
    lines.extend(
        [
            "",
            "## Plugins",
            "",
            "| Plugin | Version | Repository | Review flags |",
            "|---|---|---|---|",
        ]
    )
    for item in report["plugins"]:
        flags = ", ".join(item["review_reasons"]) or "none"
        lines.append(
            f"| {item.get('name', '')} | {item.get('version', '')} | {item.get('repository', '')} | {flags} |"
        )
    lines.extend(
        [
            "",
            "## External project curation queue",
            "",
            "No candidate is installed or executed by this report. `eligible-for-review` still requires human approval.",
            "",
            "| Project | Status | Pin | Review reasons |",
            "|---|---|---|---|",
        ]
    )
    for item in candidates:
        reasons = ", ".join(item["review_reasons"]) or "none"
        revision = item.get("revision") or "unavailable"
        lines.append(f"| {item.get('name', '')} | {item['status']} | {revision} | {reasons} |")
    return "\n".join(lines) + "\n"


def default_skill_roots() -> list[str]:
    home = Path.home()
    return [str(home / ".codex" / "skills"), str(home / ".agents" / "skills"), str(home / ".codex" / "plugins")]


def default_plugin_roots() -> list[str]:
    home = Path.home()
    return [str(home / ".codex" / "plugins"), str(home / "plugins")]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--skill-root", action="append", help="Skill root; repeatable")
    result.add_argument("--plugin-root", action="append", help="Plugin root; repeatable")
    result.add_argument("--session-root", default=str(Path.home() / ".codex" / "sessions"))
    result.add_argument("--session-limit", type=int, default=100)
    result.add_argument("--codex-config", default=str(Path.home() / ".codex" / "config.toml"))
    result.add_argument("--marketplace", default=str(Path.home() / ".agents" / "plugins" / "marketplace.json"))
    result.add_argument("--output", default="./reports")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.session_limit < 0 or args.session_limit > 10_000:
        parser().error("--session-limit must be between 0 and 10000")
    args.skill_root = args.skill_root or default_skill_roots()
    args.plugin_root = args.plugin_root or default_plugin_roots()
    report, candidates = build_report(args)
    output = Path(args.output).expanduser()
    output.mkdir(parents=True, exist_ok=True)
    (output / REPORT_JSON).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / REPORT_MARKDOWN).write_text(render_markdown(report, candidates), encoding="utf-8")
    (output / CANDIDATES_JSON).write_text(
        json.dumps({"schema_version": "1.0.0", "projects": candidates}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {REPORT_JSON}, {REPORT_MARKDOWN}, and {CANDIDATES_JSON} to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
