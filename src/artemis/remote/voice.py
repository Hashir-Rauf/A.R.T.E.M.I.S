"""Real-time voice for a paired device.

The phone streams its microphone to this computer in small encrypted pieces. This computer
decides when the person has finished speaking, turns the words into text with the local speech
model, hands the text to the same assistant path typing uses, and streams the answer back as
text and sound, one sentence at a time, so the first sentence is heard while the rest is still
being written.

Rules carried over from local voice, and enforced here:

* nothing is transcribed until the device started voice, and only if the owner allowed voice
  for paired devices (default: off). Audio that arrives otherwise is dropped unread;
* audio exists only in memory. It is never written to a file, and it is thrown away the moment
  it has been turned into words;
* the words go through the same approval gates as typed words. Voice adds no gate of its own;
* the log records that voice was used, never the audio or what was said.

Timing is counted in audio, not in clock time, so it behaves the same on a slow network.
"""

from __future__ import annotations

import base64
import math
import re
from array import array
from typing import Any, Callable, Iterator

from artemis.services.speech import NotArmed, SpeechUnavailable, VoiceSession, greeting, spoken_form

SAMPLE_RATE = 16000
#: How long with no speech before ARTEMIS speaks first. After that it just keeps listening.
NUDGE_AFTER = 4.0
#: How long a pause means the person has finished.
END_AFTER = 3.5
MAX_UTTERANCE_SECONDS = 60
PRE_ROLL_SECONDS = 0.5
LOUD_SPEECH = 0.05
MAX_NOISE_FLOOR = 0.02
CALIBRATE_SECONDS = 0.7

NUDGE = "Hello? Is there anything I can help you with?"
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_MODEL_LINE = re.compile(r'<div class="a-model">.*?</div>', re.DOTALL)


