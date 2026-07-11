import tempfile
import unittest
from pathlib import Path

from env_loader import apply_env, parse_env_file


class ParseEnvFileTests(unittest.TestCase):
    def _parse(self, content: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(content, encoding="utf-8")
            return parse_env_file(path)

    def test_parses_values_and_skips_comments_and_blanks(self):
        values = self._parse(
            "# comment\n"
            "\n"
            "WHISPER_MODEL_PATH=/opt/whisper-models/large-v3-turbo\n"
            "CUDA_VISIBLE_DEVICES=0\n"
            "NOT A KEY VALUE LINE\n"
        )
        self.assertEqual(
            values["WHISPER_MODEL_PATH"], "/opt/whisper-models/large-v3-turbo"
        )
        self.assertEqual(values["CUDA_VISIBLE_DEVICES"], "0")
        self.assertNotIn("NOT A KEY VALUE LINE", values)

    def test_strips_optional_quotes(self):
        values = self._parse('OPENAI_API_KEY="secret"\nWHISPER_DEVICE=\'cuda\'\n')
        self.assertEqual(values["OPENAI_API_KEY"], "secret")
        self.assertEqual(values["WHISPER_DEVICE"], "cuda")


class ApplyEnvTests(unittest.TestCase):
    def test_fills_missing_variables(self):
        environ = {}
        needs_reexec = apply_env({"WHISPER_MODEL_PATH": "/models"}, environ)
        self.assertEqual(environ["WHISPER_MODEL_PATH"], "/models")
        self.assertFalse(needs_reexec)

    def test_never_overrides_existing_variables(self):
        environ = {"WHISPER_MODEL_PATH": "/from-systemd"}
        apply_env({"WHISPER_MODEL_PATH": "/from-dotenv"}, environ)
        self.assertEqual(environ["WHISPER_MODEL_PATH"], "/from-systemd")

    def test_skips_empty_values(self):
        environ = {}
        apply_env({"OPENAI_API_KEY": ""}, environ)
        self.assertNotIn("OPENAI_API_KEY", environ)

    def test_new_ld_library_path_requires_reexec(self):
        environ = {}
        needs_reexec = apply_env({"LD_LIBRARY_PATH": "/venv/cublas:/venv/cudnn"}, environ)
        self.assertTrue(needs_reexec)
        self.assertEqual(environ["LD_LIBRARY_PATH"], "/venv/cublas:/venv/cudnn")

    def test_ld_library_path_prepends_missing_entries(self):
        environ = {"LD_LIBRARY_PATH": "/usr/lib"}
        needs_reexec = apply_env({"LD_LIBRARY_PATH": "/venv/cublas"}, environ)
        self.assertTrue(needs_reexec)
        self.assertEqual(environ["LD_LIBRARY_PATH"], "/venv/cublas:/usr/lib")

    def test_ld_library_path_already_present_needs_no_reexec(self):
        environ = {"LD_LIBRARY_PATH": "/venv/cublas:/venv/cudnn"}
        needs_reexec = apply_env(
            {"LD_LIBRARY_PATH": "/venv/cublas:/venv/cudnn"}, environ
        )
        self.assertFalse(needs_reexec)
        self.assertEqual(environ["LD_LIBRARY_PATH"], "/venv/cublas:/venv/cudnn")


if __name__ == "__main__":
    unittest.main()
