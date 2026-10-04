"""The ARTEMIS web interface.

A Gradio client of the same core the CLI and the desktop window use. It holds no
state the backend does not own: every action ends by re-querying the stores and
re-rendering, so the page cannot drift from what is actually held.

Four things about Gradio 6 that shaped this file:

* `css`, `js`, `theme` and `head` moved from `Blocks(...)` to `launch(...)` in
  6.0. Passing them to the constructor only raises a deprecation warning and the
  styling is dropped, which is silent and easy to miss. They are passed to
  `launch()` here.
* Gradio rewrites user CSS to prefix every selector with its container class,
  and that pass drops a declaration whose value spans a newline. Every value in
  the stylesheet below is therefore written on a single line. This failure is
  invisible: the rule survives, only its value is emptied.
* For the same reason the two gradient-clipped text rules (`.a-title` and
  `.a-metric-n`) use the `background-image` longhand rather than the
  `background` shorthand. With the shorthand the value does not survive the
  rewrite, the fill stays transparent, and the text renders invisible.
* A browser cannot open a native folder picker, so adding a folder takes a typed
  path. A **Browse** button shells out to a native dialog, which is legitimate
  only because the server runs on the user's own machine.
* The cards are rendered as raw HTML rather than Gradio components, because the
  animation and layout wanted here are beyond what the component set styles.
  Every path that reaches that HTML is escaped (see `_esc`).

The visual language is deliberate rather than decorative: ARTEMIS is a system
whose entire claim is that it stays inside a boundary, so the interface reads as
instrumentation. A light ground with magenta, violet and cyan light, glass
panels over a slow aurora, and motion used to show state changing rather than
for its own sake.
"""

from __future__ import annotations

import html
import subprocess
import sys
from pathlib import Path

import gradio as gr

from artemis.core.broker import WorkspaceBroker
from artemis.core.disclosure import DisclosurePanel
from artemis.core.errors import WorkspaceError
from artemis.core.indexer import Indexer
from artemis.core.workspace import WorkspaceManager
from artemis.data import paths
from artemis.core.providers import CLOUD_CATALOGUE
from artemis.data import credentials
from artemis.services.resume import ResumeService
from artemis.data.store import Store
from artemis.ui.assistant import AssistantPanel

# --------------------------------------------------------------------------
# Style
# --------------------------------------------------------------------------

THEME = gr.themes.Base(
    primary_hue=gr.themes.Color(
        c50="#fdf0ff", c100="#fae0ff", c200="#f4bcff", c300="#ee8fff",
        c400="#e455ff", c500="#d016f0", c600="#b410cc", c700="#8f0da3",
        c800="#680a77", c900="#42064b", c950="#220327",
    ),
    neutral_hue="slate",
    # Fonts must be Font objects, not bare strings. Gradio compares a custom
    # theme against its built-ins on launch and reads `.name` off each entry,
    # so plain strings raise AttributeError from inside that comparison.
    # Local families only: nothing here should fetch from a font CDN, because
    # the interface must work with no network at all.
    font=(
        gr.themes.Font("Segoe UI"),
        gr.themes.Font("Inter"),
        gr.themes.Font("system-ui"),
        gr.themes.Font("sans-serif"),
    ),
    font_mono=(
        gr.themes.Font("JetBrains Mono"),
        gr.themes.Font("Cascadia Code"),
        gr.themes.Font("Consolas"),
        gr.themes.Font("monospace"),
    ),
)

