from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_python_licenses import markdown_report
from prune_python_distribution import remove_distribution


class ReleaseToolTests(unittest.TestCase):
    def test_prune_removes_only_recorded_distribution_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            site_packages = Path(temporary)
            package_file = site_packages / "demo" / "__init__.py"
            package_file.parent.mkdir()
            package_file.write_text("", encoding="utf-8")
            keep_file = site_packages / "keep.py"
            keep_file.write_text("keep", encoding="utf-8")
            dist_info = site_packages / "demo-1.0.dist-info"
            dist_info.mkdir()
            record = dist_info / "RECORD"
            record.write_text(
                "demo/__init__.py,,\ndemo-1.0.dist-info/RECORD,,\n",
                encoding="utf-8",
            )

            removed = remove_distribution(site_packages, "demo")

            self.assertEqual(len(removed), 2)
            self.assertFalse(package_file.exists())
            self.assertTrue(keep_file.exists())

    def test_inventory_uses_public_display_path(self) -> None:
        report = markdown_report([], "audiosep/env/Lib/site-packages")
        self.assertIn("audiosep/env/Lib/site-packages", report)
        self.assertNotIn("C:\\Users", report)


if __name__ == "__main__":
    unittest.main()
