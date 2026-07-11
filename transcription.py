"""Selectable cloud and local audio transcription backends."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CLOUD_ENGINE = "openai"
DIARIZE_ENGINE = "openai_diarize"
LOCAL_ENGINE = "local_whisper"
ENGINES = {CLOUD_ENGINE, DIARIZE_ENGINE, LOCAL_ENGINE}
LANGUAGES = {"auto": None, "en": "en", "es": "es"}
LOCAL_MODEL_NAME = "large-v3-turbo"
OPENAI_MODELS = {
    CLOUD_ENGINE: "gpt-4o-transcribe",
    DIARIZE_ENGINE: "gpt-4o-transcribe-diarize",
}
MAX_CLOUD_BYTES = 24_000_000
CHUNK_SECONDS = 20 * 60


@dataclass
class Segment:
    text: str
    start: float | None = None
    end: float | None = None
    speaker: str | None = None


@dataclass
class Transcript:
    text: str
    language: str | None
    engine: str
    model: str
    segments: list[Segment] = field(default_factory=list)


@dataclass(frozen=True)
class Options:
    engine: str = CLOUD_ENGINE
    language: str = "auto"
    context: str = ""
    include_timestamps: bool = False


_model = None
_model_lock = threading.Lock()
_local_failure: str | None = None
_local_state = "not_loaded"


def _set_local_state(state: str) -> None:
    global _local_state
    _local_state = state
    print(f"[transcription] Local Whisper state: {state}", flush=True)


def validate_options(form: Any) -> Options:
    engine = (form.get("transcription_engine") or CLOUD_ENGINE).strip()
    language = (form.get("transcription_language") or "auto").strip()
    context = (form.get("transcription_context") or "").strip()
    timestamp_value = (form.get("include_timestamps") or "false").lower()
    if engine not in ENGINES:
        raise ValueError("Invalid transcription engine")
    if language not in LANGUAGES:
        raise ValueError("Invalid transcription language")
    if len(context) > 500:
        raise ValueError("Technical vocabulary/context must be 500 characters or less")
    if timestamp_value not in {"true", "false", "1", "0", "on", "off"}:
        raise ValueError("Invalid timestamps setting")
    include_timestamps = timestamp_value in {"true", "1", "on"}
    if engine == CLOUD_ENGINE and include_timestamps:
        raise ValueError("Timestamps are not supported by GPT-4o Transcribe")
    return Options(engine, language, context, include_timestamps)


def _basic_local_status() -> dict[str, Any]:
    if _local_failure:
        return _status(False, "cuda", _local_failure)
    if shutil.which("ffmpeg") is None:
        return _status(False, None, "FFmpeg is not installed")
    model_value = os.environ.get("WHISPER_MODEL_PATH", "").strip()
    if not model_value:
        return _status(False, None, "WHISPER_MODEL_PATH is not configured")
    if not Path(model_value).expanduser().is_dir():
        return _status(False, None, "Configured model directory was not found")
    try:
        import ctranslate2
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError:
        return _status(False, None, "faster-whisper is not installed")
    try:
        if ctranslate2.get_cuda_device_count() < 1:
            return _status(False, "cpu", "No NVIDIA CUDA device was detected")
    except Exception:
        return _status(False, None, "CUDA availability could not be determined")
    return _status(True, "cuda", None)


def _status(available: bool, device: str | None, reason: str | None) -> dict[str, Any]:
    return {
        "available": available,
        "model": LOCAL_MODEL_NAME,
        "device": device,
        "loaded": _model is not None,
        "state": _local_state,
        "unavailable_reason": reason,
    }


def transcription_status() -> dict[str, Any]:
    return {
        "cloud": {"configured": bool(os.environ.get("OPENAI_API_KEY", "").strip())},
        "local": _basic_local_status(),
    }


def _run_ffmpeg(args: list[str], timeout: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for audio and video uploads")
    try:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", *args],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Audio normalization timed out") from exc
    if result.returncode:
        detail = result.stderr.strip().splitlines()
        raise ValueError(f"Unsupported or invalid audio: {detail[-1] if detail else 'FFmpeg failed'}")


def normalize_audio(input_path: Path, work_dir: Path, timeout: int) -> Path:
    """Extract mono speech audio into a compact API-supported MP3."""
    output = work_dir / "normalized.mp3"
    _run_ffmpeg([
        "-i", str(input_path), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "libmp3lame", "-b:a", "64k", "-y", str(output),
    ], timeout)
    if not output.is_file():
        raise ValueError("The uploaded file does not contain a usable audio track")
    return output


def _cloud_parts(normalized: Path, work_dir: Path, timeout: int) -> list[Path]:
    if normalized.stat().st_size <= MAX_CLOUD_BYTES:
        return [normalized]
    pattern = work_dir / "chunk-%04d.mp3"
    _run_ffmpeg([
        "-i", str(normalized), "-f", "segment", "-segment_time", str(CHUNK_SECONDS),
        "-reset_timestamps", "1", "-c", "copy", str(pattern),
    ], timeout)
    parts = sorted(work_dir.glob("chunk-*.mp3"))
    if not parts or any(part.stat().st_size > MAX_CLOUD_BYTES for part in parts):
        raise RuntimeError("Audio could not be split below the OpenAI 25 MB limit")
    return parts


def _duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return float(CHUNK_SECONDS)
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return float(CHUNK_SECONDS)


def _value(item: Any, name: str, default=None):
    return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)


def transcribe_cloud(normalized: Path, work_dir: Path, options: Options, timeout: int) -> Transcript:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError("OpenAI transcription is not configured. Set OPENAI_API_KEY on the server.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai Python package is not installed") from exc

    client = OpenAI()
    model = OPENAI_MODELS[options.engine]
    all_text: list[str] = []
    all_segments: list[Segment] = []
    detected_language = None
    offset = 0.0
    for part in _cloud_parts(normalized, work_dir, timeout):
        kwargs: dict[str, Any] = {"model": model, "response_format": "json"}
        if options.engine == DIARIZE_ENGINE:
            kwargs.update(response_format="diarized_json", chunking_strategy="auto")
        if LANGUAGES[options.language]:
            kwargs["language"] = LANGUAGES[options.language]
        # The API does not support prompts for the diarization model.
        if options.context and options.engine != DIARIZE_ENGINE:
            kwargs["prompt"] = options.context
        with part.open("rb") as audio_file:
            response = client.audio.transcriptions.create(file=audio_file, **kwargs)
        text = (_value(response, "text", "") or "").strip()
        if text:
            all_text.append(text)
        detected_language = detected_language or _value(response, "language")
        for segment in _value(response, "segments", []) or []:
            start = _value(segment, "start")
            end = _value(segment, "end")
            all_segments.append(Segment(
                text=(_value(segment, "text", "") or "").strip(),
                start=(float(start) + offset) if start is not None else None,
                end=(float(end) + offset) if end is not None else None,
                speaker=_value(segment, "speaker"),
            ))
        offset += _duration(part)
    return Transcript("\n\n".join(all_text) or "[No speech detected]", detected_language, options.engine, model, all_segments)


def _get_local_model():
    global _model, _local_failure
    if _model is not None:
        return _model
    status = _basic_local_status()
    if not status["available"]:
        raise RuntimeError(f"Local Whisper is unavailable: {status['unavailable_reason']}")
    with _model_lock:
        if _model is not None:
            return _model
        _set_local_state("loading")
        try:
            from faster_whisper import WhisperModel
            path = str(Path(os.environ["WHISPER_MODEL_PATH"]).expanduser().resolve())
            _model = WhisperModel(path, device="cuda", compute_type="float16", local_files_only=True)
        except Exception as exc:
            _local_failure = f"Model load failed: {str(exc) or type(exc).__name__}"
            _set_local_state("error")
            raise RuntimeError(f"Local Whisper is unavailable: {_local_failure}") from exc
        _set_local_state("ready")
    return _model


def transcribe_local(normalized: Path, options: Options, beam_size: int) -> Transcript:
    model = _get_local_model()
    _set_local_state("transcribing")
    try:
        segments_iter, info = model.transcribe(
            str(normalized), language=LANGUAGES[options.language], initial_prompt=options.context or None,
            beam_size=beam_size, vad_filter=True,
        )
        # faster-whisper is lazy: iterating the generator performs the actual
        # CUDA inference. Do not return before fully consuming it.
        segments = [Segment(s.text.strip(), float(s.start), float(s.end)) for s in segments_iter if s.text.strip()]
    finally:
        _set_local_state("ready")
    text = " ".join(segment.text for segment in segments) or "[No speech detected]"
    return Transcript(text, getattr(info, "language", None), LOCAL_ENGINE, LOCAL_MODEL_NAME, segments)


def transcribe(input_path: Path, work_dir: Path, options: Options, timeout: int, beam_size: int) -> Transcript:
    if options.engine == LOCAL_ENGINE:
        _set_local_state("normalizing")
    try:
        normalized = normalize_audio(input_path, work_dir, timeout)
    except Exception:
        if options.engine == LOCAL_ENGINE:
            _set_local_state("ready" if _model is not None else "not_loaded")
        raise
    if options.engine == LOCAL_ENGINE:
        return transcribe_local(normalized, options, beam_size)
    return transcribe_cloud(normalized, work_dir, options, timeout)


def _timestamp(seconds: float | None) -> str:
    total = max(0, int(seconds or 0))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def _speaker_names(segments: list[Segment]) -> dict[str, str]:
    names: dict[str, str] = {}
    for segment in segments:
        key = str(segment.speaker or "Unknown")
        if key not in names:
            index = len(names)
            names[key] = f"Speaker {chr(65 + index)}" if index < 26 else f"Speaker {index + 1}"
    return names


def render_markdown(result: Transcript, include_timestamps: bool) -> str:
    lines: list[str] = []
    if result.engine == DIARIZE_ENGINE and result.segments:
        names = _speaker_names(result.segments)
        for segment in result.segments:
            prefix = f"[{_timestamp(segment.start)}] " if include_timestamps else ""
            lines.extend([f"**{names[str(segment.speaker or 'Unknown')]}:** {prefix}{segment.text}", ""])
    elif result.engine == LOCAL_ENGINE and result.segments:
        for segment in result.segments:
            prefix = f"[{_timestamp(segment.start)}] " if include_timestamps else ""
            lines.extend([f"{prefix}{segment.text}", ""])
    else:
        paragraphs = [p.strip() for p in result.text.split("\n") if p.strip()]
        lines.extend(paragraphs or ["[No speech detected]"])
        lines.append("")
    return "\n".join(lines)
