import json
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


if __name__ == "__main__":
    unittest.main()
