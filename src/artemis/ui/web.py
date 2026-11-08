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

import logging
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
from artemis.core.modelconfig import ModelNameError, ModelSettings
from artemis.services import mail as mailsvc
from artemis.data import credentials
from artemis.services.resume import ResumeService
from artemis.services.speech import NotArmed, SpeechUnavailable, VoiceSession, greeting
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
.gradio-container { width: 100% !important; max-width: 1280px !important; margin: 0 auto !important; }

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
.a-steps { display: flex; flex-direction: column; gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: var(--r); max-height: 300px; overflow-y: auto; }
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

.a-hidden { display: none !important; }
.a-decision { margin: 6px 0 12px; }
.a-decision button[disabled] { opacity: .45; }

/* Dark theme. Chosen with the switch in the sidebar and remembered. */
.dark {
  --page: #0b1120; --surface: #111a2e; --raised: #1a2540; --line: #243049; --line-firm: #34425e;
  --text: #e5e9f2; --muted: #a3aec4; --faint: #8b97b0;
  --accent: #8b93ff; --accent-hover: #a3a9ff; --accent-wash: #1d2347;
  --ok: #4ade80; --ok-wash: #0f2a1f; --danger: #fb7185; --danger-wash: #34121c;
}
.dark .a-d-add { background: #0f2a1f !important; color: #86efac !important; }
.dark .a-d-del { background: #34121c !important; color: #fda4af !important; }
.dark .a-note, .dark .a-assure { border-color: #14532d; }
.dark .a-msg.warn, .dark .a-warn-line, .dark .a-flag { border-color: #7f1d1d; }
.dark .a-guide { border-color: #34425e; }
.dark .a-pill-on, .dark .a-cloud-on { background: #0f2a1f; color: #86efac !important; }
.dark .a-chip { border-color: #34425e; }
.dark .a-user { background: #4f46e5; }
.dark .gradio-container button.primary { color: #ffffff !important; background: #4f46e5 !important; border-color: #4f46e5 !important; }
.dark .gradio-container input::placeholder, .dark .gradio-container textarea::placeholder { color: var(--faint) !important; }
.dark .a-user, .dark .a-user * { color: #ffffff !important; }

/* Conversation */
.a-chat { display: flex; flex-direction: column-reverse; gap: 14px; max-height: 520px; overflow-y: auto; padding: 4px 2px; }
.a-turn { display: flex; flex-direction: column; gap: 8px; }
.a-user { align-self: flex-end; max-width: 80%; background: var(--accent); color: #fff; border-radius: 14px 14px 2px 14px; padding: 9px 14px; font-size: .9rem; line-height: 1.5; white-space: pre-wrap; }
/* Explicit colours: inside Gradio's HTML blocks text inherited a pale theme
   colour on some browsers and the reply was close to invisible on white. */
.a-chat-text, .a-msg, .a-msg *, .a-claim, .a-claim *, .a-quote, .a-diff, .a-diff div { color: var(--text) !important; }
.a-msg .a-cite, .a-msg .a-flag, .a-msg .a-model, .a-msg .a-card-meta, .a-msg.warn, .a-d-add, .a-d-del, .a-d-hunk { color: revert-layer; }
.a-approval, .a-approval *, .a-step, .a-step *, .a-fact-v, .a-resume, .a-resume-line { color: var(--text) !important; }
.a-approval-sub, .a-fact-k, .a-steps-head, .a-step-n { color: var(--muted) !important; }
.a-assure { color: var(--ok) !important; }
.a-warn-line { color: var(--danger) !important; }
.a-step-t span[style] { opacity: 1 !important; background: var(--raised); border-radius: 6px; padding: 8px 10px; }
.a-card-meta, .a-card-meta *, .a-sub, .a-sub *, .a-h1, .a-h2, .a-cloud-note { color: var(--muted) !important; }
.a-card-meta strong, .a-h1, .a-h2 { color: var(--text) !important; }
.gradio-container .label-wrap, .gradio-container .label-wrap *, .gradio-container button.label-wrap { color: var(--text) !important; background: transparent !important; }
.gradio-container .wrap, .gradio-container .wrap-inner, .gradio-container .secondary-wrap { background: var(--surface) !important; }
.gradio-container .accordion, .gradio-container .block.padded { background: transparent !important; }
.a-chat-text { white-space: pre-wrap; line-height: 1.65; }
.a-chats label { font-size: .84rem !important; }
.a-chat-text code { background: var(--raised); border-radius: 4px; padding: 1px 5px; font-size: .85em; }
.a-user, .a-user * { color: #ffffff !important; }
.a-model { color: var(--faint) !important; }
.a-cite { color: var(--accent) !important; }
.a-flag { color: var(--danger) !important; }
.a-d-add { color: #065f46 !important; }
.a-d-del { color: #9f1239 !important; }
.a-d-hunk, .a-d-head { color: var(--muted) !important; }
.a-msg.warn, .a-msg.warn * { color: var(--text) !important; }
.a-model { margin-top: 8px; font-size: .74rem; color: var(--faint); font-family: ui-monospace, Consolas, monospace; }
.a-local, .a-local * { color: var(--text) !important; }
.a-local .k { color: var(--muted) !important; }
.a-local { display: grid; grid-template-columns: 1fr auto; gap: 6px 14px; padding: 13px 16px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--r); font-size: .88rem; }
.a-local .k { color: var(--muted); font-weight: 600; }
.a-pill-on { color: #166534; background: #dcfce7; border-radius: 999px; padding: 2px 10px; font-size: .75rem; font-weight: 600; }
.a-pill-off { color: var(--danger); background: var(--danger-wash); border-radius: 999px; padding: 2px 10px; font-size: .75rem; font-weight: 600; }

.a-guide { background: var(--accent-wash); border: 1px solid #c7d2fe; border-radius: var(--r); padding: 14px 18px; }
.a-guide-head { font-weight: 700; margin-bottom: 4px; }
.a-guide ol { margin: 8px 0 0 20px; padding: 0; line-height: 1.75; font-size: .9rem; }
.a-guide, .a-guide *, .a-guide-head { color: var(--text) !important; }

/* Status banner, answers with sources, and diffs. */
.a-status-slot { min-height: 46px; }
.a-toast { padding: 11px 15px; border-radius: var(--r); background: var(--ok-wash); border: 1px solid #a7f3d0; border-left: 3px solid var(--ok); color: var(--text); font-size: .9rem; line-height: 1.5; }
.a-toast.warn { background: var(--danger-wash); border-color: #fecdd3; border-left-color: var(--danger); }
.a-warn-line { margin: 0 0 16px; padding: 9px 13px; border-radius: var(--r); background: var(--danger-wash); border: 1px solid #fecdd3; color: var(--danger); font-size: .85rem; font-weight: 600; }
.a-claim { padding: 8px 0; border-bottom: 1px solid var(--line); line-height: 1.6; font-size: .9rem; }
.a-claim:last-of-type { border-bottom: none; }
.a-cite { color: var(--accent); font-family: ui-monospace, "Cascadia Code", Consolas, monospace; font-size: .78rem; background: var(--accent-wash); border-radius: 4px; padding: 1px 6px; word-break: break-all; }
.a-unsupported { color: var(--muted); }
.a-flag { color: var(--danger); background: var(--danger-wash); border: 1px solid #fecdd3; border-radius: 4px; padding: 1px 7px; font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; margin-right: 6px; }
.a-diff { margin-top: 8px; border: 1px solid var(--line); border-radius: var(--r); overflow-x: auto; font-family: ui-monospace, "Cascadia Code", Consolas, monospace; font-size: .8rem; line-height: 1.6; background: var(--surface); }
.a-diff div { padding: 1px 12px; white-space: pre; }
.a-d-add { background: #ecfdf5; color: #065f46; }
.a-d-del { background: #fff1f2; color: #9f1239; }
.a-d-hunk { background: var(--raised); color: var(--muted); }
.a-d-head { color: var(--faint); font-weight: 700; }

/* Gradio overrides ----------------------------------------------------------- */
.gradio-container .block, .gradio-container .form, .gradio-container .panel { background: transparent !important; border: none !important; }

.gradio-container button { border-radius: var(--r) !important; font-size: .88rem !important; font-weight: 550 !important; padding: 9px 15px !important; transition: background .15s ease, border-color .15s ease !important; }
.gradio-container button.primary { background: var(--accent) !important; border: 1px solid var(--accent) !important; color: #ffffff !important; font-weight: 600 !important; }
.gradio-container button.primary:hover { background: var(--accent-hover) !important; border-color: var(--accent-hover) !important; }
.gradio-container button.secondary { background: var(--surface) !important; border: 1px solid var(--line-firm) !important; color: var(--text) !important; }
.gradio-container button.secondary:hover { background: var(--raised) !important; }
.gradio-container button.stop { background: var(--surface) !important; border: 1px solid #fda4af !important; color: var(--danger) !important; font-weight: 600 !important; }
.gradio-container button.stop:hover { background: var(--danger-wash) !important; }

.gradio-container input[type=text], .gradio-container input[type=password], .gradio-container input[type=number], .gradio-container input[role=listbox], .gradio-container textarea, .gradio-container select { background: var(--surface) !important; border: 1px solid var(--line-firm) !important; border-radius: var(--r) !important; color: var(--text) !important; font-size: .9rem !important; padding: 9px 12px !important; }
.gradio-container input[type=text]:focus, .gradio-container textarea:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(79,70,229,.14) !important; outline: none !important; }
.gradio-container input::placeholder, .gradio-container textarea::placeholder { color: var(--faint) !important; }
.gradio-container label span, .gradio-container .block label, .gradio-container [data-testid=block-info] { color: var(--muted) !important; }
.gradio-container label span { color: var(--muted) !important; font-weight: 600 !important; font-size: .82rem !important; }

/* Tabs: the one navigation. Selected state is a solid underline, not colour
   alone, so it does not rely on hue to be legible. */
.gradio-container button[role=tab] { color: var(--muted) !important; font-weight: 600 !important; border: none !important; border-bottom: 2px solid transparent !important; border-radius: 0 !important; background: transparent !important; }
.gradio-container button[role=tab].selected { color: var(--accent) !important; border-bottom-color: var(--accent) !important; }

.gradio-container button:focus-visible, .gradio-container input:focus-visible, .gradio-container textarea:focus-visible, .gradio-container [role=tab]:focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px !important; }

@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition-duration: .001ms !important; animation-duration: .001ms !important; } }
"""


#: Presses the hidden refresh button once the page has rendered, so a browser
#: refresh re-reads what ARTEMIS holds instead of showing the state from when
#: the server started. Polls briefly because Gradio draws the page after load,
#: then waits a moment for the button's handler to be attached. Delivered in the
#: page head: the `js=` option of launch() was accepted but never ran.
LOAD_HEAD = """<script>
(function () {
  var KEY = 'artemis-theme';
  function wantDark() { try { return localStorage.getItem(KEY) === 'dark'; } catch (e) { return false; } }
  function apply() {
    var dark = wantDark();
    var root = document.documentElement, body = document.body;
    if (root.classList.contains('dark') !== dark) { root.classList.toggle('dark', dark); }
    if (body && body.classList.contains('dark') !== dark) { body.classList.toggle('dark', dark); }
  }
  // Gradio switches itself to dark whenever the operating system is dark, which
  // left half the page dark and half light. The person's own choice wins.
  window.artemisToggleTheme = function () {
    try { localStorage.setItem(KEY, wantDark() ? 'light' : 'dark'); } catch (e) {}
    apply();
  };
  new MutationObserver(apply).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  document.addEventListener('DOMContentLoaded', function () {
    apply();
    new MutationObserver(apply).observe(document.body, { attributes: true, attributeFilter: ['class'] });
  });
  apply();

  // Hands-free voice. While "Voice is on" is ticked, listen after ARTEMIS finishes
  // speaking, and stop listening when the person goes quiet, so it feels like taking
  // turns in a conversation. Nothing records unless the box is ticked.
  (function () {
    var rec = false, waitingSince = 0, heardVoice = false, lastLoud = 0, startedAt = 0, floor = 0, awaiting = 0, sawSpeech = false;
    var nudged = false, nudgeStop = false, sawBusy = false, unheard = false, playTried = 0;
    var ctx = null, analyser = null, buf = null, stream = null;
    function q(id) { return document.getElementById(id); }
    function on() { var c = q('a-voice-on'); var i = c && c.querySelector('input[type=checkbox]'); return !!(i && i.checked); }
    function micButton(word) {
      var m = q('a-mic'); if (!m) return null;
      var bs = m.querySelectorAll('button');
      for (var i = 0; i < bs.length; i++) {
        var t = ((bs[i].getAttribute('aria-label') || '') + ' ' + bs[i].textContent).toLowerCase();
        if (t.indexOf(word) >= 0 && bs[i].offsetParent !== null) return bs[i];
      }
      return null;
    }
    function outButton(word) {
      var o = q('a-voice-out'); if (!o) return null;
      var bs = o.querySelectorAll('button');
      for (var i = 0; i < bs.length; i++) {
        if ((bs[i].getAttribute('aria-label') || '').toLowerCase() === word) return bs[i];
      }
      return null;
    }
    function clipId() {
      var o = q('a-voice-out'); var s = o && o.querySelector('[aria-label^="Skip forward"]');
      return s ? s.getAttribute('aria-label') : '';
    }
    var lastClip = '';
    function speaking() { return !!outButton('pause'); }
    window.__afUnheard = function () { return unheard; };
    window.__afState = function () { return { on: on(), rec: rec, speaking: speaking(), busy: busy(), record: !!micButton('record'), clip: clipId(), last: lastClip }; };
    function busy() { return !!document.querySelector('.a-chat .a-thinking, .a-chat .a-streaming'); }
    function level() {
      analyser.getByteTimeDomainData(buf);
      var s = 0; for (var i = 0; i < buf.length; i++) { var v = (buf[i] - 128) / 128; s += v * v; }
      return Math.sqrt(s / buf.length);
    }
    function listen() {
      if (!navigator.mediaDevices) return;
      navigator.mediaDevices.getUserMedia({ audio: true }).then(function (s) {
        stream = s;
        ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
        var src = ctx.createMediaStreamSource(s);
        analyser = ctx.createAnalyser(); analyser.fftSize = 1024; buf = new Uint8Array(analyser.fftSize);
        src.connect(analyser);
      }).catch(function () {});
    }
    function release() {
      if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
      analyser = null;
    }
    setInterval(function () {
      var now = Date.now();
      if (!on()) { if (rec || stream) { release(); rec = false; } nudged = false; return; }
      // play each new spoken reply once (the page only plays it itself when allowed to)
      var id = clipId(), play = outButton('play');
      if (id && id !== lastClip && play && !rec) { lastClip = id; unheard = true; playTried = now; play.click(); return; }
      var stop = micButton('stop');
      if (stop && rec) {
        var l = analyser ? level() : 0;
        // the room's own noise sets the bar, so a quiet fan is not mistaken for speech
        if (analyser && now - startedAt < 700) { floor = Math.max(floor * 0.8, l); }
        else if (l > Math.max(0.03, floor * 2.5)) { heardVoice = true; lastLoud = now; }
        // A pause of three and a half seconds is the end of what was said.
        if (heardVoice && now - lastLoud > 3500) {
          rec = false; heardVoice = false; nudged = false; nudgeStop = false; waitingSince = now; awaiting = now;
          sawSpeech = false; sawBusy = false; release(); stop.click();
        } else if (!heardVoice && !nudged && now - startedAt > 4000) {
          // Nobody spoke for four seconds, so ARTEMIS speaks first. After that it just
          // keeps listening, however long it takes.
          nudged = true; nudgeStop = true; rec = false; waitingSince = now; awaiting = now;
          sawSpeech = false; sawBusy = false; release(); stop.click();
          setTimeout(function () { var n = q('a-nudge'); if (n) n.click(); }, 300);
        }
        return;
      }
      if (rec && !stop) { rec = false; release(); }
      if (speaking()) { sawSpeech = true; unheard = false; nudgeStop = false; waitingSince = 0; return; }
      if (busy()) { sawBusy = true; waitingSince = 0; return; }
      // The browser may refuse to play sound before the person has touched the page.
      if (unheard && now - playTried < 20000) { return; }
      // After something was said, wait for the spoken reply to start and finish before
      // listening again, so ARTEMIS never hears itself. Give up after a while, or at
      // once if it could not make out what was said.
      if (awaiting) {
        var note = q('a-voice-note'); var txt = note ? note.textContent : '';
        var failed = txt.indexOf('did not catch') >= 0 || txt.indexOf('Voice is off') >= 0 || txt.indexOf('could not') >= 0
          || (!nudgeStop && !sawBusy && now - awaiting > 8000);
        if (sawSpeech || failed || now - awaiting > 60000) { awaiting = 0; } else { return; }
      }
      var go = micButton('record');
      if (go && !rec) {
        waitingSince = 0; rec = true; heardVoice = false; startedAt = now; lastLoud = now; floor = 0;
        listen(); go.click();
      }
    }, 400);
  })();

  // Sound may be blocked until the first touch of the page; play what is waiting then.
  document.addEventListener('pointerdown', function () {
    var o = document.getElementById('a-voice-out');
    var b = o && Array.prototype.filter.call(o.querySelectorAll('button'), function (x) {
      return (x.getAttribute('aria-label') || '').toLowerCase() === 'play';
    })[0];
    if (window.__afUnheard && window.__afUnheard() && b) { b.click(); }
  });
  var tries = 0;
  var timer = setInterval(function () {
    var button = document.getElementById('a-refresh');
    if (button) {
      clearInterval(timer);
      setTimeout(function () { button.click(); }, 700);
      // Voice starts on its own: ARTEMIS greets and listens. The box can be unticked.
      setTimeout(function () {
        var a = document.getElementById('a-autostart');
        if (a) { a.click(); }
      }, 1500);
    } else if (++tries > 80) {
      clearInterval(timer);
    }
  }, 250);
})();
</script>"""


#: Common email providers, so nobody has to know what a "server" or a "port" is.
#: Each is (server, port, security, a hint shown to the person).
MAIL_PRESETS = {
    "Gmail": ("smtp.gmail.com", 465, "ssl",
              "Gmail needs an app password, not your normal one. Google account > Security > 2-Step Verification > App passwords."),
    "Outlook / Hotmail": ("smtp-mail.outlook.com", 587, "starttls",
                          "Use your normal Outlook password, or an app password if you use two-step sign-in."),
    "Yahoo": ("smtp.mail.yahoo.com", 465, "ssl",
              "Yahoo needs an app password: Account security > Generate app password."),
    "iCloud": ("smtp.mail.me.com", 587, "starttls",
               "iCloud needs an app password from appleid.apple.com."),
    "Other": ("", 465, "ssl", "Ask your email provider for the outgoing (SMTP) server, or open Advanced below."),
}


#: Step-by-step help for each provider, in plain words. Gmail, Yahoo and iCloud do
#: not accept a normal password from a program like ARTEMIS; they want an "app
#: password", a separate password made just for it.
MAIL_GUIDE = {
    "Gmail": (
        "Gmail does not let programs use your normal password. You make a special one, once:",
        [
            "Open <b>myaccount.google.com/apppasswords</b> in your browser and sign in.",
            "(If it says the page is not available: go to <b>Security</b> and turn on <b>2-Step Verification</b> first, then try again.)",
            "Type a name such as <b>ARTEMIS</b> and press <b>Create</b>.",
            "Google shows 16 letters in a yellow box. Copy them. Google only shows them once.",
            "Paste them in <b>Your password</b> below. Spaces do not matter.",
            "Press <b>Connect my email</b>, then <b>Test connection</b>.",
        ],
    ),
    "Outlook / Hotmail": (
        "Outlook usually accepts your normal password. If it does not (because you use two-step sign-in), make an app password:",
        [
            "Sign in at <b>account.microsoft.com</b> and open <b>Security</b>.",
            "Open <b>Advanced security options</b> and choose <b>Create a new app password</b>.",
            "Paste it in <b>Your password</b> below, then press <b>Connect my email</b> and <b>Test connection</b>.",
        ],
    ),
    "Yahoo": (
        "Yahoo needs a special app password:",
        [
            "Sign in at <b>login.yahoo.com</b> and open <b>Account security</b>.",
            "Choose <b>Generate app password</b>, name it <b>ARTEMIS</b>, and copy it.",
            "Paste it in <b>Your password</b> below, then press <b>Connect my email</b> and <b>Test connection</b>.",
        ],
    ),
    "iCloud": (
        "iCloud needs a special app password:",
        [
            "Sign in at <b>appleid.apple.com</b> and open <b>Sign-In and Security</b>.",
            "Choose <b>App-Specific Passwords</b>, press <b>+</b>, name it <b>ARTEMIS</b>, and copy it.",
            "Paste it in <b>Your password</b> below, then press <b>Connect my email</b> and <b>Test connection</b>.",
        ],
    ),
    "Other": (
        "Ask your email provider for the outgoing mail (SMTP) server, or look it up on their help page.",
        [
            "Open <b>Advanced</b> below and type the server name and port they give you.",
            "Type your address and password, then press <b>Connect my email</b> and <b>Test connection</b>.",
        ],
    ),
}


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

        The counts used to be repeated here and in the cards across the top,
        which showed the same three numbers twice. They live in the cards now;
        this holds the name and the promise.
        """
        return (
            '<div class="a-side">'
            '<div class="a-brand">ARTEMIS</div>'
            '<div class="a-brand-sub">Bounded desktop assistant</div>'
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
            cloud_line = (
                "Cloud models are allowed here: what you type may leave this computer."
                if w.cloud_policy == "cloud_allowed"
                else "Cloud models are off here: everything stays on this computer."
            )
            cards.append(
                '<div class="a-card">'
                '<div class="a-card-top">'
                f'<div class="a-card-name">{_esc(w.name)}</div>'
                f'<div class="a-chip">{_esc(_plural(count, "file"))}</div>'
                "</div>"
                f'<div class="a-card-path">{_esc(w.root)}</div>'
                f'<div class="a-card-meta">ARTEMIS {access}</div>'
                f'<div class="a-card-meta">{cloud_line}</div>'
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

    def set_cloud_policy(self, workspace_id: int, allow: bool) -> None:
        self._store.set_cloud_policy(workspace_id, "cloud_allowed" if allow else "local_only")

    def chat_cloud(self) -> bool:
        return self._store.get_setting("cloud.chat") == "1"

    def set_chat_cloud(self, on: bool) -> str:
        self._store.set_setting("cloud.chat", "1" if on else "0")
        return self.toast(
            "Plain chat may now use your cloud model." if on else "Plain chat stays on this computer."
        )

    def first_workspace_id(self) -> int | None:
        found = self._manager.list()
        return found[0].id if found else None

    def workspace_name(self, workspace_id: int | None) -> str:
        ws = self._manager.get(workspace_id) if workspace_id else None
        return ws.name if ws else ""

    def add(self, folder: str) -> str:
        self.last_added: int | None = None
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
        self.last_added = ws.id
        return self.toast(
            f"Added '{ws.name}'. ARTEMIS now knows about "
            f"{_plural(count, 'file')} in it."
        )

    def rescan(self, workspace_id: int | None) -> str:
        if not workspace_id:
            return self.toast("Choose a folder first.", warn=True)
        def snapshot() -> dict:
            return {
                r["rel_path"]: (r["mtime"], r["size"])
                for r in self._store.list_files(workspace_id)
            }

        before = snapshot()
        self._indexer.scan(workspace_id)
        after = snapshot()
        # Said in terms of what changed, not how many files there are. Comparing
        # only the totals reported "nothing has changed" for a folder where one
        # file was added and another removed, because the count came out equal.
        report = self._resume.report(workspace_id)
        if not report.is_first_visit:
            return self.toast("Checked. " + report.summary())
        added = len(after.keys() - before.keys())
        gone = len(before.keys() - after.keys())
        edited = sum(1 for k in before.keys() & after.keys() if before[k] != after[k])
        if not (added or gone or edited):
            return self.toast("Checked. Nothing has changed since last time.")
        bits = [
            f"{n} {label}"
            for n, label in ((added, "new"), (edited, "changed"), (gone, "gone"))
            if n
        ]
        return self.toast("Checked. " + ", ".join(bits) + ".")

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
        self._store.delete_all_chats()
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
                f'<span class="a-cloud-model">{_esc(self.models().cloud_model(entry["name"]))}</span>'
                f'<span class="{tone}">{state}</span></div>'
            )
        return (
            '<div class="a-cloud">' + "".join(rows) + "</div>"
            '<div class="a-cloud-note">Keys are kept in the Windows Credential '
            "Manager, never in the ARTEMIS folder. A cloud model is only used "
            "for a folder you have set to allow it.</div>"
        )

    # -- models --------------------------------------------------------------

    def models(self) -> ModelSettings:
        return ModelSettings(self._store)

    def local_models_html(self) -> str:
        """Which local models were found, and which one ARTEMIS is using."""
        status = self.models().local_status(refresh=True)
        if not status.running:
            return (
                '<div class="a-local"><span class="k">Local models</span>'
                '<span class="a-pill-off">Ollama not running</span>'
                '<span>ARTEMIS could not reach Ollama on this computer. Start it, '
                "then press Check again.</span><span></span></div>"
            )
        if status.models:
            found = "".join(
                f'<div class="a-cloud-row"><span class="a-cloud-name">{_esc(m.name)}</span>'
                f'<span class="a-cloud-model">{_esc(m.size_label)}</span>'
                + ('<span class="a-pill-on">In use</span>' if m.name == status.active else "")
                + "</div>"
                for m in status.models
            )
            found = f'<div class="a-cloud">{found}</div>'
        else:
            found = '<div class="a-cloud-note">Ollama is running but has no models installed.</div>'
        how = "you chose this" if status.chosen else "chosen automatically"
        warn = "" if status.active_installed else (
            f'<div class="a-warn-line">\u201c{_esc(status.active)}\u201d is not installed in '
            "Ollama, so local answers will fail until you pick an installed model.</div>"
        )
        return (
            f'<div class="a-card-meta">Using <strong>{_esc(status.active)}</strong> ({how}).</div>'
            f"{found}{warn}"
        )

    def local_model_choices(self) -> list[str]:
        return self.models().local_status().names

    def set_local_model(self, name: str) -> str:
        try:
            chosen = self.models().set_local_model(name)
        except ModelNameError as exc:
            return self.toast(str(exc), warn=True)
        return self.toast(f"ARTEMIS will use {chosen} on this computer.")

    def reset_local_model(self) -> str:
        self.models().reset_local_model()
        return self.toast("Back to choosing the local model automatically.")

    def set_cloud_model(self, provider: str, name: str) -> str:
        if not provider:
            return self.toast("Choose which service first.", warn=True)
        try:
            chosen = self.models().set_cloud_model(provider, name)
        except ModelNameError as exc:
            return self.toast(str(exc), warn=True)
        return self.toast(f"{self._label(provider)} will use {chosen}.")

    def reset_cloud_model(self, provider: str) -> str:
        if not provider:
            return self.toast("Choose which service first.", warn=True)
        self.models().reset_cloud_model(provider)
        return self.toast(f"{self._label(provider)} is back to its default model.")

    @staticmethod
    def _label(provider: str) -> str:
        return next((e["label"] for e in CLOUD_CATALOGUE if e["name"] == provider), provider)

    # -- mail account ----------------------------------------------------------

    @staticmethod
    def mail_html() -> str:
        current = mailsvc.load_settings()
        if current is None:
            return '<div class="a-card-meta">Email is not connected yet, so ARTEMIS cannot send emails.</div>'
        return (
            '<div class="a-card-meta">Connected. ARTEMIS sends email as <strong>'
            f"{_esc(current.from_addr)}</strong>. "
            "Your password is stored safely by Windows.</div>"
        )

    @staticmethod
    def mail_hint(provider: str) -> str:
        guide = MAIL_GUIDE.get(provider or "")
        if not guide:
            return ""
        intro, steps = guide
        items = "".join(f"<li>{s}</li>" for s in steps)  # the steps are written here, not typed by a person
        return (
            '<div class="a-guide">'
            f'<div class="a-guide-head">How to connect {_esc(provider)}</div>'
            f'<div class="a-card-meta">{_esc(intro)}</div>'
            f"<ol>{items}</ol></div>"
        )

    def save_mail(self, provider, address, password, host, port, security) -> str:
        address = (address or "").strip()
        if not address:
            return self.toast("Type your email address first.", warn=True)
        try:
            address = mailsvc.validate_address(address)
        except mailsvc.MailError:
            return self.toast(
                "That does not look like an email address. It should look like you@gmail.com.",
                warn=True,
            )
        preset = MAIL_PRESETS.get(provider or "")
        if preset and preset[0]:
            host, port, security = preset[0], preset[1], preset[2]
        if not (host or "").strip():
            return self.toast(
                "Pick your email provider from the list. If yours is not there, choose Other and open Advanced.",
                warn=True,
            )
        if not password:
            return self.toast("Type your password first.", warn=True)
        try:
            mailsvc.save_settings(
                mailsvc.MailSettings(host.strip(), int(port or 0), address, address, security or "ssl"),
                password,
            )
        except (mailsvc.MailError, ValueError) as exc:
            return self.toast(str(exc), warn=True)
        return self.toast("Done. ARTEMIS can now send email from " + address + ". Your password is kept safely in Windows, not in a file.")

    def test_mail(self) -> str:
        """Log in with the saved account without sending anything."""
        current = mailsvc.load_settings()
        if current is None:
            return self.toast("Connect your email first.", warn=True)
        password = mailsvc.get_password(current.username)
        if not password:
            return self.toast("The password is missing. Connect your email again.", warn=True)
        try:
            mailsvc.test_connection(current, password)
        except mailsvc.MailError as exc:
            return self.toast(f"The test failed: {exc}.", warn=True)
        return self.toast("The test worked. ARTEMIS can log in to your email and send.")

    def forget_mail(self) -> str:
        mailsvc.forget_settings()
        return self.toast("Email disconnected.")

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
        """Point the one shared store at its new location.

        The same object is kept, because the assistant, gateway and panel all hold
        it; replacing it would leave them using the closed connection.
        """
        self._store.reopen()


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
    class _QuietRecordingFetch(logging.Filter):
        """The page sometimes re-fetches a recording just as it is deleted (by design,
        recordings are never kept). That is harmless, so do not print it as an error."""

        def filter(self, record: logging.LogRecord) -> bool:
            return "Response content shorter than Content-Length" not in record.getMessage() and not (
                record.exc_info and "shorter than Content-Length" in str(record.exc_info[1])
            )

    logging.getLogger("uvicorn.error").addFilter(_QuietRecordingFetch())
    voice = VoiceSession(audit=store.append_audit)
    voice.warm()  # load the voices in the background so the first hello is quick

    with gr.Blocks(title="ARTEMIS", fill_width=True) as page:
        refresh_on_open = gr.Button("refresh", elem_id="a-refresh", elem_classes=["a-hidden"])
        with gr.Row(equal_height=False):
            # -- the rail ---------------------------------------------------
            with gr.Column(scale=0, min_width=250):
                sidebar = gr.HTML(panel.sidebar_html("work"))
                new_chat_btn = gr.Button("+ New chat", variant="primary", size="sm")
                chat_list = gr.Radio(
                    label="Your chats (kept for 7 days)",
                    choices=assistant.chat_choices(),
                    value=None,
                    interactive=True,
                    elem_classes=["a-chats"],
                )
                delete_chat_btn = gr.Button("Delete this chat", size="sm")
                theme_btn = gr.Button("Switch light / dark", size="sm")

            # -- the work area ----------------------------------------------
            with gr.Column(scale=5):
                metrics = gr.HTML(panel.metrics_html())
                status = gr.HTML(elem_classes=["a-status-slot"])

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

                        with gr.Accordion("Talk instead of typing", open=True):
                            gr.HTML(
                                '<div class="a-sub">Voice starts on its own when ARTEMIS opens; untick the box to stop it. '
                                "While it is on, just talk and pause when you are done. "
                                "Your words appear in the box and are handled exactly like "
                                "typed words, so anything that changes something still asks "
                                "you first. The recording is deleted as soon as it has been "
                                "turned into words.</div>"
                            )
                            voice_on = gr.Checkbox(label="Voice is on (microphone allowed)", value=True, elem_id="a-voice-on")
                            autostart_btn = gr.Button("start voice", elem_id="a-autostart", elem_classes=["a-hidden"])
                            nudge_btn = gr.Button("nudge", elem_id="a-nudge", elem_classes=["a-hidden"])
                            read_aloud = gr.Checkbox(label="Read answers aloud", value=True)
                            mic = gr.Audio(
                                sources=["microphone"], type="filepath",
                                label="Microphone", interactive=False, elem_id="a-mic",
                            )
                            voice_note = gr.HTML(elem_id="a-voice-note")
                            voice_out = gr.Audio(
                                label="ARTEMIS speaking", autoplay=False, interactive=False,
                                elem_id="a-voice-out",
                            )

                        with gr.Row():
                            tidy_btn = gr.Button("Suggest a tidy-up")
                            resume_btn = gr.Button("What changed")
                            patterns_btn = gr.Button("Repeated tasks")
                            undo_btn = gr.Button("Undo last change")

                        conversation = gr.HTML()
                        clear_chat_btn = gr.Button("Clear conversation", size="sm")

                        # Above the card, not below it. Under a 14-step plan the
                        # buttons sat off the bottom of the window, and pinning
                        # them there does not work because Gradio's containers
                        # defeat position: sticky. Directly under the summary
                        # line they are always in view.
                        #
                        # Hidden until something is actually awaiting a
                        # decision. Buttons offering to confirm a plan that
                        # does not exist are the most confusing thing a page
                        # can show.
                        with gr.Row(elem_classes=["a-decision"]) as decision_row:
                            approve_btn = gr.Button("Approve", variant="primary", interactive=False)
                            remember_btn = gr.Button("Approve, don't ask again", interactive=False)
                            reject_btn = gr.Button("No, leave it", variant="stop", interactive=False)

                        approval_card = gr.HTML()

                        resume_card = gr.HTML()
                        with gr.Row():
                            note_box = gr.Textbox(
                                label="Leave a note for next time",
                                placeholder="Where I stopped, what to do next",
                                scale=6,
                            )
                            note_btn = gr.Button("Save note", scale=1)
                        with gr.Accordion("Habits and choices ARTEMIS remembers", open=False):
                            habit_pick = gr.Dropdown(label="A habit ARTEMIS noticed", choices=[], interactive=True)
                            with gr.Row():
                                habit_yes = gr.Button("Yes, that is a habit")
                                habit_no = gr.Button("No, stop mentioning it")
                            rule_pick = gr.Dropdown(label="Something you told ARTEMIS not to ask about", choices=[], interactive=True)
                            rule_btn = gr.Button("Ask me again before doing this")
                            habit_note = gr.HTML()

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
                        with gr.Row():
                            cloud_folder = gr.Dropdown(
                                label="Folder",
                                choices=panel.choices(),
                                interactive=True,
                                scale=4,
                            )
                            cloud_on_btn = gr.Button("Allow cloud models here", scale=2)
                            cloud_off_btn = gr.Button("Keep it on this computer", scale=2)

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
                        # Forgetting asks first. These buttons used to act on a
                        # single click, which a misplaced click could not undo.
                        with gr.Row(visible=False) as confirm_row:
                            confirm_text = gr.HTML()
                            confirm_yes = gr.Button("Yes, forget it", variant="stop")
                            confirm_no = gr.Button("Cancel")
                        pending_action = gr.State("")
                        files = gr.HTML(panel.files_html(None))
                        with gr.Row():
                            file_pick = gr.Dropdown(label="One file", choices=[], interactive=True, scale=4)
                            forget_file_btn = gr.Button("Forget this file", variant="stop", scale=1)
                        gr.HTML(
                            '<div class="a-card-meta">Erasing removes everything '
                            "ARTEMIS remembers about your folders. The activity "
                            "log is kept, so you can always check what ARTEMIS "
                            "did.</div>"
                        )
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
                        gr.HTML('<div class="a-h2" style="margin-top:6px">Local model</div>')
                        local_state = gr.HTML(panel.local_models_html())
                        with gr.Row():
                            local_pick = gr.Dropdown(
                                label="Use this local model",
                                choices=panel.local_model_choices(),
                                allow_custom_value=True,
                                scale=5,
                            )
                            local_save = gr.Button("Use it", scale=1)
                            local_auto = gr.Button("Choose for me", scale=1)
                            local_check = gr.Button("Check again", scale=1)
                        local_note = gr.HTML()
                        gr.HTML('<div class="a-h2" style="margin-top:18px">Cloud services</div>')
                        chat_cloud = gr.Checkbox(
                            label="Use cloud models for plain chat when no folder is chosen (what you type is sent to the cloud service)",
                            value=panel.chat_cloud(),
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
                        with gr.Row():
                            cloud_model_box = gr.Textbox(
                                label="Model name for the service chosen above",
                                placeholder="for example gpt-4.1-mini",
                                scale=6,
                            )
                            cloud_model_save = gr.Button("Use this model", scale=1)
                            cloud_model_reset = gr.Button("Default", scale=1)
                        cloud_note = gr.HTML()

                        gr.HTML(
                            '<div class="a-h1" style="margin-top:28px">Email</div>'
                            '<div class="a-sub">So ARTEMIS can send emails for you. It always shows you the '
                            "email first and only sends it if you say yes.</div>"
                        )
                        mail_state = gr.HTML(panel.mail_html())
                        mail_provider = gr.Dropdown(
                            label="Who provides your email?",
                            choices=list(MAIL_PRESETS),
                            value="Gmail",
                            interactive=True,
                        )
                        mail_hint = gr.HTML(panel.mail_hint("Gmail"))
                        with gr.Row():
                            mail_user = gr.Textbox(label="Your email address", placeholder="you@gmail.com", scale=4)
                            mail_pass = gr.Textbox(label="Your password", type="password", scale=4)
                        with gr.Accordion("Advanced: type the server details yourself", open=False):
                            with gr.Row():
                                mail_host = gr.Textbox(label="Outgoing mail server", placeholder="smtp.example.com", scale=4)
                                mail_port = gr.Number(label="Port", value=465, precision=0, scale=1)
                                mail_security = gr.Dropdown(label="Security", choices=["ssl", "starttls"], value="ssl", scale=1)
                        with gr.Row():
                            mail_save = gr.Button("Connect my email", variant="primary")
                            mail_test = gr.Button("Test connection")
                            mail_forget = gr.Button("Disconnect")
                        mail_note = gr.HTML()

                        # Optional: with the remote package deleted this section is just absent.
                        try:
                            from artemis.remote.screen import build_remote_section
                        except ImportError:
                            build_remote_section = None
                        if build_remote_section is not None:
                            build_remote_section(gr, store, lambda: AssistantPanel(store))

        # -- wiring. Each action returns the same four outputs so the page is
        # always re-read from the stores rather than patched in place.
        def refresh(
            message: str = "",
            workspace_id: int | None = None,
            select: int | None = None,
            clear: bool = False,
        ):
            def pick():
                if clear:
                    return gr.update(choices=panel.choices(), value=None)
                if select is not None:
                    return gr.update(choices=panel.choices(), value=select)
                return gr.update(choices=panel.choices())

            return (
                panel.cards_html(),
                panel.metrics_html(),
                pick(),
                message,
                panel.files_html(workspace_id),
                pick(),
                panel.sidebar_html("work"),
                pick(),
            )

        outputs = [
            cards, metrics, picker, status, files, work_picker, sidebar, cloud_folder
        ]

        def add_folder(folder):
            message = panel.add(folder)
            new_id = panel.last_added
            if new_id:
                assistant.index_in_background(new_id)
            # The new folder is chosen for the person: they added it in order to
            # use it, and an empty dropdown on the Work tab looked like nothing
            # had happened.
            return refresh(message, new_id, select=new_id)

        def set_cloud(ws, allow):
            if not ws:
                return refresh(panel.toast("Choose a folder first.", warn=True))
            panel.set_cloud_policy(ws, allow)
            assistant.refresh_models()
            name = panel.workspace_name(ws)
            return refresh(panel.toast(
                f"Cloud models are now allowed for {name}. Anything you ask there may be sent to the cloud service you set up."
                if allow else f"{name} stays on this computer. Cloud models will not be used for it."
            ))

        cloud_on_btn.click(lambda ws: set_cloud(ws, True), inputs=cloud_folder, outputs=outputs)
        cloud_off_btn.click(lambda ws: set_cloud(ws, False), inputs=cloud_folder, outputs=outputs)

        add_btn.click(add_folder, inputs=folder_box, outputs=outputs).then(
            lambda: "", outputs=folder_box
        )

        browse_btn.click(_browse, outputs=folder_box)

        show_btn.click(
            lambda ws: refresh("", ws), inputs=picker, outputs=outputs
        )
        rescan_btn.click(
            lambda ws: refresh(panel.rescan(ws), ws), inputs=picker, outputs=outputs
        )
        def ask_to_forget(ws):
            if not ws:
                return (
                    gr.update(visible=False), "", "",
                    panel.toast("Choose a folder first.", warn=True),
                )
            name = panel.workspace_name(ws)
            text = (
                f'<div class="a-msg warn">Forget \u201c{_esc(name)}\u201d? ARTEMIS will '
                "stop knowing about this folder. Your files in it are not touched.</div>"
            )
            return gr.update(visible=True), text, "forget", ""

        def ask_to_erase():
            count = len(panel.workspaces())
            if not count:
                return (
                    gr.update(visible=False), "", "",
                    panel.toast("There is nothing to forget.", warn=True),
                )
            text = (
                f'<div class="a-msg warn">Forget all {_plural(count, "folder")}? '
                "None of your files are touched. The activity log is kept.</div>"
            )
            return gr.update(visible=True), text, "erase", ""

        def confirmed(action, ws):
            chats = (gr.update(), gr.update())
            if action == "forget":
                message = panel.forget_workspace(ws)
            elif action == "erase":
                message = panel.forget_everything()
                # the saved chats were erased too, so the list and the open chat must go
                chats = (assistant.new_chat(), gr.update(choices=assistant.chat_choices(), value=None))
            else:
                return (*refresh(""), gr.update(visible=False), "", *chats)
            return (*refresh(message, clear=True), gr.update(visible=False), "", *chats)

        def cancelled():
            return (
                gr.update(visible=False), "",
                panel.toast("Left as it was. Nothing was forgotten."),
            )

        forget_btn.click(
            ask_to_forget, inputs=picker,
            outputs=[confirm_row, confirm_text, pending_action, status],
        )
        erase_btn.click(
            ask_to_erase,
            outputs=[confirm_row, confirm_text, pending_action, status],
        )
        confirm_yes.click(
            confirmed, inputs=[pending_action, picker],
            outputs=[*outputs, confirm_row, pending_action, conversation, chat_list],
        )
        confirm_no.click(cancelled, outputs=[confirm_row, pending_action, status])

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

        def refresh_after_change(message_html: str, card_html: str, ws, said=None):
            """Log the reply into the conversation and return everything to redraw."""
            return (
                assistant.log_turn(said, message_html),
                card_html,
                panel.cards_html(),
                panel.metrics_html(),
                assistant.resume_html(ws),
                panel.sidebar_html("work"),
                gr.update(choices=assistant.chat_choices(), value=assistant.state.session_id),
            )

        assistant_outputs = [
            conversation, approval_card, cards, metrics, resume_card, sidebar, chat_list,
        ]

        # The Approve and No buttons are shown from what is actually waiting,
        # read once the answer has finished. A flag carried inside a streamed
        # answer was dropped by the page, which left a card asking "Approve
        # these changes?" with nothing to press.
        decision_buttons = [approve_btn, remember_btn, reject_btn]

        def sync_decision():
            # The three buttons are always on the page and are switched on only
            # while something is waiting. Showing and hiding the row was what made
            # them disappear: a card asking "Approve these changes?" with nothing to
            # press.
            on = assistant.has_pending
            return (
                gr.update(interactive=on),
                gr.update(interactive=on and assistant.can_remember),
                gr.update(interactive=on),
            )

        def ask_progressively(ws, text):
            """Stream the turn into the conversation as it is worked on."""
            said = (text or "").strip()
            last = None
            for message_html, card_html in assistant.ask_streaming(ws, text):
                last = (message_html, card_html)
                if "a-thinking" in message_html or "a-streaming" in message_html:
                    yield (
                        assistant.preview_turn(said, message_html), "",
                        gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(),
                    )
                else:
                    yield refresh_after_change(message_html, card_html, ws, said)
            if last is None:
                yield refresh_after_change("", "", ws, said)

        # -- voice: another way to type, with no gates of its own --------------
        def set_voice(on):
            """Switching voice on starts the conversation: ARTEMIS greets you out loud."""
            if not on:
                voice.disarm()
                assistant.set_spoken(False)
                return (
                    gr.update(interactive=False, value=None),
                    '<div class="a-msg">Voice is off. Nothing is recorded.</div>',
                    gr.skip(), None,
                )
            voice.arm()
            assistant.set_spoken(True)
            hello = greeting(resuming=bool(assistant.state.transcript))
            conversation_html = assistant.log_turn(None, assistant._say(hello))
            try:
                clip = str(voice.speak(hello) or "") or None
            except SpeechUnavailable:
                clip = None
            return (
                gr.update(interactive=True, value=None),
                '<div class="a-msg">Voice is on. Just talk; I listen when I am not speaking.</div>',
                conversation_html, clip,
            )

        autostart_btn.click(lambda: set_voice(True), outputs=[mic, voice_note, conversation, voice_out])
        voice_on.change(set_voice, inputs=voice_on, outputs=[mic, voice_note, conversation, voice_out])
        read_aloud.change(lambda on: voice.set_read_aloud(on), inputs=read_aloud)

        def hear_voice(clip):
            """Words from the recording go into the same box typing uses."""
            try:
                turn = voice.hear(clip)
            except NotArmed:
                return gr.skip(), '<div class="a-msg warn">Voice is off, so that was ignored.</div>', False, None
            except SpeechUnavailable as exc:
                return gr.skip(), f'<div class="a-msg warn">{html.escape(str(exc))}</div>', False, None
            if turn is None:
                return gr.skip(), gr.skip(), False, None  # silence: nothing to say about it
            return turn.text, f'<div class="a-msg">Heard: {html.escape(turn.text)}</div>', True, None

        voice_flag = gr.State(False)

        def ask_if_voice(ws, text, ok):
            """A spoken turn shows its words and plays its voice at the same moment.

            While the answer is being worked out only "Working on it" is shown; the words
            and the sound arrive together, so the voice is never behind the text.
            """
            if not ok:
                yield (gr.skip(),) * 8
                return
            held = None
            shown_working = False
            for out in ask_progressively(ws, text):
                if isinstance(out[2], dict):  # a preview while it is still being worked on
                    if not shown_working and "a-thinking" in str(out[0]):
                        shown_working = True
                        yield (*out, gr.skip())
                    continue
                held = out
            if held is None:
                yield (gr.skip(),) * 8
                return
            try:
                clip = str(voice.speak(assistant.last_reply_text()) or "") or None
            except SpeechUnavailable:
                clip = None
            yield (*held, clip)

        def nudge():
            """Nobody spoke for a few seconds, so ARTEMIS says something first."""
            if not voice.armed:
                return gr.skip(), gr.skip()
            line = "Hello? Is there anything I can help you with?"
            shown = assistant.log_turn(None, assistant._say(line))
            try:
                clip = str(voice.speak(line) or "") or None
            except SpeechUnavailable:
                clip = None
            return shown, clip

        nudge_btn.click(nudge, outputs=[conversation, voice_out])

        mic.stop_recording(
            hear_voice, inputs=mic, outputs=[ask_box, voice_note, voice_flag, mic]
        ).then(
            ask_if_voice, inputs=[work_picker, ask_box, voice_flag],
            outputs=assistant_outputs + [voice_out],
        ).then(sync_decision, outputs=decision_buttons).then(
            lambda: "", outputs=ask_box
        ).then(lambda: None, outputs=mic)  # clear the clip

        ask_btn.click(
            ask_progressively,
            inputs=[work_picker, ask_box],
            outputs=assistant_outputs,
        ).then(sync_decision, outputs=decision_buttons).then(lambda: "", outputs=ask_box)

        ask_box.submit(
            ask_progressively,
            inputs=[work_picker, ask_box],
            outputs=assistant_outputs,
        ).then(sync_decision, outputs=decision_buttons).then(lambda: "", outputs=ask_box)

        tidy_btn.click(
            lambda ws: refresh_after_change(*assistant.suggest_tidy(ws), ws, "Suggest a tidy-up"),
            inputs=work_picker,
            outputs=assistant_outputs,
        ).then(sync_decision, outputs=decision_buttons)

        approve_btn.click(
            lambda ws: refresh_after_change(*assistant.approve(remember=False), ws, "Approve"),
            inputs=work_picker,
            outputs=assistant_outputs,
        ).then(sync_decision, outputs=decision_buttons)

        remember_btn.click(
            lambda ws: refresh_after_change(*assistant.approve(remember=True), ws, "Approve, don't ask again"),
            inputs=work_picker,
            outputs=assistant_outputs,
        ).then(sync_decision, outputs=decision_buttons)

        reject_btn.click(
            lambda ws: refresh_after_change(*assistant.reject(), ws, "No, leave it"),
            inputs=work_picker,
            outputs=assistant_outputs,
        ).then(sync_decision, outputs=decision_buttons)

        undo_btn.click(
            lambda ws: refresh_after_change(assistant.undo_last(), "", ws, "Undo last change"),
            inputs=work_picker,
            outputs=assistant_outputs,
        ).then(sync_decision, outputs=decision_buttons)

        def start_new_chat():
            return assistant.new_chat(), gr.update(choices=assistant.chat_choices(), value=None)

        clear_chat_btn.click(start_new_chat, outputs=[conversation, chat_list])
        new_chat_btn.click(start_new_chat, outputs=[conversation, chat_list])
        # .input fires only when the person picks one, not when the list is redrawn
        chat_list.input(lambda sid: assistant.open_chat(sid), inputs=chat_list, outputs=conversation)

        def delete_this_chat():
            assistant.delete_chat()
            return "", gr.update(choices=assistant.chat_choices(), value=None)

        delete_chat_btn.click(delete_this_chat, outputs=[conversation, chat_list])

        resume_btn.click(
            lambda ws: refresh_after_change(*assistant.answer_what_changed(ws), ws, "What changed"),
            inputs=work_picker,
            outputs=assistant_outputs,
        )

        def habits_ui(ws):
            return (
                gr.update(choices=assistant.habit_choices(ws), value=None),
                gr.update(choices=assistant.remembered_rules(ws), value=None),
            )

        patterns_btn.click(
            lambda ws: (
                assistant.log_turn("Repeated tasks", assistant.look_for_patterns(ws)),
                assistant.patterns_html(ws),
                *habits_ui(ws),
            ),
            inputs=work_picker,
            outputs=[conversation, resume_card, habit_pick, rule_pick],
        )

        note_btn.click(
            lambda ws, n: (assistant.save_note(ws, n), assistant.resume_html(ws), ""),
            inputs=[work_picker, note_box],
            outputs=[habit_note, resume_card, note_box],
        )
        habit_yes.click(
            lambda ws, r: (panel.toast(assistant.decide_habit(ws, r, True)), *habits_ui(ws)),
            inputs=[work_picker, habit_pick], outputs=[habit_note, habit_pick, rule_pick],
        )
        habit_no.click(
            lambda ws, r: (panel.toast(assistant.decide_habit(ws, r, False)), *habits_ui(ws)),
            inputs=[work_picker, habit_pick], outputs=[habit_note, habit_pick, rule_pick],
        )
        rule_btn.click(
            lambda ws, r: (panel.toast(assistant.revoke_rule(r)), *habits_ui(ws)),
            inputs=[work_picker, rule_pick], outputs=[habit_note, habit_pick, rule_pick],
        )

        def forget_one(ws, rel):
            if not ws or not rel:
                return panel.toast("Choose a file first.", warn=True), panel.files_html(ws), gr.update()
            DisclosurePanel(store).forget_file(ws, rel)
            return (
                panel.toast(f"ARTEMIS has forgotten {rel}. The file itself was not touched."),
                panel.files_html(ws),
                gr.update(choices=[r["rel_path"] for r in store.list_files(ws)], value=None),
            )

        forget_file_btn.click(forget_one, inputs=[picker, file_pick], outputs=[status, files, file_pick])
        show_btn.click(
            lambda ws: gr.update(choices=[r["rel_path"] for r in store.list_files(ws)] if ws else []),
            inputs=picker, outputs=file_pick,
        )

        # -- models and mail
        def models_changed(note):
            assistant.refresh_models()
            return note, panel.local_models_html(), panel.cloud_html(), gr.update(choices=panel.local_model_choices())

        local_outs = [local_note, local_state, cloud_state, local_pick]
        local_save.click(lambda n: models_changed(panel.set_local_model(n)), inputs=local_pick, outputs=local_outs)
        local_auto.click(lambda: models_changed(panel.reset_local_model()), outputs=local_outs)
        local_check.click(lambda: models_changed(""), outputs=local_outs)
        cloud_model_save.click(
            lambda p, n: models_changed(panel.set_cloud_model(p, n)),
            inputs=[cloud_pick, cloud_model_box], outputs=[cloud_note, local_state, cloud_state, local_pick],
        )
        cloud_model_reset.click(
            lambda p: models_changed(panel.reset_cloud_model(p)),
            inputs=[cloud_pick], outputs=[cloud_note, local_state, cloud_state, local_pick],
        )

        mail_save.click(
            lambda pr, u, pw, h, pt, s: (panel.save_mail(pr, u, pw, h, pt, s), panel.mail_html(), ""),
            inputs=[mail_provider, mail_user, mail_pass, mail_host, mail_port, mail_security],
            outputs=[mail_note, mail_state, mail_pass],
        )
        mail_provider.change(lambda pr: panel.mail_hint(pr), inputs=mail_provider, outputs=mail_hint)
        def chat_cloud_changed(on):
            note = panel.set_chat_cloud(bool(on))
            assistant.refresh_models()
            return note

        chat_cloud.change(chat_cloud_changed, inputs=chat_cloud, outputs=cloud_note)
        mail_test.click(lambda: panel.test_mail(), outputs=mail_note)
        mail_forget.click(lambda: (panel.forget_mail(), panel.mail_html()), outputs=[mail_note, mail_state])


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
            assistant.refresh_models()
            return panel.cloud_html(), _say_html(message), ""

        def _forget_key(provider):
            message = panel.forget_cloud_key(provider)
            assistant.refresh_models()
            return panel.cloud_html(), _say_html(message), ""

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

        # The page was built once, when the server started, so a browser refresh
        # used to show that moment: no folders, an empty dropdown, "ARTEMIS
        # cannot see anything", while the data was all still there. Reading the
        # stores again on every page load makes the page match what is held.
        def _pick(first):
            # Only set a value when there is one. Assigning None to an empty
            # dropdown as the page loads was one of the things that made this
            # version of Gradio spin.
            if first:
                return gr.update(choices=panel.choices(), value=first)
            return gr.update(choices=panel.choices())

        def on_load():
            first = panel.first_workspace_id()
            return (
                panel.cards_html(),
                panel.metrics_html(),
                _pick(first),
                panel.files_html(first),
                _pick(first),
                panel.sidebar_html("work"),
                assistant.resume_html(first),
                panel.cloud_html(),
                _location_html(panel.store_location()),
                # A first-time person lands on Work with nothing to work on.
                # Say what to do rather than leave an empty dropdown. (Switching
                # the tab for them from here makes this version of Gradio loop
                # forever, so the message does the job instead.)
                assistant.transcript_html() or ("" if first else assistant.welcome_html()),
                # Read from disk each time, so a reload shows the account that
                # is really saved instead of the state from when the server began.
                panel.mail_html(),
                panel.local_models_html(),
                gr.update(choices=assistant.chat_choices(), value=assistant.state.session_id),
                assistant.pending_card_html(),
                *sync_decision(),
            )

        # Gradio 6.12 freezes the whole page when a tab is clicked if the page
        # has any load event (reproduced with a one-line load handler on the
        # previous version of this interface). So the refresh is an ordinary
        # click on a hidden button, pressed once by LOAD_JS when the page opens.
        theme_btn.click(None, js="() => { window.artemisToggleTheme(); }")

        refresh_on_open.click(
            on_load,
            outputs=[
                cards, metrics, picker, files, work_picker, sidebar, resume_card,
                cloud_state, location, conversation, mail_state, local_state, chat_list,
                approval_card, *decision_buttons,
            ],
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
            head=LOAD_HEAD,
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
