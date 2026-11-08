"""Speech input and output (feature F9).

Speech is not a capability. It is another way to type. What the person says is turned
into text here and handed to the same assistant path that typed text uses, so every
approval gate, boundary check and undo applies to a spoken request exactly as it does
to a typed one. Nothing in this module can approve, send, change or delete anything,
and it has no opinion about what a request means.

Two rules are enforced here rather than left to the interface:

* Nothing is transcribed unless the person armed the session first. Audio that arrives
  while the session is not armed is discarded without being read.
* Audio is never kept. The recording is deleted as soon as it has been turned into text,
  whether or not that worked. Only the words are used, and they appear on screen like
  typed words.

Transcription runs on this computer (faster-whisper). Speaking the answer back uses the
voice built into Windows. Neither sends anything anywhere. Both are optional: if a
piece is missing the person is told in plain words and typing still works.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

#: Answers longer than this are not read out in full; the rest is on screen.
MAX_SPOKEN_CHARS = 600


class NotArmed(Exception):
    """Speech arrived while the session was not armed. The audio was not read."""


class SpeechUnavailable(Exception):
    """Voice cannot be used right now; the message says why, in plain words."""


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path) -> str: ...


class Speaker(Protocol):
    def speak_to_file(self, text: str, out_path: Path) -> None: ...


@dataclass(frozen=True)
class Turn:
    """What reaches the assistant. Voice and typing are the same thing from here on.

    The source is kept only so the interface can speak the reply for a voice turn.
    Nothing downstream of the assistant is told which one it was.
    """

    text: str
    spoken: bool = False


class FasterWhisperTranscriber:
    """Local speech-to-text. The model is loaded the first time it is needed."""

    def __init__(self, model_size: str = "base.en") -> None:
        self._model_size = model_size
        self._model = None
        self._lock = threading.Lock()

    def available(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return False
        return True

    def transcribe(self, audio_path: Path) -> str:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise SpeechUnavailable(
                "Voice typing is not installed on this computer. Typing still works."
            ) from exc
        with self._lock:
            if self._model is None:
                try:
                    self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
                except Exception as exc:  # download/offline failures are common on first use
                    raise SpeechUnavailable(
                        "ARTEMIS could not load the speech model on this computer. "
                        "The first use needs a one-time download. Typing still works."
                    ) from exc
            model = self._model
        try:
            segments, _info = model.transcribe(str(audio_path), vad_filter=True, language="en")
            return " ".join(s.text.strip() for s in segments).strip()
        except Exception as exc:  # an unreadable or damaged recording, or a broken install
            raise SpeechUnavailable(
                "ARTEMIS could not make out that recording. Try again, or type it."
            ) from exc


class WindowsSpeaker:
    """Speaks with the voice built into Windows, to a sound file the page can play."""

    def available(self) -> bool:
        try:
            import win32com.client  # noqa: F401
        except ImportError:
            return False
        return True

    def speak_to_file(self, text: str, out_path: Path) -> None:
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise SpeechUnavailable("This computer has no speech voice ARTEMIS can use.") from exc
        pythoncom.CoInitialize()
        try:
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            stream = win32com.client.Dispatch("SAPI.SpFileStream")
            stream.Open(str(out_path), 3)  # SSFMCreateForWrite
            voice.AudioOutputStream = stream
            voice.Speak(text)
            stream.Close()
        except Exception as exc:
            raise SpeechUnavailable("ARTEMIS could not speak the answer.") from exc
        finally:
            pythoncom.CoUninitialize()


class VoiceSession:
    """Whether the microphone is armed, and the turning of speech into a `Turn`."""

    def __init__(
        self,
        transcriber: Transcriber | None = None,
        speaker: Speaker | None = None,
        audit: Callable[[str, str], None] | None = None,
    ) -> None:
        self._transcriber = transcriber or FasterWhisperTranscriber()
        self._speaker = speaker or WindowsSpeaker()
        self._audit = audit or (lambda event, outcome: None)
        self._armed = False
        self._read_aloud = True

    # -- arming ------------------------------------------------------------

    @property
    def armed(self) -> bool:
        return self._armed

    def arm(self) -> None:
        self._armed = True
        self._audit("voice.armed", "recorded")

    def disarm(self) -> None:
        if self._armed:
            self._audit("voice.disarmed", "recorded")
        self._armed = False

    @property
    def read_aloud(self) -> bool:
        return self._read_aloud

    def set_read_aloud(self, on: bool) -> None:
        self._read_aloud = bool(on)

    # -- input -------------------------------------------------------------

    def hear(self, audio_path: str | Path | None) -> Turn | None:
        """Turn one recording into a Turn, then delete the recording.

        Returns None when there was nothing to hear. Raises NotArmed if the session
        was not armed (the file is still deleted, unread) and SpeechUnavailable if
        the speech model could not run.
        """
        if not audio_path:
            return None
        path = Path(audio_path)
        try:
            if not self._armed:
                raise NotArmed("Voice is off. Turn it on first; nothing was recorded.")
            text = self._transcriber.transcribe(path)
        finally:
            with contextlib.suppress(OSError):
                path.unlink()
        text = (text or "").strip()
        if not text:
            return None
        self._audit("voice.heard", "recorded")  # that it happened, never the audio
        return Turn(text=text, spoken=True)

    # -- output ------------------------------------------------------------

    def speak(self, text: str) -> Path | None:
        """A sound file reading `text` aloud, or None when reading aloud is off."""
        if not self._read_aloud:
            return None
        text = " ".join((text or "").split())
        if not text:
            return None
        if len(text) > MAX_SPOKEN_CHARS:
            text = text[:MAX_SPOKEN_CHARS].rsplit(" ", 1)[0] + ". The rest is on the screen."
        handle, name = tempfile.mkstemp(prefix="artemis-speech-", suffix=".wav")
        os.close(handle)  # leaving it open stops Windows from writing to the file
        out = Path(name)
        try:
            self._speaker.speak_to_file(text, out)
        except SpeechUnavailable:
            with contextlib.suppress(OSError):
                out.unlink()
            raise
        return out
