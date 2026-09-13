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
from artemis.data.store import Store

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
/* Light cyberpunk.

   Cyberpunk normally means neon on black. On a light ground the same energy has
   to come from saturated gradient light rather than glow, so the palette runs
   electric magenta into cyan over near-white, and the glass panels pick up
   colour from a slow aurora moving behind them. Text stays near-black for
   contrast, because vibrancy must not cost legibility. */
:root {
  --a-bg: #f7f4ff;
  --a-glass: rgba(255, 255, 255, 0.62);
  --a-glass-hi: rgba(255, 255, 255, 0.86);
  --a-border: rgba(160, 92, 255, 0.20);
  --a-border-hi: rgba(214, 31, 205, 0.55);
  --a-magenta: #d61fcd;
  --a-violet: #7b3ff2;
  --a-cyan: #00c2d1;
  --a-lime: #00c68a;
  --a-danger: #e8265f;
  --a-text: #1a1130;
  --a-muted: #4a4370;
}

.gradio-container, body, gradio-app {
  background: var(--a-bg) !important;
  color: var(--a-text) !important;
}

/* The aurora. Three saturated blooms drifting slowly, so the glass above has
   something to refract. Fixed and non-interactive; it never competes for
   attention because nothing about it is sudden. */
.gradio-container::before {
  content: "";
  position: fixed; inset: -12%; z-index: 0; pointer-events: none;
  background: radial-gradient(42rem 42rem at 14% 4%, rgba(214,31,205,.30), transparent 62%), radial-gradient(38rem 38rem at 92% 12%, rgba(0,194,209,.30), transparent 62%), radial-gradient(46rem 46rem at 52% 104%, rgba(123,63,242,.26), transparent 64%);
  filter: saturate(135%);
  animation: a-aurora 26s ease-in-out infinite alternate;
}
@keyframes a-aurora {
  from { transform: translate3d(0,0,0) scale(1) rotate(0deg); }
  to   { transform: translate3d(0,-3%,0) scale(1.1) rotate(4deg); }
}
/* A faint grid, the one overt cyberpunk cue. Kept very low contrast so it
   reads as texture rather than decoration. */
