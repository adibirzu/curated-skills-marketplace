import json
import hashlib
import re
import unittest
from pathlib import Path


CATALOG = Path(__file__).parents[1] / "catalog" / "external-projects.json"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class ExternalCatalogTests(unittest.TestCase):
    def test_catalog_is_pinned_unique_and_review_only(self):
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        projects = data["projects"]
        repositories = [project["repository"] for project in projects]

        self.assertEqual(len(repositories), len(set(repositories)))
        self.assertGreater(len(projects), 0)
        for project in projects:
            self.assertTrue(project["repository"].startswith("https://github.com/"))
            self.assertRegex(project["revision"], FULL_SHA)
            self.assertEqual(project["status"], "review-required")
            self.assertIn("source-review-pending", project["review_reasons"])
            self.assertTrue(project["license"])

    def test_marketplace_contains_installable_just_do_it_plugin(self):
        root = Path(__file__).parents[1]
        marketplace = json.loads(
            (root / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
        )
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}

        self.assertIn("just-do-it", entries)
        self.assertEqual(entries["just-do-it"]["policy"]["installation"], "AVAILABLE")
        source_path = entries["just-do-it"]["source"]["path"]
        plugin_root = root / source_path
        self.assertTrue((plugin_root / ".codex-plugin" / "plugin.json").is_file())
        self.assertTrue((plugin_root / "skills" / "jd" / "SKILL.md").is_file())

        upstream = json.loads((plugin_root / "UPSTREAM.json").read_text(encoding="utf-8"))
        manifest_digest = hashlib.sha256(
            (plugin_root / ".codex-plugin" / "plugin.json").read_bytes()
        ).hexdigest()
        skill_digest = hashlib.sha256(
            (plugin_root / "skills" / "jd" / "SKILL.md").read_bytes()
        ).hexdigest()
        self.assertEqual(manifest_digest, upstream["manifest_sha256"])
        self.assertEqual(skill_digest, upstream["skill_sha256"])
        self.assertEqual(upstream["status"], "validation-pending")
        historical = upstream["historical_upstream"]
        self.assertRegex(historical["revision"], FULL_SHA)
        self.assertEqual(historical["revision_status"], "released-main")
        self.assertEqual(historical["status"], "vendored-reviewed")
        self.assertNotEqual(historical["skill_sha256"], skill_digest)
        self.assertEqual(upstream["native_provenance"]["evidence_class"], "unverified")
        release = json.loads(
            (plugin_root / "skills" / "jd" / "assets" / "jd-release.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(release["status"], "validation-pending")
        self.assertEqual(release["gates"], {
            "skill_validation": False,
            "contract_tests": False,
            "strict_config": False,
            "security_scan": False,
            "forward_test": False,
            "distribution_parity": False,
        })

    def test_claude_marketplace_contains_just_do_it_and_skills_audit(self):
        root = Path(__file__).parents[1]
        marketplace = json.loads(
            (root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}

        self.assertEqual(set(entries), {"just-do-it", "skills-audit"})
        self.assertEqual(entries["just-do-it"]["source"], "./plugins/just-do-it")
        self.assertEqual(entries["skills-audit"]["source"], "./plugins/skills-audit")
        self.assertTrue(
            (root / "plugins" / "skills-audit" / ".claude-plugin" / "plugin.json").is_file()
        )


if __name__ == "__main__":
    unittest.main()
