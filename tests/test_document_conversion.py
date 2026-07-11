import io
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from werkzeug.datastructures import FileStorage

import app
from transcription import Options, Transcript


class MarkItDownCliTests(unittest.TestCase):
    def test_document_conversion_uses_markitdown_cli(self):
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="# Converted\n", stderr=""
        )

        with (
            patch.object(app, "find_markitdown_cli", return_value="/venv/bin/markitdown"),
            patch.object(app.subprocess, "run", return_value=completed) as run,
        ):
            result = app.convert_with_markitdown_cli(Path("document.pdf"))

        self.assertEqual(result, "# Converted\n")
        run.assert_called_once_with(
            ["/venv/bin/markitdown", "document.pdf"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_cli_failure_reports_last_error_line(self):
        completed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="details\ninvalid PDF\n"
        )

        with (
            patch.object(app, "find_markitdown_cli", return_value="markitdown"),
            patch.object(app.subprocess, "run", return_value=completed),
        ):
            with self.assertRaisesRegex(RuntimeError, "invalid PDF"):
                app.convert_with_markitdown_cli(Path("document.pdf"))


class ConversionRoutingTests(unittest.TestCase):
    def test_pdf_uses_cli_route(self):
        upload = FileStorage(stream=io.BytesIO(b"PDF"), filename="report.pdf")

        with patch.object(
            app, "convert_with_markitdown_cli", return_value="# Report\n"
        ) as convert:
            result = app.convert_single_file(upload, Options())

        self.assertEqual(result["status"], "ok")
        self.addCleanup(app.shutil.rmtree, app.temp_dir_for(result["id"]), True)
        convert.assert_called_once()
        self.assertEqual(convert.call_args.args[0].suffix, ".pdf")

    def test_audio_does_not_use_cli_route(self):
        upload = FileStorage(stream=io.BytesIO(b"audio"), filename="meeting.mp3")
        transcript = Transcript(
            text="Meeting notes", language="en", engine="openai", model="test"
        )

        with (
            patch.object(app, "convert_with_markitdown_cli") as convert,
            patch.object(app, "transcribe", return_value=transcript),
            patch.object(app, "render_markdown", return_value="# Meeting\n"),
        ):
            result = app.convert_single_file(upload, Options())

        self.assertEqual(result["status"], "ok")
        self.addCleanup(app.shutil.rmtree, app.temp_dir_for(result["id"]), True)
        convert.assert_not_called()


if __name__ == "__main__":
    unittest.main()