.gradio-container::after {
  content: "";
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image: linear-gradient(rgba(123,63,242,.055) 1px, transparent 1px), linear-gradient(90deg, rgba(123,63,242,.055) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: radial-gradient(circle at 50% 34%, #000 12%, transparent 78%);
  -webkit-mask-image: radial-gradient(circle at 50% 34%, #000 12%, transparent 78%);
}
.gradio-container > * { position: relative; z-index: 1; }

/* Masthead ------------------------------------------------------------- */
.a-head { padding: 30px 4px 10px; }
/* The title paints a gradient into the glyphs themselves.
   The clip and the gradient must be declared together in one rule: splitting
   them across an @supports block leaves the plain background painting as a
   solid bar behind the text in browsers that then also apply the clip.
   `display:inline-block` keeps the painted box tight to the text rather than
   spanning the full line. */
.a-title {
  display: inline-block;
  font-size: 2.3rem; font-weight: 800; letter-spacing: .17em; margin: 0;
  background-image: linear-gradient(96deg, var(--a-violet) 2%, var(--a-magenta) 42%, var(--a-cyan) 88%); background-size: 220% 100%; background-position: 0% 50%;
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: a-rise .7s cubic-bezier(.16,1,.3,1) both, a-hue 14s ease-in-out 1s infinite alternate;
}
/* The gradient slides rather than the hue rotating: rotation would drift the
   brand colours away from the palette, sliding keeps them exact. */
@keyframes a-hue {
  from { background-position: 0% 50%; }
  to   { background-position: 100% 50%; }
}
.a-sub {
  color: var(--a-muted); margin: 10px 0 0; max-width: 62ch; line-height: 1.65;
  animation: a-rise .7s cubic-bezier(.16,1,.3,1) .08s both;
}
.a-rule {
  height: 2px; margin: 20px 0 4px; border: 0; border-radius: 2px;
  background: linear-gradient(90deg, transparent, var(--a-magenta) 22%, var(--a-violet) 50%, var(--a-cyan) 78%, transparent);
  opacity: .55; transform-origin: left;
  animation: a-sweep .9s cubic-bezier(.16,1,.3,1) .14s both;
}
@keyframes a-rise  { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes a-sweep { from { transform: scaleX(0); opacity: 0; } to { transform: scaleX(1); opacity: .55; } }

/* "Local only" as a visible state rather than a claim. */
.a-status {
  display: inline-flex; align-items: center; gap: 9px;
  font-size: .78rem; letter-spacing: .13em; text-transform: uppercase;
  color: var(--a-muted); margin-top: 14px; font-weight: 600;
}
/* Glass cards ---------------------------------------------------------- */
.a-cards { display: flex; flex-direction: column; gap: 14px; margin-top: 6px; }
.a-card {
  position: relative; overflow: hidden;
  background: var(--a-glass);
  border: 1px solid var(--a-border);
  border-radius: 18px;
  padding: 18px 20px;
  backdrop-filter: blur(22px) saturate(180%);
  -webkit-backdrop-filter: blur(22px) saturate(180%);
  box-shadow: 0 8px 32px -16px rgba(90,40,160,.32), inset 0 1px 0 rgba(255,255,255,.85);
  transition: transform .32s cubic-bezier(.16,1,.3,1), border-color .3s ease, box-shadow .32s ease, background .3s ease;
  animation: a-card-in .55s cubic-bezier(.16,1,.3,1) both;
}
.a-card:nth-child(1){animation-delay:.02s}
.a-card:nth-child(2){animation-delay:.09s}
.a-card:nth-child(3){animation-delay:.16s}
.a-card:nth-child(4){animation-delay:.23s}
.a-card:nth-child(n+5){animation-delay:.30s}
@keyframes a-card-in {
  from { opacity: 0; transform: translateY(20px) scale(.98); filter: blur(6px); }
  to   { opacity: 1; transform: none; filter: none; }
}
.a-card:hover {
  transform: translateY(-4px);
  background: var(--a-glass-hi);
  border-color: var(--a-border-hi);
  box-shadow: 0 20px 46px -18px rgba(214,31,205,.42), inset 0 1px 0 rgba(255,255,255,.95);
}
/* A neon filament sweeps the top edge on hover. */
.a-card::after {
  content: ""; position: absolute; left: 0; top: 0; height: 2px; width: 100%;
  background: linear-gradient(90deg, transparent, var(--a-magenta), var(--a-cyan), transparent);
  transform: translateX(-100%); opacity: 0; transition: opacity .3s ease;
}
.a-card:hover::after { opacity: 1; animation: a-scan 1.25s ease-in-out infinite; }
@keyframes a-scan { from { transform: translateX(-100%);} to { transform: translateX(100%);} }

.a-card-top { display: flex; align-items: baseline; justify-content: space-between; gap: 14px; }
.a-card-name { font-size: 1.1rem; font-weight: 700; letter-spacing: .01em; }
.a-chip {
  font-size: .72rem; letter-spacing: .09em; text-transform: uppercase;
  font-weight: 700; color: #fff; border-radius: 999px; padding: 4px 12px;
  white-space: nowrap;
  background: linear-gradient(135deg, var(--a-magenta), var(--a-violet));
  box-shadow: 0 4px 14px -6px rgba(214,31,205,.75);
}
.a-card-path {
  font-family: var(--font-mono, monospace);
  font-size: .79rem; color: var(--a-muted); margin-top: 8px;
  word-break: break-all; line-height: 1.5;
}
.a-card-meta { font-size: .85rem; color: var(--a-muted); margin-top: 9px; }

/* Empty state ---------------------------------------------------------- */
.a-empty {
  border: 1.5px dashed rgba(123,63,242,.34); border-radius: 18px;
  padding: 46px 22px; text-align: center;
  background: rgba(255,255,255,.5);
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
  animation: a-card-in .6s cubic-bezier(.16,1,.3,1) both;
}
.a-empty-title { font-size: 1.15rem; font-weight: 700; }
.a-empty-body  { color: var(--a-muted); margin-top: 10px; line-height: 1.65; }
.a-eye {
  width: 52px; height: 52px; margin: 0 auto 18px; border-radius: 50%;
  display: grid; place-items: center; color: #fff; font-size: 1.25rem;
  background: linear-gradient(135deg, var(--a-violet), var(--a-magenta));
  box-shadow: 0 10px 28px -10px rgba(123,63,242,.7);
  animation: a-breathe 3.4s ease-in-out infinite;
}
@keyframes a-breathe {
  0%,100% { transform: scale(1);    box-shadow: 0 10px 28px -10px rgba(123,63,242,.55); }
  50%     { transform: scale(1.08); box-shadow: 0 16px 38px -10px rgba(214,31,205,.85); }
}

/* Metrics -------------------------------------------------------------- */
.a-metrics { display: flex; gap: 12px; flex-wrap: wrap; margin: 4px 0 2px; }
.a-metric {
  flex: 1 1 130px; background: var(--a-glass);
  border: 1px solid var(--a-border); border-radius: 16px; padding: 14px 17px;
  backdrop-filter: blur(20px) saturate(170%);
  -webkit-backdrop-filter: blur(20px) saturate(170%);
  box-shadow: 0 6px 24px -14px rgba(90,40,160,.34), inset 0 1px 0 rgba(255,255,255,.85);
  animation: a-card-in .5s cubic-bezier(.16,1,.3,1) both;
  transition: border-color .3s ease, transform .3s ease, box-shadow .3s ease;
}
.a-metric:hover {
  border-color: var(--a-border-hi); transform: translateY(-3px);
  box-shadow: 0 16px 34px -16px rgba(214,31,205,.45);
}
/* Same one-rule treatment as the title, and inline-block so the gradient is
   clipped to the digits instead of filling the metric card's width. */
.a-metric-n {
  display: inline-block;
  font-size: 1.85rem; font-weight: 800; line-height: 1.1;
  font-variant-numeric: tabular-nums;
  background-image: linear-gradient(135deg, var(--a-violet), var(--a-magenta));
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
.a-metric-l {
  font-size: .7rem; letter-spacing: .13em; text-transform: uppercase;
  color: var(--a-muted); margin-top: 6px; font-weight: 600;
}

/* Gradio component overrides ------------------------------------------- */
.gradio-container .block,
.gradio-container .form,
.gradio-container .panel { background: transparent !important; border: none !important; }

.gradio-container button {
  border-radius: 13px !important;
  transition: transform .2s cubic-bezier(.16,1,.3,1), box-shadow .25s ease, filter .25s ease !important;
}
.gradio-container button:hover { transform: translateY(-2px); }
.gradio-container button:active { transform: translateY(0) scale(.985); }

.gradio-container button.primary {
  background: linear-gradient(135deg, var(--a-magenta), var(--a-violet)) !important;
  border: none !important; color: #fff !important; font-weight: 700 !important;
  box-shadow: 0 10px 28px -12px rgba(214,31,205,.85) !important;
}
.gradio-container button.primary:hover {
  filter: brightness(1.07);
  box-shadow: 0 16px 36px -12px rgba(214,31,205,1) !important;
}
.gradio-container button.secondary {
  background: rgba(255,255,255,.72) !important;
  border: 1px solid var(--a-border) !important;
  color: var(--a-text) !important; font-weight: 600 !important;
  backdrop-filter: blur(14px);
}
.gradio-container button.secondary:hover {
  border-color: var(--a-border-hi) !important;
}
.gradio-container button.stop, .gradio-container button.danger {
  background: rgba(232,38,95,.10) !important;
  border: 1px solid rgba(232,38,95,.45) !important;
  color: var(--a-danger) !important; font-weight: 650 !important;
}
.gradio-container button.stop:hover {
  background: rgba(232,38,95,.16) !important;
}

.gradio-container input[type=text], .gradio-container textarea,
.gradio-container .wrap.svelte-1hfxrpf, .gradio-container select {
  background: rgba(255,255,255,.78) !important;
  border: 1px solid var(--a-border) !important;
  border-radius: 13px !important; color: var(--a-text) !important;
  backdrop-filter: blur(12px);
  transition: border-color .25s ease, box-shadow .25s ease !important;
}
.gradio-container input[type=text]:focus, .gradio-container textarea:focus {
  border-color: var(--a-magenta) !important;
  box-shadow: 0 0 0 4px rgba(214,31,205,.14) !important;
}
.gradio-container label span { color: var(--a-text) !important; font-weight: 600 !important; }

/* Toast ---------------------------------------------------------------- */
.a-toast {
  border-left: 3px solid var(--a-magenta);
  background: linear-gradient(90deg, rgba(214,31,205,.13), rgba(255,255,255,.5) 70%);
  padding: 12px 16px; border-radius: 0 13px 13px 0;
  font-size: .92rem; color: var(--a-text); font-weight: 500;
  backdrop-filter: blur(14px);
  animation: a-toast-in .45s cubic-bezier(.16,1,.3,1) both;
}
.a-toast.warn {
  border-left-color: var(--a-danger);
  background: linear-gradient(90deg, rgba(232,38,95,.14), rgba(255,255,255,.5) 70%);
}
@keyframes a-toast-in {
  from { opacity: 0; transform: translateX(-16px); }
  to   { opacity: 1; transform: none; }
}

/* Store location -------------------------------------------------------- */
.a-section { font-size: 1.05rem; font-weight: 700; margin: 4px 0 6px; }
.a-location {
  display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
  margin: 10px 0 2px; padding: 12px 16px; border-radius: 14px;
  background: rgba(255,255,255,.78); border: 1px solid var(--a-border);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
}
.a-location-label {
  font-size: .7rem; letter-spacing: .13em; text-transform: uppercase;
  color: var(--a-muted); font-weight: 700; white-space: nowrap;
}
.a-location-path {
  font-family: var(--font-mono, monospace); font-size: .84rem;
  color: var(--a-text); word-break: break-all;
}

/* File rows ------------------------------------------------------------ */
.a-files { display: flex; flex-direction: column; gap: 7px; }
.a-file {
  display: flex; justify-content: space-between; gap: 12px;
  font-family: var(--font-mono, monospace); font-size: .82rem;
  padding: 10px 14px; border-radius: 11px;
  color: var(--a-text); background: rgba(255,255,255,.86); border: 1px solid var(--a-border);
  backdrop-filter: blur(12px);
  animation: a-card-in .4s cubic-bezier(.16,1,.3,1) both;
  transition: border-color .25s ease, transform .25s ease, background .25s ease;
}
.a-file:hover {
  border-color: var(--a-border-hi); transform: translateX(4px);
  background: rgba(255,255,255,.96);
}
.a-file-name { color: var(--a-text) !important; }
.a-file-size { color: var(--a-muted) !important; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .001ms !important; animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
  }
}
"""


def _esc(value: object) -> str:
    """Escape anything interpolated into the raw HTML blocks."""
    return html.escape(str(value), quote=True)


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

    # -- queries -----------------------------------------------------------

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

    with gr.Blocks(title="ARTEMIS", fill_width=True) as page:
        gr.HTML(
            '<div class="a-head">'
            '<h1 class="a-title">A R T E M I S</h1>'
            '<p class="a-sub">ARTEMIS can only see folders you add here. '
            "Everything it knows is stored on this computer and has not been "
            "sent anywhere. You can take any of it away at any time.</p>"
            '<div class="a-status">'
            "local only \u00b7 nothing leaves this machine</div>"
            '<hr class="a-rule"/></div>'
        )

        metrics = gr.HTML(panel.metrics_html())
        status = gr.HTML()

        with gr.Row():
            folder_box = gr.Textbox(
                label="Folder to let ARTEMIS see",
                placeholder=r"C:\Users\you\Documents\Thesis",
                scale=6,
            )
            browse_btn = gr.Button("Browse", scale=1)
            add_btn = gr.Button("Add folder", variant="primary", scale=1)

        cards = gr.HTML(panel.cards_html())

        gr.HTML('<hr class="a-rule"/>')

        with gr.Row():
            picker = gr.Dropdown(
                choices=panel.choices(),
                label="Work with one folder",
                interactive=True,
                scale=4,
            )
            show_btn = gr.Button("Show files", scale=1)
            rescan_btn = gr.Button("Check for changes", scale=1)
            forget_btn = gr.Button("Forget this folder", variant="stop", scale=1)

        files = gr.HTML(panel.files_html(None))

        with gr.Row():
            erase_btn = gr.Button("Erase everything ARTEMIS knows", variant="stop")

        gr.HTML('<hr class="a-rule"/>')

        gr.HTML(
            '<div class="a-section">Where ARTEMIS keeps what it knows</div>'
            '<div class="a-card-meta">Everything ARTEMIS remembers lives in one '
            "folder on this computer. Move it anywhere you like, including onto "
            "another drive.</div>"
        )
        location = gr.HTML(_location_html(panel.store_location()))

        with gr.Row():
            move_box = gr.Textbox(
                label="New location for that folder",
                placeholder=r"D:\ARTEMIS",
                scale=6,
            )
            move_browse = gr.Button("Browse", scale=1)
            move_btn = gr.Button("Move it here", scale=1)

        gr.HTML(
            '<div class="a-card-meta" style="margin-top:18px">'
            "Forget never deletes. Every button here removes what ARTEMIS "
            "remembers; your files stay exactly where they are.</div>"
        )

        # -- wiring. Each action returns the same four outputs so the page is
        # always re-read from the stores rather than patched in place.
        def refresh(message: str = "", workspace_id: int | None = None):
            return (
                panel.cards_html(),
                panel.metrics_html(),
                gr.update(choices=panel.choices()),
                message,
                panel.files_html(workspace_id),
            )

        outputs = [cards, metrics, picker, status, files]

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
