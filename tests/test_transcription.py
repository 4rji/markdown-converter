import unittest

from transcription import (
    DIARIZE_ENGINE,
    LOCAL_ENGINE,
    Segment,
    Transcript,
    render_markdown,
    transcription_status,
    validate_options,
)


class TranscriptionTests(unittest.TestCase):
    def test_defaults_to_regular_cloud_transcription(self):
        options = validate_options({})
        self.assertEqual(options.engine, "openai")
        self.assertEqual(options.language, "auto")
        self.assertFalse(options.include_timestamps)

    def test_regular_cloud_rejects_timestamps(self):
        with self.assertRaisesRegex(ValueError, "not supported"):
            validate_options({"transcription_engine": "openai", "include_timestamps": "true"})

    def test_diarized_markdown_normalizes_speakers_and_timestamps(self):
        result = Transcript(
            "hello there", "en", DIARIZE_ENGINE, "gpt-4o-transcribe-diarize",
            [Segment("Hello", 1.2, 2.0, "speaker_0"), Segment("Hi", 65, 66, "speaker_1")],
        )
        markdown = render_markdown(result, True)
        self.assertIn("**Speaker A:** [00:00:01] Hello", markdown)
        self.assertIn("**Speaker B:** [00:01:05] Hi", markdown)

    def test_local_markdown_keeps_segments_as_paragraphs(self):
        result = Transcript("One Two", "en", LOCAL_ENGINE, "large-v3-turbo", [Segment("One", 0, 1), Segment("Two", 2, 3)])
        self.assertIn("One\n\nTwo", render_markdown(result, False))

    def test_status_exposes_local_runtime_state(self):
        local = transcription_status()["local"]
        self.assertIn("loaded", local)
        self.assertIn("state", local)


if __name__ == "__main__":
    unittest.main()