CSS = """
/* ARTEMIS - clean light SaaS.

   Flat surfaces, one accent, real borders, generous whitespace. No gradients
   or blur behind content: the previous versions put animated colour under
   dense text and it failed contrast in two places and read as unfinished.

   Every colour pair here is checked against white. Muted text is #475569
   (7.5:1), not the #64748b (4.3:1) that failed the audit, and the accent is
   indigo #4f46e5 (7.4:1) rather than the magenta that failed at 3.8:1. */
:root {
  --page: #f8fafc;
  --surface: #ffffff;
  --raised: #f1f5f9;
  --line: #e2e8f0;
  --line-firm: #cbd5e1;
  --text: #0f172a;
  --muted: #475569;
  --faint: #64748b;
  --accent: #4f46e5;
  --accent-hover: #4338ca;
  --accent-wash: #eef2ff;
  --ok: #047857;
  --ok-wash: #ecfdf5;
  --danger: #be123c;
  --danger-wash: #fff1f2;
  --r: 8px;
}

.gradio-container, body, gradio-app { background: var(--page) !important; color: var(--text) !important; font-size: 15px !important; }
.gradio-container { max-width: 1280px !important; margin: 0 auto !important; }

/* Sidebar ---------------------------------------------------------------- */
.a-side { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r); padding: 20px 16px; }
.a-brand { font-size: 1.05rem; font-weight: 700; letter-spacing: .02em; color: var(--text); }
.a-brand-sub { font-size: .75rem; color: var(--muted); margin-top: 2px; padding-bottom: 18px; border-bottom: 1px solid var(--line); }
.a-stat { padding: 13px 0; border-bottom: 1px solid var(--line); }
.a-stat-n { font-size: 1.4rem; font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; line-height: 1.2; }
.a-stat-l { font-size: .78rem; color: var(--muted); margin-top: 1px; }
.a-note { margin-top: 16px; padding: 11px 12px; background: var(--ok-wash); border: 1px solid #a7f3d0; border-radius: var(--r); font-size: .78rem; color: var(--ok); line-height: 1.5; font-weight: 500; }

/* Headings and type ------------------------------------------------------- */
.a-h1 { font-size: 1.3rem; font-weight: 700; color: var(--text); margin-bottom: 3px; }
.a-h2 { font-size: 1rem; font-weight: 650; color: var(--text); margin-bottom: 3px; }
.a-sub { font-size: .88rem; color: var(--muted); line-height: 1.6; margin-bottom: 4px; }
.a-section { font-size: .76rem; letter-spacing: .07em; text-transform: uppercase; color: var(--muted); font-weight: 700; margin: 2px 0 9px; }
.a-card-meta { font-size: .86rem; color: var(--muted); line-height: 1.6; }

/* Metrics ----------------------------------------------------------------- */
.a-metrics { display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 12px; }
.a-metric { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r); padding: 15px 17px; }
.a-metric-n { font-size: 1.55rem; font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; line-height: 1.2; }
.a-metric-l { font-size: .78rem; color: var(--muted); margin-top: 3px; }

/* Workspace cards ---------------------------------------------------------- */
.a-cards { display: flex; flex-direction: column; gap: 10px; }
.a-card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r); padding: 15px 17px; transition: border-color .15s ease; }
.a-card:hover { border-color: var(--line-firm); }
.a-card-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.a-card-name { font-size: .98rem; font-weight: 650; color: var(--text); }
.a-chip { font-size: .74rem; font-weight: 600; color: var(--accent); background: var(--accent-wash); border: 1px solid #c7d2fe; border-radius: 999px; padding: 3px 11px; white-space: nowrap; }
.a-card-path { font-family: ui-monospace, "Cascadia Code", Consolas, monospace; font-size: .78rem; color: var(--faint); margin-top: 7px; word-break: break-all; line-height: 1.5; }

.a-empty { border: 1px dashed var(--line-firm); border-radius: var(--r); padding: 40px 24px; text-align: center; background: var(--surface); }
.a-empty-title { font-size: 1rem; font-weight: 650; color: var(--text); }
.a-empty-body { color: var(--muted); margin-top: 8px; line-height: 1.6; font-size: .88rem; max-width: 44ch; margin-left: auto; margin-right: auto; }
.a-eye { width: 40px; height: 40px; margin: 0 auto 14px; border-radius: var(--r); display: grid; place-items: center; color: var(--accent); font-size: 1.1rem; background: var(--accent-wash); border: 1px solid #c7d2fe; }

/* Messages ----------------------------------------------------------------- */
.a-msg { padding: 13px 16px; border-radius: var(--r); background: var(--surface); border: 1px solid var(--line); border-left: 3px solid var(--accent); color: var(--text); font-size: .9rem; line-height: 1.6; }
.a-msg.warn { border-left-color: var(--danger); background: var(--danger-wash); }
.a-msg.a-thinking { color: var(--muted); display: flex; align-items: center; gap: 10px; }
.a-cloud { border: 1px solid var(--line); border-radius: var(--r); overflow: hidden; margin-bottom: 12px; }
.a-cloud-row { display: flex; align-items: center; gap: 14px; padding: 12px 16px; border-bottom: 1px solid var(--line); background: var(--surface); }
.a-cloud-row:last-child { border-bottom: none; }
.a-cloud-name { font-weight: 600; color: var(--text); font-size: .9rem; min-width: 150px; }
.a-cloud-model { color: var(--muted); font-size: .82rem; font-family: ui-monospace, monospace; flex: 1; }
.a-cloud-on { color: #166534; background: #dcfce7; border-radius: 999px; padding: 3px 10px; font-size: .75rem; font-weight: 600; }
.a-cloud-off { color: #475569; background: #f1f5f9; border-radius: 999px; padding: 3px 10px; font-size: .75rem; font-weight: 600; }
.a-cloud-note { color: var(--muted); font-size: .82rem; line-height: 1.6; margin-bottom: 14px; }
.a-quote { margin-top: 8px; padding: 12px 14px; background: var(--raised); border-left: 3px solid var(--line-firm); border-radius: 6px; color: var(--text); font-size: .85rem; line-height: 1.6; white-space: pre-wrap; max-height: 320px; overflow-y: auto; }
.a-dots { display: inline-flex; gap: 4px; }
.a-dots i { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); display: inline-block; animation: a-bounce 1.2s ease-in-out infinite; }
.a-dots i:nth-child(2) { animation-delay: .15s; }
.a-dots i:nth-child(3) { animation-delay: .3s; }
@keyframes a-bounce { 0%, 80%, 100% { opacity: .25; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }

/* The approval card, the one screen that must be answerable at a glance. */
.a-approval { background: var(--surface); border: 1px solid var(--line-firm); border-top: 3px solid var(--accent); border-radius: var(--r); padding: 20px 22px; }
.a-approval-head { font-size: 1.05rem; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.a-approval-sub { font-size: .86rem; color: var(--muted); margin-bottom: 16px; }
.a-facts { display: grid; grid-template-columns: auto 1fr; gap: 7px 16px; margin-bottom: 15px; align-items: baseline; }
.a-fact-k { color: var(--muted); font-size: .8rem; font-weight: 600; white-space: nowrap; }
.a-fact-v { color: var(--text); font-size: .9rem; }
.a-assures { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }
.a-assure { font-size: .8rem; font-weight: 600; color: var(--ok); background: var(--ok-wash); border: 1px solid #a7f3d0; border-radius: var(--r); padding: 6px 12px; }
.a-steps-head { font-size: .76rem; letter-spacing: .07em; text-transform: uppercase; color: var(--muted); font-weight: 700; margin-bottom: 8px; }
.a-steps { display: flex; flex-direction: column; gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: var(--r); overflow: hidden; }
.a-step { display: flex; gap: 13px; align-items: baseline; font-size: .88rem; padding: 10px 14px; background: var(--surface); }
.a-step-n { color: var(--faint); font-weight: 600; min-width: 16px; font-variant-numeric: tabular-nums; font-size: .82rem; }
.a-step-t { color: var(--text); }

/* Resume, files, settings --------------------------------------------------- */
.a-resume { padding: 15px 17px; border-radius: var(--r); background: var(--surface); border: 1px solid var(--line); }
.a-resume-line { font-size: .9rem; color: var(--text); line-height: 1.6; margin-bottom: 10px; }
.a-changes { display: flex; flex-direction: column; gap: 4px; }
.a-change { font-family: ui-monospace, "Cascadia Code", Consolas, monospace; font-size: .8rem; color: var(--muted); padding: 5px 10px; border-radius: 6px; background: var(--raised); }
.a-change.a-added { color: var(--ok); background: var(--ok-wash); }
.a-change.a-removed { color: var(--danger); background: var(--danger-wash); }

.a-files { display: flex; flex-direction: column; gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: var(--r); overflow: hidden; }
.a-file { display: flex; justify-content: space-between; gap: 14px; font-size: .85rem; padding: 10px 14px; background: var(--surface); }
.a-file-name { color: var(--text) !important; font-family: ui-monospace, "Cascadia Code", Consolas, monospace; }
.a-file-size { color: var(--faint) !important; font-variant-numeric: tabular-nums; white-space: nowrap; }

.a-location { display: flex; flex-direction: column; gap: 6px; padding: 14px 16px; border-radius: var(--r); background: var(--raised); border: 1px solid var(--line); }
.a-location-label { font-size: .76rem; color: var(--muted); font-weight: 600; }
.a-location-path { font-family: ui-monospace, "Cascadia Code", Consolas, monospace; font-size: .82rem; color: var(--text); word-break: break-all; }

/* Gradio overrides ----------------------------------------------------------- */
.gradio-container .block, .gradio-container .form, .gradio-container .panel { background: transparent !important; border: none !important; }

.gradio-container button { border-radius: var(--r) !important; font-size: .88rem !important; font-weight: 550 !important; padding: 9px 15px !important; transition: background .15s ease, border-color .15s ease !important; }
.gradio-container button.primary { background: var(--accent) !important; border: 1px solid var(--accent) !important; color: #ffffff !important; font-weight: 600 !important; }
.gradio-container button.primary:hover { background: var(--accent-hover) !important; border-color: var(--accent-hover) !important; }
.gradio-container button.secondary { background: var(--surface) !important; border: 1px solid var(--line-firm) !important; color: var(--text) !important; }
.gradio-container button.secondary:hover { background: var(--raised) !important; }
.gradio-container button.stop { background: var(--surface) !important; border: 1px solid #fda4af !important; color: var(--danger) !important; font-weight: 600 !important; }
.gradio-container button.stop:hover { background: var(--danger-wash) !important; }

.gradio-container input[type=text], .gradio-container textarea, .gradio-container select { background: var(--surface) !important; border: 1px solid var(--line-firm) !important; border-radius: var(--r) !important; color: var(--text) !important; font-size: .9rem !important; padding: 9px 12px !important; }
.gradio-container input[type=text]:focus, .gradio-container textarea:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(79,70,229,.14) !important; outline: none !important; }
.gradio-container input::placeholder, .gradio-container textarea::placeholder { color: var(--faint) !important; }
.gradio-container label span { color: var(--muted) !important; font-weight: 600 !important; font-size: .82rem !important; }

/* Tabs: the one navigation. Selected state is a solid underline, not colour
   alone, so it does not rely on hue to be legible. */
.gradio-container button[role=tab] { color: var(--muted) !important; font-weight: 600 !important; border: none !important; border-bottom: 2px solid transparent !important; border-radius: 0 !important; background: transparent !important; }
.gradio-container button[role=tab].selected { color: var(--accent) !important; border-bottom-color: var(--accent) !important; }

.gradio-container button:focus-visible, .gradio-container input:focus-visible, .gradio-container textarea:focus-visible, .gradio-container [role=tab]:focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px !important; }

@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition-duration: .001ms !important; animation-duration: .001ms !important; } }
"""


