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
import re
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime
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


class PiperSpeaker:
    """A natural-sounding voice that runs on this computer (Piper).

    The built-in Windows voice sounds robotic; this one sounds like a person. The voice
    file (about 60 MB) is fetched once, the first time it is used.
    """

    REPO = "rhasspy/piper-voices"
    FILE = "en/en_US/amy/medium/en_US-amy-medium"

    def __init__(self) -> None:
        self._voice = None
        self._lock = threading.Lock()

    def available(self) -> bool:
        try:
            import piper  # noqa: F401
        except ImportError:
            return False
        return True

    def _load(self):
        with self._lock:
            if self._voice is None:
                from huggingface_hub import hf_hub_download
                from piper import PiperVoice

                # Use the copy already on this computer; only go online the first time.
                try:
                    hf_hub_download(self.REPO, self.FILE + ".onnx.json", local_files_only=True)
                    model = hf_hub_download(self.REPO, self.FILE + ".onnx", local_files_only=True)
                except Exception:
                    hf_hub_download(self.REPO, self.FILE + ".onnx.json")
                    model = hf_hub_download(self.REPO, self.FILE + ".onnx")
                self._voice = PiperVoice.load(model)
            return self._voice

    def speak_to_file(self, text: str, out_path: Path) -> None:
        import wave

        try:
            voice = self._load()
            with wave.open(str(out_path), "wb") as wav:
                voice.synthesize_wav(text, wav)
        except Exception as exc:
            raise SpeechUnavailable("The natural voice could not run.") from exc


class KokoroSpeaker:
    """The most natural voice here (Kokoro), running on this computer.

    Noticeably more lifelike than Piper: it varies pace and pitch like a person does.
    The two files (about 120 MB) are fetched once, the first time it is used.
    """

    BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
    FILES = ("kokoro-v1.0.int8.onnx", "voices-v1.0.bin")
    VOICE = "af_heart"

    def __init__(self) -> None:
        self._engine = None
        self._lock = threading.Lock()

    def available(self) -> bool:
        try:
            import kokoro_onnx  # noqa: F401
            import soundfile  # noqa: F401
        except ImportError:
            return False
        return True

    def _load(self):
        with self._lock:
            if self._engine is None:
                import urllib.request

                from kokoro_onnx import Kokoro

                from artemis.data.paths import artemis_home

                folder = artemis_home() / "voice"
                folder.mkdir(parents=True, exist_ok=True)
                for name in self.FILES:
                    target = folder / name
                    if not target.exists():
                        part = target.with_suffix(target.suffix + ".part")
                        urllib.request.urlretrieve(self.BASE + name, part)
                        part.replace(target)
                self._engine = Kokoro(str(folder / self.FILES[0]), str(folder / self.FILES[1]))
            return self._engine

    def speak_to_file(self, text: str, out_path: Path) -> None:
        try:
            import soundfile

            samples, rate = self._load().create(text, voice=self.VOICE, speed=0.97, lang="en-us")
            soundfile.write(str(out_path), samples, rate)
        except Exception as exc:
            raise SpeechUnavailable("The natural voice could not run.") from exc


class BestAvailableSpeaker:
    """The most natural voice that works, falling back to plainer ones."""

    def __init__(self) -> None:
        self._chain = [KokoroSpeaker(), PiperSpeaker(), WindowsSpeaker()]
        self._failed: set[int] = set()

    def speak_to_file(self, text: str, out_path: Path) -> None:
        for index, speaker in enumerate(self._chain):
            if index in self._failed or not speaker.available():
                continue
            try:
                speaker.speak_to_file(text, out_path)
                return
            except SpeechUnavailable:
                self._failed.add(index)  # offline on first use, say: fall back quietly
        raise SpeechUnavailable("This computer has no speech voice ARTEMIS can use.")


_LABEL = re.compile(r"^\s*\S+\s*[·•]\s*(on this computer|via \w[\w .-]*)\s*$", re.IGNORECASE)
_MARKUP = re.compile(r"[*_`#>]+")


def spoken_form(text: str) -> str:
    """What a person would actually say aloud for this reply.

    Drops the line that names the model and where it ran, the markup, and the list
    bullets, and reads a waiting plan as an invitation to look at the screen.
    """
    kept: list[str] = []
    for line in (text or "").splitlines():
        if _LABEL.match(line):
            continue
        line = _MARKUP.sub("", line)
        line = re.sub(r"^\s*[-•]\s+", "", line).strip()
        if line:
            kept.append(line if line[-1] in ".?!:" else line + ".")
    spoken = " ".join(kept)
    if re.search(r"approve these changes|nothing has happened yet", spoken, re.IGNORECASE):
        return "I've put the plan on the screen. Have a look, and press Approve when you're happy with it."
    return spoken


def greeting(now: datetime | None = None, resuming: bool = False) -> str:
    """The first thing said when voice is switched on."""
    if resuming:
        return "Hi again. Let's pick up where we left off. What's next?"
    hour = (now or datetime.now()).hour
    part = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    return f"{part}! I'm ARTEMIS. I'm listening. What can I help you with?"


class VoiceSession:
    """Whether the microphone is armed, and the turning of speech into a `Turn`."""

    def __init__(
        self,
        transcriber: Transcriber | None = None,
        speaker: Speaker | None = None,
        audit: Callable[[str, str], None] | None = None,
    ) -> None:
        self._transcriber = transcriber or FasterWhisperTranscriber()
        self._speaker = speaker or BestAvailableSpeaker()
        self._audit = audit or (lambda event, outcome: None)
        self._armed = False
        self._read_aloud = True

    def warm(self) -> None:
        """Load the speech models in the background so the first greeting is quick.

        Loads files only. It does not open the microphone or record anything.
        """

        def load() -> None:
            with contextlib.suppress(Exception):
                handle, name = tempfile.mkstemp(prefix="artemis-warm-", suffix=".wav")
                os.close(handle)
                out = Path(name)
                try:
                    self._speaker.speak_to_file("Hello.", out)
                finally:
                    with contextlib.suppress(OSError):
                        out.unlink()

        threading.Thread(target=load, daemon=True).start()

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
        text = " ".join(spoken_form(text).split())
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
