import tempfile
import unittest
from pathlib import Path

from scripts.check_repository_safety import (
    MAX_TEXT_SCAN_BYTES,
    MAX_TRACKED_FILE_BYTES,
    check_paths,
)


class RepositorySafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.repository = Path(self.temp_directory.name)

    def tearDown(self):
        self.temp_directory.cleanup()

    def write_file(self, relative_path: str, content: bytes = b"safe") -> None:
        path = self.repository / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def test_allows_normal_source_and_documentation(self):
        self.write_file("app/main.py", b"print('hello')\n")
        self.write_file("docs/screenshot.png", b"small documentation image")

        self.assertEqual([], check_paths(self.repository, ["app/main.py", "docs/screenshot.png"]))

    def test_rejects_forbidden_directory_and_media_extension(self):
        self.write_file("media/test_sample.mp4")

        findings = check_paths(self.repository, ["media/test_sample.mp4"])

        self.assertTrue(any("forbidden directory" in item for item in findings))
        self.assertTrue(any("forbidden tracked file type '.mp4'" in item for item in findings))

    def test_rejects_model_weight_and_runtime_manifest(self):
        self.write_file("weights/model.safetensors")
        self.write_file("runtime-assets.json")

        findings = check_paths(
            self.repository,
            ["weights/model.safetensors", "runtime-assets.json"],
        )

        self.assertTrue(any(".safetensors" in item for item in findings))
        self.assertTrue(any("generated/runtime file" in item for item in findings))

    def test_rejects_large_tracked_file(self):
        path = self.repository / "large.dat"
        with path.open("wb") as handle:
            handle.truncate(MAX_TRACKED_FILE_BYTES + 1)

        findings = check_paths(self.repository, ["large.dat"])

        self.assertTrue(any("tracked file is" in item for item in findings))

    def test_rejects_private_key_and_local_user_path(self):
        private_key = "-----BEGIN " + "PRIVATE KEY-----\nnot-a-real-key\n"
        local_path = "C:" + "\\Users\\ExampleUser\\Desktop\\clip.mp4\n"
        self.write_file("notes.txt", (private_key + local_path).encode("utf-8"))

        findings = check_paths(self.repository, ["notes.txt"])

        self.assertTrue(any("private key" in item for item in findings))
        self.assertTrue(any("local Windows user path" in item for item in findings))

    def test_rejects_representative_tokens(self):
        github_token = "gh" + "p_" + ("A" * 36)
        hugging_face_token = "hf_" + ("B" * 24)
        self.write_file("config.txt", f"{github_token}\n{hugging_face_token}\n".encode("utf-8"))

        findings = check_paths(self.repository, ["config.txt"])

        self.assertTrue(any("GitHub token" in item for item in findings))
        self.assertTrue(any("Hugging Face token" in item for item in findings))

    def test_rejects_local_agent_notes_and_secret_filenames(self):
        paths = [
            "AGENTS.local.md",
            ".env.local",
            "config/client_secret_desktop.json",
            "certificates/signing.pfx",
        ]
        for path in paths:
            self.write_file(path)

        findings = check_paths(self.repository, paths)

        self.assertTrue(any("AGENTS.local.md" in item for item in findings))
        self.assertTrue(any(".env.local" in item for item in findings))
        self.assertTrue(any("client_secret_desktop.json" in item for item in findings))
        self.assertTrue(any(".pfx" in item for item in findings))

    def test_rejects_additional_media_and_model_extensions(self):
        paths = ["sample.m4v", "sound.m4a", "weights/model.gguf", "weights/model.h5"]
        for path in paths:
            self.write_file(path)

        findings = check_paths(self.repository, paths)

        for suffix in (".m4v", ".m4a", ".gguf", ".h5"):
            self.assertTrue(any(suffix in item for item in findings))

    def test_scans_sensitive_text_larger_than_two_megabytes(self):
        github_token = "gh" + "p_" + ("A" * 36)
        padding_size = (2 * 1024 * 1024) + 1
        self.assertLess(padding_size, MAX_TEXT_SCAN_BYTES)
        self.write_file("large-notes.txt", (b"x" * padding_size) + github_token.encode("utf-8"))

        findings = check_paths(self.repository, ["large-notes.txt"])

        self.assertTrue(any("GitHub token" in item for item in findings))

    def test_scans_utf16_sensitive_text(self):
        private_key = "-----BEGIN " + "PRIVATE KEY-----\nnot-a-real-key\n"
        self.write_file("utf16-notes.txt", private_key.encode("utf-16"))

        findings = check_paths(self.repository, ["utf16-notes.txt"])

        self.assertTrue(any("private key" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