def _esc(value: object) -> str:
    """Escape anything interpolated into the raw HTML blocks."""
    return html.escape(str(value), quote=True)


def _say_html(message: str) -> str:
    """A short confirmation under the settings controls."""
    return f'<div class="a-msg">{_esc(message)}</div>' if message else ""


def _location_html(path: str) -> str:
    """The current store location, shown as a path the user can read."""
    return (
        '<div class="a-location"><span class="a-location-label">Currently in'
        f'</span><span class="a-location-path">{_esc(path)}</span></div>'
    )


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


class WebPanel:
    """Renders the page and performs its actions against the core."""

    def __init__(self, store: Store) -> None:
        self._store = store
        self._manager = WorkspaceManager(store)
        self._broker = WorkspaceBroker(store)
        self._indexer = Indexer(store, self._broker)
        self._panel = DisclosurePanel(store)
        self._resume = ResumeService(store, self._broker)

    # -- queries -----------------------------------------------------------


    def sidebar_html(self, active: str = "work") -> str:
        """The rail: what ARTEMIS currently holds, and where it is kept.

        Statistics rather than navigation. The tab strip navigates; a second
        set of nav-shaped items here would be two controls for one job, and
        the earlier version of this rail only looked clickable.
        """
        workspaces = self._manager.list()
        files = sum(self._store.count_files(w.id) for w in workspaces)
        actions = self._store.count_audit()

        stats = [
            (str(len(workspaces)), "folders it can see"),
            (str(files), "files it knows about"),
            (str(actions), "actions recorded"),
        ]
        rows = "".join(
            f'<div class="a-stat"><div class="a-stat-n">{_esc(n)}</div>'
            f'<div class="a-stat-l">{_esc(label)}</div></div>'
            for n, label in stats
        )
        return (
            '<div class="a-side">'
            '<div class="a-brand">ARTEMIS</div>'
            '<div class="a-brand-sub">Bounded desktop assistant</div>'
            f"{rows}"
            '<div class="a-note">Everything is stored on this computer. '
            "Nothing has been sent anywhere.</div>"
            "</div>"
        )

    def workspaces(self) -> list:
        return self._manager.list()

    def choices(self) -> list[tuple[str, int]]:
        return [
            (f"{w.name}  ({_plural(self._store.count_files(w.id), 'file')})", w.id)
            for w in self._manager.list()
        ]

    def cards_html(self) -> str:
        workspaces = self._manager.list()
        if not workspaces:
            return (
                '<div class="a-empty">'
                '<div class="a-eye">\u25c9</div>'
                '<div class="a-empty-title">ARTEMIS cannot see anything '
                "on this computer.</div>"
                '<div class="a-empty-body">It stays that way until you add a '
                "folder. Even then, it only ever looks inside the folders "
                "you choose.</div></div>"
            )

        cards = []
        for w in workspaces:
            count = self._store.count_files(w.id)
            access = (
                "can read files here"
                if w.permission == "read_only"
                else "can read and change files here, with your approval"
            )
            cards.append(
                '<div class="a-card">'
                '<div class="a-card-top">'
                f'<div class="a-card-name">{_esc(w.name)}</div>'
                f'<div class="a-chip">{_esc(_plural(count, "file"))}</div>'
                "</div>"
                f'<div class="a-card-path">{_esc(w.root)}</div>'
                f'<div class="a-card-meta">ARTEMIS {access}</div>'
                "</div>"
            )
        return f'<div class="a-cards">{"".join(cards)}</div>'

    def metrics_html(self) -> str:
        rows = {r.label: r for r in self._panel.snapshot().rows}
        folders = len(self._manager.list())
        files = rows["Files indexed"].count if "Files indexed" in rows else 0
        actions = rows["Actions recorded"].count if "Actions recorded" in rows else 0
        kb = DisclosurePanel.disk_usage() / 1024
        cells = [
            (folders, "folders visible"),
            (files, "files known"),
            (actions, "actions recorded"),
            (f"{kb:.0f} KB", "stored locally"),
        ]
        inner = "".join(
            f'<div class="a-metric"><div class="a-metric-n">{_esc(n)}</div>'
            f'<div class="a-metric-l">{_esc(label)}</div></div>'
            for n, label in cells
        )
        return f'<div class="a-metrics">{inner}</div>'

    def files_html(self, workspace_id: int | None) -> str:
        if not workspace_id:
            return (
                '<div class="a-card-meta">Choose a folder above to see what '
                "ARTEMIS knows about inside it.</div>"
            )
        rows = self._store.list_files(workspace_id)
        if not rows:
            return '<div class="a-card-meta">No files known in this folder.</div>'
        items = "".join(
            f'<div class="a-file"><span class="a-file-name">'
            f'{_esc(r["rel_path"])}</span>'
            f'<span class="a-file-size">{r["size"]:,} B</span></div>'
            for r in rows
        )
        return f'<div class="a-files">{items}</div>'

    @staticmethod
    def toast(message: str, warn: bool = False) -> str:
        cls = "a-toast warn" if warn else "a-toast"
        return f'<div class="{cls}">{_esc(message)}</div>'

    # -- actions -----------------------------------------------------------

    def add(self, folder: str) -> str:
        folder = (folder or "").strip().strip('"')
        if not folder:
            return self.toast("Type or browse to a folder first.", warn=True)
        try:
            ws = self._manager.grant(Path(folder))
        except WorkspaceError as exc:
            return self.toast(str(exc), warn=True)
        count = self._indexer.scan(ws.id)
        # Establish the baseline "pick up where you left off" compares against.
        # Without this there is no completed session to diff, and the feature
        # reports "first time" forever however much the folder changes.
        self._resume.checkpoint(ws.id)
        return self.toast(
            f"Added '{ws.name}'. ARTEMIS now knows about "
            f"{_plural(count, 'file')} in it."
        )

    def rescan(self, workspace_id: int | None) -> str:
        if not workspace_id:
            return self.toast("Choose a folder first.", warn=True)
        before = self._store.count_files(workspace_id)
        after = self._indexer.scan(workspace_id)
        if after == before:
            return self.toast("Checked. Nothing has changed since last time.")
        delta = after - before
        verb = "now knows about" if delta > 0 else "has forgotten"
        return self.toast(f"Checked. ARTEMIS {verb} {_plural(abs(delta), 'more file')}.")

    def forget_workspace(self, workspace_id: int | None) -> str:
        if not workspace_id:
            return self.toast("Choose a folder first.", warn=True)
        ws = self._manager.get(workspace_id)
        if ws is None:
            return self.toast("That folder is already forgotten.", warn=True)
        name, root = ws.name, ws.root
        self._manager.revoke(workspace_id)
        return self.toast(
            f"ARTEMIS has forgotten '{name}'. Your files in {root} were not touched."
        )

    def forget_everything(self) -> str:
        workspaces = self._manager.list()
        if not workspaces:
            return self.toast("There is nothing to forget.", warn=True)
        for w in workspaces:
            self._manager.revoke(w.id)
        return self.toast(
            f"ARTEMIS has forgotten {_plural(len(workspaces), 'folder')}. "
            "None of your files were deleted."
        )

    # -- where the store lives ---------------------------------------------

    @staticmethod
    def store_location() -> str:
        return str(paths.artemis_home())

    def cloud_html(self) -> str:
        """Which cloud models are set up, without ever showing a key.

        The panel is allowed to know that a credential exists and nothing more:
        keys live in the operating system keyring, and this asks `has_key`
        rather than reading them.
        """
        rows = []
        for entry in CLOUD_CATALOGUE:
            ready = credentials.has_key(entry["name"])
            state = "Key saved" if ready else "Not set up"
            tone = "a-cloud-on" if ready else "a-cloud-off"
            rows.append(
                f'<div class="a-cloud-row"><span class="a-cloud-name">'
                f'{_esc(entry["label"])}</span>'
                f'<span class="a-cloud-model">{_esc(entry["model"])}</span>'
                f'<span class="{tone}">{state}</span></div>'
            )
        return (
            '<div class="a-cloud">' + "".join(rows) + "</div>"
            '<div class="a-cloud-note">Keys are kept in the Windows Credential '
            "Manager, never in the ARTEMIS folder. A cloud model is only used "
            "for a folder you have set to allow it.</div>"
        )

    def provider_choices(self) -> list[tuple[str, str]]:
        """The providers a key can be saved for, as (label, name) pairs."""
        return [(entry["label"], entry["name"]) for entry in CLOUD_CATALOGUE]

    @staticmethod
    def save_key(provider: str, key: str) -> str:
        """Store an API key for a provider.

        The key is not echoed back, logged, or written to the database. If the
        keyring is unavailable this says so rather than quietly falling back to
        a file, because a silent downgrade to plaintext would break the promise
        the interface just made.
        """
        provider = (provider or "").strip()
        key = (key or "").strip()
        if not provider:
            return "Choose which service the key is for."
        if not key:
            return "Paste the key first."
        try:
            credentials.set_key(provider, key)
        except credentials.KeyringUnavailable as exc:
            return f"The key could not be stored safely, so it was not saved. {exc}"
        label = next(
            (e["label"] for e in CLOUD_CATALOGUE if e["name"] == provider), provider
        )
        return f"Saved the key for {label}. It is in the Windows Credential Manager."

    @staticmethod
    def forget_cloud_key(provider: str) -> str:
        """Remove a stored key."""
        provider = (provider or "").strip()
        if not provider:
            return "Choose which service to forget."
        credentials.forget_key(provider)
        label = next(
            (e["label"] for e in CLOUD_CATALOGUE if e["name"] == provider), provider
        )
        return f"Removed the key for {label}."

    def move_store(self, destination: str) -> str:
        """Move everything ARTEMIS knows to a new folder.

        The database connection is closed first. Windows refuses to delete an
        open file, so leaving it open makes the copy succeed and the cleanup
        fail, which strands a second copy of the store and leaves the pointer
        aimed at the old one. The connection is reopened against the new
        location afterwards, whether or not the move succeeded.
        """
        destination = (destination or "").strip().strip('"')
        if not destination:
            return self.toast("Type or browse to a folder first.", warn=True)
        try:
            self._close_store()
            moved_to = paths.set_home(destination, move_existing=True)
        except ValueError as exc:
            return self.toast(str(exc), warn=True)
        except OSError as exc:
            return self.toast(f"Could not move the store: {exc}", warn=True)
        finally:
            self._reopen_store()
        return self.toast(f"Everything ARTEMIS knows now lives in {moved_to}.")

    def _close_store(self) -> None:
        self._store.close()

    def _reopen_store(self) -> None:
        """Rebuild the store handle and everything that captured it."""
        self._store = Store()
        self._manager = WorkspaceManager(self._store)
        self._broker = WorkspaceBroker(self._store)
        self._indexer = Indexer(self._store, self._broker)
        self._panel = DisclosurePanel(self._store)


