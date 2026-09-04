from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_python_licenses import audit, markdown_report
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

    def test_license_audit_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "audiosep"
            site_packages = runtime / "env" / "Lib" / "site-packages"
            dist_info = site_packages / "demo-1.0.dist-info"
            dist_info.mkdir(parents=True)
            (site_packages / "outside-license.txt").write_text("private", encoding="utf-8")
            (dist_info / "METADATA").write_text(
                "Name: demo\nVersion: 1.0\nLicense: MIT\n"
                "License-File: ../outside-license.txt\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                audit(site_packages, Path(temporary) / "licenses", runtime)

    def test_license_audit_rejects_linked_dist_info(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "audiosep"
            site_packages = runtime / "env" / "Lib" / "site-packages"
            external = root / "external" / "demo-1.0.dist-info"
            site_packages.mkdir(parents=True)
            external.mkdir(parents=True)
            (external / "METADATA").write_text(
                "Name: demo\nVersion: 1.0\nLicense: MIT\n", encoding="utf-8"
            )
            (external / "LICENSE").write_text("private", encoding="utf-8")
            linked = site_packages / "demo-1.0.dist-info"
            if os.name == "nt":
                result = subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", str(linked), str(external)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if result.returncode != 0:
                    self.skipTest("Windows junction creation is unavailable")
            else:
                linked.symlink_to(external, target_is_directory=True)

            with self.assertRaises(ValueError):
                audit(site_packages, root / "licenses", runtime)


if __name__ == "__main__":
    unittest.main()
