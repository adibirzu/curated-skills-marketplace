import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "plugins"
    / "skills-audit"
    / "skills"
    / "audit-skills-plugins"
    / "scripts"
    / "skills_report.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("skills_report", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillsReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = load_module()

    def test_parse_skill_uses_frontmatter_and_static_estimate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_file = Path(temp_dir) / "demo" / "SKILL.md"
            skill_file.parent.mkdir()
            skill_file.write_text(
                "---\nname: demo-skill\ndescription: Safe demo\n---\n\n# Demo\nDo work.\n",
                encoding="utf-8",
            )

            result = self.report.inspect_skill(skill_file, Path(temp_dir))

            self.assertEqual(result["name"], "demo-skill")
            self.assertEqual(result["description"], "Safe demo")
            self.assertEqual(result["token_metric"], "estimated_static_prompt_tokens")
            self.assertGreater(result["estimated_static_prompt_tokens"], 0)
            self.assertNotIn("content", result)

    def test_discovery_collapses_identical_skill_copies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content = "---\nname: repeated\ndescription: Same\n---\nBody\n"
            for folder in ("first", "second"):
                path = root / folder / "SKILL.md"
                path.parent.mkdir()
                path.write_text(content, encoding="utf-8")

            result = self.report.discover_skills([root])

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["copy_count"], 2)
            self.assertEqual(len(result[0]["locations"]), 2)

    def test_plugin_output_is_allowlisted_and_flags_executable_surfaces(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin = root / "plugin" / ".codex-plugin" / "plugin.json"
            plugin.parent.mkdir(parents=True)
            plugin.write_text(
                json.dumps(
                    {
                        "name": "demo-plugin",
                        "version": "1.0.0",
                        "description": "Demo",
                        "repository": "https://github.com/example/demo",
                        "license": "MIT",
                        "skills": "./skills/",
                        "mcpServers": "./.mcp.json",
                        "env": {"SECRET": "must-not-leak"},
                    }
                ),
                encoding="utf-8",
            )

            result = self.report.inspect_plugin(plugin, root)

            self.assertEqual(result["name"], "demo-plugin")
            self.assertNotIn("env", result)
            self.assertNotIn("must-not-leak", json.dumps(result))
            self.assertIn("mcp-server", result["review_reasons"])

    def test_session_parser_uses_token_events_without_exporting_messages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = Path(temp_dir) / "session.jsonl"
            rows = [
                {
                    "type": "session_meta",
                    "payload": {"id": "session-1", "timestamp": "2026-07-09T00:00:00Z"},
                },
                {
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": "PRIVATE_SENTINEL"},
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "total_token_usage": {
                                "input_tokens": 120,
                                "cached_input_tokens": 80,
                                "output_tokens": 30,
                                "reasoning_output_tokens": 10,
                                "total_tokens": 150,
                            }
                        },
                    },
                },
            ]
            session.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

            result = self.report.inspect_session(session)

            self.assertEqual(result["session_id"], "session-1")
            self.assertEqual(result["tokens"]["total_tokens"], 150)
            self.assertEqual(result["skill_attribution"], "unavailable")
            self.assertNotIn("PRIVATE_SENTINEL", json.dumps(result))

    def test_external_project_requires_repository_license_and_pin(self):
        plugin = {
            "name": "demo",
            "repository": "https://github.com/example/demo",
            "license": "MIT",
            "revision": None,
            "review_reasons": [],
        }

        candidate = self.report.external_project_candidate(plugin)

        self.assertEqual(candidate["status"], "review-required")
        self.assertIn("unpinned-source", candidate["review_reasons"])

        approved = self.report.external_project_candidate({**plugin, "revision": "a" * 40})
        self.assertEqual(approved["status"], "eligible-for-review")

    def test_marketplace_inventory_redacts_absolute_local_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = root / "config.toml"
            config.write_text(
                "[marketplaces.local]\nsource_type = \"local\"\nsource = \"/opt/private/catalog\"\n"
                "[marketplaces.remote]\nsource_type = \"git\"\nsource = \"https://github.com/example/catalog.git\"\n",
                encoding="utf-8",
            )

            results = self.report.inspect_marketplaces(config, root / "missing.json")

            by_name = {item["name"]: item for item in results}
            self.assertEqual(by_name["local"]["source"], "<LOCAL_PATH>")
            self.assertEqual(
                by_name["remote"]["source"], "https://github.com/example/catalog.git"
            )

    def test_cli_writes_json_markdown_and_candidate_catalog(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill = root / "skills" / "demo" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "---\nname: demo\ndescription: Demo skill\n---\nDo work.\n",
                encoding="utf-8",
            )
            output = root / "reports"

            exit_code = self.report.main(
                [
                    "--skill-root",
                    str(root / "skills"),
                    "--plugin-root",
                    str(root / "plugins"),
                    "--session-root",
                    str(root / "sessions"),
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((output / "skills-plugins-report.json").is_file())
            self.assertTrue((output / "skills-plugins-report.md").is_file())
            self.assertTrue((output / "external-project-candidates.json").is_file())
            report = json.loads((output / "skills-plugins-report.json").read_text())
            self.assertEqual(report["methodology"]["per_skill_token_usage"], "estimated")


if __name__ == "__main__":
    unittest.main()