def _browse() -> str:
    """Open the host's native folder picker.

    The browser cannot do this, but the server is on the user's own machine, so
    a dialogue there is both possible and what the user expects. It runs in a
    separate process so a Tk failure cannot take the web server with it.
    """
    code = (
        "import tkinter as tk;"
        "from tkinter import filedialog;"
        "r=tk.Tk();r.withdraw();r.attributes('-topmost',True);"
        "print(filedialog.askdirectory() or '')"
    )
    try:
        done = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=180
        )
        return done.stdout.strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------


def build(store: Store) -> gr.Blocks:
    """Assemble the interface. Separated from launch so tests can build it."""
    panel = WebPanel(store)
    assistant = AssistantPanel(store)

    with gr.Blocks(title="ARTEMIS", fill_width=True) as page:
        with gr.Row(equal_height=False):
            # -- the rail ---------------------------------------------------
            with gr.Column(scale=0, min_width=250):
                sidebar = gr.HTML(panel.sidebar_html("work"))

            # -- the work area ----------------------------------------------
            with gr.Column(scale=5):
                metrics = gr.HTML(panel.metrics_html())
                status = gr.HTML()

                with gr.Tabs():
                    # Work is first because it is what someone opens ARTEMIS
                    # to do. Inspection and settings come after.
                    with gr.Tab("Work"):
                        gr.HTML(
                            '<div class="a-h1">What would you like done?</div>'
                            '<div class="a-sub">ARTEMIS plans the work and shows '
                            "you every step. Nothing changes until you say yes."
                            "</div>"
                        )

                        with gr.Row():
                            work_picker = gr.Dropdown(
                                choices=panel.choices(),
                                label="In this folder",
                                interactive=True,
                                scale=3,
                            )
                            ask_box = gr.Textbox(
                                label="What would you like done",
                                placeholder="Tidy up this folder",
                                scale=5,
                            )
                            ask_btn = gr.Button("Ask", variant="primary", scale=1)

                        with gr.Row():
                            tidy_btn = gr.Button("Suggest a tidy-up")
                            resume_btn = gr.Button("What changed")
                            patterns_btn = gr.Button("Repeated tasks")
                            undo_btn = gr.Button("Undo last change")

                        conversation = gr.HTML()
                        approval_card = gr.HTML()

                        # Hidden until something is actually awaiting a
                        # decision. Buttons offering to confirm a plan that
                        # does not exist are the most confusing thing a page
                        # can show.
                        with gr.Row(visible=False) as decision_row:
                            approve_btn = gr.Button("Approve", variant="primary")
                            remember_btn = gr.Button("Approve, don't ask again")
                            reject_btn = gr.Button("No, leave it", variant="stop")

                        resume_card = gr.HTML()

                    with gr.Tab("Folders"):
                        gr.HTML(
                            '<div class="a-h1">Folders ARTEMIS can see</div>'
                            '<div class="a-sub">It can only ever see folders you '
                            "add here, and nothing outside them.</div>"
                        )
                        with gr.Row():
                            folder_box = gr.Textbox(
                                label="Folder to add",
                                placeholder=r"C:\Users\you\Documents\Thesis",
                                scale=6,
                            )
                            browse_btn = gr.Button("Browse", scale=1)
                            add_btn = gr.Button(
                                "Add folder", variant="primary", scale=1
                            )
                        cards = gr.HTML(panel.cards_html())

                    with gr.Tab("What it knows"):
                        gr.HTML(
                            '<div class="a-h1">Everything ARTEMIS holds</div>'
                            '<div class="a-sub">Forget never deletes. These '
                            "buttons remove what ARTEMIS remembers; your files "
                            "stay exactly where they are.</div>"
                        )
                        with gr.Row():
                            picker = gr.Dropdown(
                                choices=panel.choices(),
                                label="Folder",
                                interactive=True,
                                scale=4,
                            )
                            show_btn = gr.Button("Show files", scale=1)
                            rescan_btn = gr.Button("Check for changes", scale=1)
                            forget_btn = gr.Button(
                                "Forget this folder", variant="stop", scale=1
                            )
                        files = gr.HTML(panel.files_html(None))
                        erase_btn = gr.Button(
                            "Erase everything ARTEMIS knows", variant="stop"
                        )

                    with gr.Tab("Settings"):
                        gr.HTML(
                            '<div class="a-h1">Where ARTEMIS keeps what it '
                            "knows</div>"
                            '<div class="a-sub">Everything it remembers lives in '
                            "one folder on this computer. Move it anywhere, "
                            "including another drive.</div>"
                        )
                        location = gr.HTML(_location_html(panel.store_location()))
                        with gr.Row():
                            move_box = gr.Textbox(
                                label="New location",
                                placeholder=r"D:\ARTEMIS",
                                scale=6,
                            )
                            move_browse = gr.Button("Browse", scale=1)
                            move_btn = gr.Button("Move it here", scale=1)

                        gr.HTML(
                            '<div class="a-h1" style="margin-top:28px">Cloud '
                            "models</div>"
                            '<div class="a-sub">ARTEMIS uses the model on this '
                            "computer by default. A cloud model is faster, but "
                            "your request leaves this machine, so it is only "
                            "used for folders you have set to allow it.</div>"
                        )
                        cloud_state = gr.HTML(panel.cloud_html())
                        with gr.Row():
                            cloud_pick = gr.Dropdown(
                                choices=panel.provider_choices(),
                                label="Service",
                                scale=3,
                            )
                            key_box = gr.Textbox(
                                label="API key",
                                placeholder="Paste the key here",
                                type="password",
                                scale=5,
                            )
                            save_key_btn = gr.Button("Save key", scale=2)
                            forget_key_btn = gr.Button("Forget key", scale=2)
                        cloud_note = gr.HTML()

        # -- wiring. Each action returns the same four outputs so the page is
        # always re-read from the stores rather than patched in place.
        def refresh(message: str = "", workspace_id: int | None = None):
            return (
                panel.cards_html(),
                panel.metrics_html(),
                gr.update(choices=panel.choices()),
                message,
                panel.files_html(workspace_id),
                gr.update(choices=panel.choices()),
                panel.sidebar_html("work"),
            )

        outputs = [
            cards, metrics, picker, status, files, work_picker, sidebar
        ]

        add_btn.click(
            lambda folder: refresh(panel.add(folder)),
            inputs=folder_box,
            outputs=outputs,
        ).then(lambda: "", outputs=folder_box)

        browse_btn.click(_browse, outputs=folder_box)

        show_btn.click(
            lambda ws: refresh("", ws), inputs=picker, outputs=outputs
        )
        rescan_btn.click(
            lambda ws: refresh(panel.rescan(ws), ws), inputs=picker, outputs=outputs
        )
        forget_btn.click(
            lambda ws: refresh(panel.forget_workspace(ws)),
            inputs=picker,
            outputs=outputs,
        )
        erase_btn.click(lambda: refresh(panel.forget_everything()), outputs=outputs)

        # Moving the store changes where every later query reads from, so the
        # whole page is refreshed afterwards, not just the location line.
        def do_move(destination: str):
            message = panel.move_store(destination)
            return (*refresh(message), _location_html(panel.store_location()))

        # -- the assistant ------------------------------------------------
        # Every handler returns the conversation line and the approval card
        # together, so the card is always cleared by whatever answers it. A
        # stale approval card offering to run a plan that was already decided
        # would be the worst possible bug in this surface.

        def refresh_after_change(message_html: str, card_html: str, ws):
            return (
                message_html,
                card_html,
                panel.cards_html(),
                panel.metrics_html(),
                assistant.resume_html(ws),
                panel.sidebar_html("work"),
                gr.update(visible=bool(card_html)),
            )

        assistant_outputs = [
            conversation, approval_card, cards, metrics, resume_card, sidebar,
            decision_row,
        ]

        def ask_progressively(ws, text):
            """Stream the turn to the page.

            A generator event handler, so Gradio pushes each yield to the
            browser as it arrives. The local model needs about six seconds for a
            plan but produces its first output in about one, which is the
            difference between a frozen page and a visibly working one.
            """
            for message_html, card_html in assistant.ask_streaming(ws, text):
                yield refresh_after_change(message_html, card_html, ws)

        ask_btn.click(
            ask_progressively,
            inputs=[work_picker, ask_box],
            outputs=assistant_outputs,
        ).then(lambda: "", outputs=ask_box)

        ask_box.submit(
            ask_progressively,
            inputs=[work_picker, ask_box],
            outputs=assistant_outputs,
        ).then(lambda: "", outputs=ask_box)

        tidy_btn.click(
            lambda ws: refresh_after_change(*assistant.suggest_tidy(ws), ws),
            inputs=work_picker,
            outputs=assistant_outputs,
        )

        approve_btn.click(
            lambda ws: refresh_after_change(*assistant.approve(remember=False), ws),
            inputs=work_picker,
            outputs=assistant_outputs,
        )

        remember_btn.click(
            lambda ws: refresh_after_change(*assistant.approve(remember=True), ws),
            inputs=work_picker,
            outputs=assistant_outputs,
        )

        reject_btn.click(
            lambda ws: refresh_after_change(*assistant.reject(), ws),
            inputs=work_picker,
            outputs=assistant_outputs,
        )

        undo_btn.click(
            lambda ws: refresh_after_change(assistant.undo_last(), "", ws),
            inputs=work_picker,
            outputs=assistant_outputs,
        )

        resume_btn.click(
            lambda ws: assistant.resume_html(ws),
            inputs=work_picker,
            outputs=resume_card,
        )

        patterns_btn.click(
            lambda ws: (
                assistant.look_for_patterns(ws),
                assistant.patterns_html(ws),
            ),
            inputs=work_picker,
            outputs=[conversation, resume_card],
        )

        # Choosing a folder shows what changed while the user was away, which
        # is F1 arriving unprompted rather than behind a button.
        work_picker.change(
            lambda ws: assistant.resume_html(ws),
            inputs=work_picker,
            outputs=resume_card,
        )

        def _save_key(provider, key):
            # The key is not echoed back into the box, and the box is cleared,
            # so a pasted secret is not left sitting on screen.
            message = panel.save_key(provider, key)
            return panel.cloud_html(), _say_html(message), ""

        def _forget_key(provider):
            return panel.cloud_html(), _say_html(panel.forget_cloud_key(provider)), ""

        save_key_btn.click(
            _save_key,
            inputs=[cloud_pick, key_box],
            outputs=[cloud_state, cloud_note, key_box],
        )
        forget_key_btn.click(
            _forget_key,
            inputs=[cloud_pick],
            outputs=[cloud_state, cloud_note, key_box],
        )

        move_browse.click(_browse, outputs=move_box)
        move_btn.click(
            do_move, inputs=move_box, outputs=[*outputs, location]
        ).then(lambda: "", outputs=move_box)

    return page


def launch(inbrowser: bool = True, port: int | None = None) -> None:
    """Serve the interface on this machine only."""
    store = Store()
    page = build(store)
    try:
        page.launch(
            # Styling moved to launch() in Gradio 6; on Blocks() it is dropped.
            theme=THEME,
            css=CSS,
            server_name="127.0.0.1",  # loopback only, never a public interface
            server_port=port,
            inbrowser=inbrowser,
            quiet=True,
            show_error=True,
            # Removes Gradio's own footer: "Use via API", "Built with Gradio"
            # and "Settings". None of the three belong in this interface.
            footer_links=[],
            favicon_path=None,
        )
    finally:
        store.close()


if __name__ == "__main__":
    launch()
