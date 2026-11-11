"""Shared helpers for the UI test agents. Import with:

    import sys; sys.path.insert(0, r"<repo>/tests/agents"); from harness import *

Nothing here changes ARTEMIS. It starts a private copy of the app on its own port with its own
data folder, so several agents can run side by side without touching each other or the
developer's real data.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENTS = REPO / "tests" / "agents"
RESULTS = AGENTS / "results"
WORK = AGENTS / "work"


class App:
    """A private ARTEMIS: its own port, its own data folder, started and stopped for you."""

    def __init__(self, name: str, port: int, extra_env: dict | None = None) -> None:
        self.name = name
        self.port = port
        self.home = WORK / name / "home"
        self.log_path = WORK / name / "server.log"
        self.url = f"http://127.0.0.1:{port}/"
        self._extra = extra_env or {}
        self._proc: subprocess.Popen | None = None

    def start(self, fresh: bool = True) -> "App":
        if fresh:
            shutil.rmtree(self.home, ignore_errors=True)
        self.home.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, ARTEMIS_HOME=str(self.home), PYTHONPATH=str(REPO / "src"),
                   PYTHONUNBUFFERED="1", **self._extra)
        log = open(self.log_path, "w", encoding="utf-8", errors="replace")
        self._proc = subprocess.Popen(
            [sys.executable, "-c", f"from artemis.ui.web import launch; launch(inbrowser=False, port={self.port})"],
            env=env, cwd=str(REPO), stdout=log, stderr=subprocess.STDOUT,
        )
        for _ in range(90):
            try:
                urllib.request.urlopen(self.url, timeout=2)
                return self
            except Exception:
                time.sleep(1)
        raise RuntimeError(f"ARTEMIS did not start; see {self.log_path}")

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.kill()

    def restart(self) -> "App":
        """Stop and start again WITHOUT wiping the data folder (to test what survives)."""
        self.stop()
        return self.start(fresh=False)

    def server_log(self) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def __enter__(self) -> "App":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()


def make_user_folder(path: Path, kind: str = "messy") -> Path:
    """A believable folder of someone's files. `kind`: messy | project | notes | big."""
    path.mkdir(parents=True, exist_ok=True)
    if kind == "messy":
        names = ["Invoice_March.pdf", "invoice-april.pdf", "holiday photo 1.jpg", "holiday photo 2.jpg",
                 "resume_final_v3.docx", "resume_final_v3_REAL.docx", "notes.txt", "todo.md",
                 "budget 2026.xlsx", "meeting-notes-jan.txt", "screenshot (1).png", "screenshot (2).png",
                 "random.zip", "readme.txt"]
        for n in names:
            (path / n).write_text(f"sample content of {n}\n", encoding="utf-8")
        (path / "notes.txt").write_text(
            "Project Orion budget is 45,000 dollars. The deadline is 14 March. Owner: Sara Khan.\n"
            "Kickoff meeting was held on 2 February. Risks: late hardware delivery.\n", encoding="utf-8")
        (path / "meeting-notes-jan.txt").write_text(
            "January meeting: we agreed to hire two testers. Sara will draft the plan by Friday.\n", encoding="utf-8")
    elif kind == "project":
        (path / "app").mkdir(exist_ok=True)
        (path / "app" / "main.py").write_text(
            "def add(a, b):\n    return a - b  # BUG: should add\n\n\nif __name__ == '__main__':\n    print(add(2, 3))\n",
            encoding="utf-8")
        (path / "app" / "util.py").write_text("def shout(s):\n    return s.upper() + '!'\n", encoding="utf-8")
        (path / "README.md").write_text("# Demo\nA tiny demo project with a bug in add().\n", encoding="utf-8")
    elif kind == "notes":
        for i in range(1, 6):
            (path / f"lecture-{i}.md").write_text(
                f"# Lecture {i}\nTopic {i}: the key idea is that concept {i} depends on concept {max(i-1,1)}.\n",
                encoding="utf-8")
    elif kind == "big":
        for i in range(400):
            (path / f"file_{i:04d}.txt").write_text(f"document {i} about subject {i % 17}\n", encoding="utf-8")
    return path


def make_speech_wav(text: str, out: Path, silence_after: float = 9.0) -> Path:
    """A WAV of `text` spoken aloud, followed by silence, for use as a fake microphone.

    Pass the file to Chromium with  --use-file-for-fake-audio-capture=<wav>  and the flags in
    FAKE_MIC_ARGS. It loops, so the trailing silence lets ARTEMIS hear you finish.
    """
    sys.path.insert(0, str(REPO / "src"))
    from artemis.services.speech import VoiceSession

    clip = VoiceSession().speak(text)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        src = wave.open(str(clip))
        params, frames = src.getparams(), src.readframes(src.getnframes())
        src.close()
    finally:
        with contextlib.suppress(OSError):
            Path(clip).unlink()
    w = wave.open(str(out), "wb")
    w.setparams(params)
    w.writeframes(frames + bytes(int(params.framerate * params.sampwidth * params.nchannels * silence_after)))
    w.close()
    return out


FAKE_MIC_ARGS = [
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    "--autoplay-policy=no-user-gesture-required",
]


def browser_page(pw, app: App, mic_wav: Path | None = None, width: int = 1300, height: int = 1000):
    """A Chromium page already opened on the app. Returns (browser, page)."""
    args = list(FAKE_MIC_ARGS) if mic_wav else []
    if mic_wav:
        args.append(f"--use-file-for-fake-audio-capture={mic_wav}")
    browser = pw.chromium.launch(args=args)
    ctx = browser.new_context(viewport={"width": width, "height": height},
                              permissions=["microphone"] if mic_wav else [])
    page = ctx.new_page()
    page.goto(app.url)
    page.wait_for_timeout(3500)
    return browser, page


def shot(page, folder: Path, name: str) -> str:
    """Save a screenshot under the agent's own results folder and return its relative name."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    page.screenshot(path=str(path))
    return path.name


def wait_for_reply(page, timeout_s: int = 180) -> str:
    """Wait until the conversation has stopped working on a message; return the newest turn."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        page.wait_for_timeout(1000)
        busy = page.locator(".a-chat .a-thinking, .a-chat .a-streaming").count()
        turns = page.locator(".a-chat .a-turn")
        if not busy and turns.count():
            return turns.first.inner_text()  # newest turn is first in the markup
    return "TIMEOUT: no finished reply within %ss" % timeout_s