def _plain(markup: str) -> str:
    import html

    text = re.sub(r"<[^>]+>", " ", _MODEL_LINE.sub("", markup or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def level(pcm: bytes) -> float:
    """How loud a piece of audio is, from 0 to 1."""
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    if not samples:
        return 0.0
    step = 4
    picked = samples[::step]
    return math.sqrt(sum(s * s for s in picked) / len(picked)) / 32768.0


class RemoteVoice:
    def __init__(
        self,
        session: VoiceSession,
        panel: Any,
        workspace_id: int,
        audit: Callable[[str, str, dict], None],
    ) -> None:
        self._session = session
        self._panel = panel
        self._workspace_id = workspace_id
        self._audit = audit
        self._busy = False
        self._reset()

    def _reset(self) -> None:
        self._buffer = bytearray()
        self._pre = bytearray()
        self._heard = False
        self._silence = 0.0
        self._quiet = 0.0
        self._floor = 0.0
        self._calibrated = 0.0
        self._nudged = False if not hasattr(self, "_nudged") else self._nudged

    # -- starting and stopping ----------------------------------------------------

    def start(self) -> Iterator[dict]:
        self._session.arm()
        self._panel.set_spoken(True)  # worded for the ear; also loads the local model
        self._nudged = False
        self._reset()
        again = bool(self._panel.state.transcript)
        text = "Hi again. Let's pick up where we left off. What's next?" if again else greeting()
        self._panel.log_turn(None, self._panel._say(text))
        self._busy = True  # until the phone has played the greeting and says it is listening
        yield from self._say(text)
        yield {"type": "listening"}

    def stop(self) -> dict:
        self._session.disarm()
        self._panel.set_spoken(False)
        self._buffer.clear()
        self._pre.clear()
        return {"type": "stopped"}

    def resume(self) -> dict:
        """The phone finished playing the sound and is listening again."""
        self._busy = False
        self._reset()
        return {"type": "ready"}  # not "listening", which would make the phone resume again

    # -- audio in -----------------------------------------------------------------

    def feed(self, pcm: bytes) -> Iterator[dict]:
        if not self._session.armed:
            yield {"type": "error", "message": "Voice is off, so that audio was ignored."}
            return
        if self._busy or not pcm:
            return
        seconds = len(pcm) / 2 / SAMPLE_RATE
        loud = level(pcm)

        # The room's own noise sets the bar, but it can never be set so high that talking
        # straight away is missed.
        if self._calibrated < CALIBRATE_SECONDS and not self._heard and loud <= LOUD_SPEECH:
            self._calibrated += seconds
            self._floor = min(max(self._floor * 0.8, loud), MAX_NOISE_FLOOR)
            self._quiet += seconds
            self._remember_pre(pcm)
            return

        speech = loud > max(0.02, self._floor * 2.5)
        if speech:
            if not self._heard:
                self._heard = True
                self._buffer = bytearray(self._pre)
            self._silence = 0.0
            self._buffer.extend(pcm)
        elif self._heard:
            self._silence += seconds
            self._buffer.extend(pcm)
        else:
            self._quiet += seconds
            self._remember_pre(pcm)

        too_long = len(self._buffer) / 2 / SAMPLE_RATE >= MAX_UTTERANCE_SECONDS
        if self._heard and (self._silence >= END_AFTER or too_long):
            yield from self._answer()
        elif not self._heard and not self._nudged and self._quiet >= NUDGE_AFTER:
            self._busy = True
            self._nudged = True
            self._panel.log_turn(None, self._panel._say(NUDGE))
            yield from self._say(NUDGE)
            yield {"type": "listening"}  # the phone resumes after it has played the sound

    def _remember_pre(self, pcm: bytes) -> None:
        self._pre.extend(pcm)
        keep = int(PRE_ROLL_SECONDS * SAMPLE_RATE) * 2
        if len(self._pre) > keep:
            del self._pre[: len(self._pre) - keep]

    # -- the turn ------------------------------------------------------------------

    def _answer(self) -> Iterator[dict]:
        self._busy = True
        audio = bytes(self._buffer)
        self._buffer.clear()
        self._pre.clear()
        self._heard = False
        self._nudged = False
        yield {"type": "thinking"}
        try:
            turn = self._session.hear_pcm(audio)
        except NotArmed:
            yield {"type": "error", "message": "Voice is off, so that audio was ignored."}
            yield {"type": "listening"}
            return
        except SpeechUnavailable as exc:
            yield {"type": "error", "message": str(exc)}
            yield {"type": "listening"}
            return
        finally:
            del audio  # the recording is not kept
        if turn is None:
            yield {"type": "nothing"}
            yield {"type": "listening"}
            return
        yield {"type": "heard", "text": turn.text}
        yield from self._reply(turn.text)
        yield {"type": "done"}

    def _reply(self, text: str) -> Iterator[dict]:
        said_upto = 0
        final = ""
        card = ""
        for message_html, card_html in self._panel.ask_streaming(self._workspace_id, text):
            final, card = message_html, card_html
            if "a-streaming" not in message_html:
                continue
            body = _plain(message_html)
            # speak each finished sentence as it appears, so the voice is not behind the text
            pending = body[said_upto:]
            parts = _SENTENCE_END.split(pending)
            for sentence in parts[:-1]:
                yield from self._say(sentence)
                said_upto += len(sentence) + 1
        full = _plain(final)
        if "a-thinking" in final:
            full = ""
        self._panel.log_turn(text, final)
        rest = full[said_upto:].strip()
        if rest:
            yield from self._say(rest)
        outcome = self._panel.state.outcome
        yield {
            "type": "reply",
            "message": full,
            "card": _plain(card),
            "pending": bool(self._panel.has_pending),
            "leaves_computer": bool(outcome and (outcome.preview or {}).get("leaves_machine")),
        }

    def _say(self, text: str) -> Iterator[dict]:
        shown = " ".join(spoken_form(text).split()) or text
        try:
            wav = self._session.speak_bytes(text)
        except SpeechUnavailable:
            wav = None
        event: dict[str, Any] = {"type": "speech", "text": shown}
        if wav:
            event["wav"] = base64.b64encode(wav).decode("ascii")
        yield event
