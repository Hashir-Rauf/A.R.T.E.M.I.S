"""
Generate all architecture diagrams for the ARTEMIS Architecture document.

Every figure is emitted as a vector PDF into this directory, named fig_*.pdf,
so LaTeX can include them at any scale without raster artefacts.

Run from the Tex/Architecture directory:
    python figures/gen_figures.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

# ---------------------------------------------------------------------------
# House style, matched to preamble.sty
# ---------------------------------------------------------------------------

INK = "#1B1B1B"
BLUE = "#356FB0"
RULE = "#9AB2CC"
BG = "#EEF3F8"
WHITE = "#FFFFFF"
GREY = "#6B7280"
LIGHTGREY = "#F4F5F7"

# Risk-tier palette. Kept distinct from the corporate blue so tiers read as
# a separate semantic axis rather than as emphasis.
T0 = "#0E7490"
T1 = "#B45309"
T2 = "#BE123C"
T3 = "#4B5563"
T0BG = "#E6F2F5"
T1BG = "#FBEEDD"
T2BG = "#FBE9ED"
T3BG = "#EDEEF0"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "text.color": INK,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    }
)

OUT = os.path.dirname(os.path.abspath(__file__))


# Data units per typographic point. 100 data units span `w` inches and there
# are 72 points to the inch, so this conversion is exact for a given canvas.
# Text can therefore be positioned in real font units rather than in fractions
# of a container, which is what keeps multi-line labels from colliding.
_PT = {"scale": 100.0 / (72.0 * 7.0)}


def pt(n: float) -> float:
    """Convert `n` typographic points into data units on the current canvas."""
    return n * _PT["scale"]


def text_block_height(n_lines: int, fs: float, linespacing: float = 1.45) -> float:
    """Height in data units of an `n_lines` block set at `fs` points."""
    if n_lines <= 0:
        return 0.0
    return pt(fs * (1 + (n_lines - 1) * linespacing))


def new_canvas(w: float, h: float):
    """A blank axes in data units 0..100 wide, 0..(100*h/w) tall."""
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100 * h / w)
    ax.axis("off")
    ax.set_aspect("equal")
    _PT["scale"] = 100.0 / (72.0 * w)
    return fig, ax


def save(fig, name: str):
    path = os.path.join(OUT, name)
    fig.savefig(path, format="pdf", transparent=True)
    plt.close(fig)
    print("  wrote", name)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def top(self) -> tuple[float, float]:
        return (self.cx, self.y + self.h)

    @property
    def bottom(self) -> tuple[float, float]:
        return (self.cx, self.y)

    @property
    def left(self) -> tuple[float, float]:
        return (self.x, self.cy)

    @property
    def right(self) -> tuple[float, float]:
        return (self.x + self.w, self.cy)


def box(
    ax,
    x,
    y,
    w,
    h,
    label,
    *,
    sub=None,
    fc=WHITE,
    ec=RULE,
    lw=0.9,
    fs=8.0,
    subfs=6.6,
    bold=False,
    tc=INK,
    subtc=GREY,
    radius=0.6,
    ls="solid",
    align="center",
    pad=1.4,
    grow=True,
) -> Box:
    """A rounded box whose text is laid out in real typographic units.

    The title and the optional sub-label are measured as one block and centred
    together, so a tall box never lets the two collide and a short box grows to
    fit rather than overflowing. Set `grow=False` to pin the height exactly.
    """
    lab_lines = label.count("\n") + 1 if label else 0
    sub_lines = sub.count("\n") + 1 if sub else 0

    lab_h = text_block_height(lab_lines, fs)
    sub_h = text_block_height(sub_lines, subfs)
    gap = pt(fs * 0.55) if (lab_lines and sub_lines) else 0.0
    block_h = lab_h + gap + sub_h

    if grow:
        h = max(h, block_h + 2 * pad)

    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        linestyle=ls,
        zorder=2,
    )
    ax.add_patch(patch)
    b = Box(x, y, w, h)

    # Lay the block out from its top edge downward, so every line lands at a
    # known offset and nothing depends on the box's height.
    top = b.cy + block_h / 2

    if lab_lines:
        ha = {"center": "center", "left": "left"}[align]
        tx = b.cx if align == "center" else x + pad + 0.2
        ax.text(
            tx,
            top - lab_h / 2,
            label,
            ha=ha,
            va="center",
            fontsize=fs,
            color=tc,
            fontweight="bold" if bold else "normal",
            linespacing=1.45,
            zorder=3,
        )

    if sub_lines:
        ax.text(
            b.cx,
            top - lab_h - gap - sub_h / 2,
            sub,
            ha="center",
            va="center",
            fontsize=subfs,
            color=subtc,
            linespacing=1.45,
            zorder=3,
        )
    return b


def band(ax, x, y, w, h, label, *, fc=BG, ec=RULE, lw=0.9, fs=7.4, ls="solid"):
    """A wide labelled container band (used for layers and planes)."""
    ax.add_patch(
        Rectangle(
            (x, y),
            w,
            h,
            facecolor=fc,
            edgecolor=ec,
            linewidth=lw,
            linestyle=ls,
            zorder=0 if fc == "none" else 1,
        )
    )
    if label:
        ax.text(
            x + 1.4,
            y + h - 1.5,
            label,
            ha="left",
            va="top",
            fontsize=fs,
            color=BLUE,
            fontweight="bold",
            zorder=3,
        )


def arrow(ax, p0, p1, *, color=INK, lw=0.9, ls="solid", shrink=1.5, head=6.0, z=4):
    ax.add_patch(
        FancyArrowPatch(
            p0,
            p1,
            arrowstyle=f"-|>,head_width={head/22:.3f},head_length={head/13:.3f}",
            mutation_scale=10,
            color=color,
            linewidth=lw,
            linestyle=ls,
            shrinkA=shrink,
            shrinkB=shrink,
            zorder=z,
        )
    )


def elbow(ax, p0, p1, *, via_y=None, via_x=None, **kw):
    """An orthogonal two-segment connector."""
    x0, y0 = p0
    x1, y1 = p1
    if via_y is not None:
        ax.plot([x0, x0], [y0, via_y], color=kw.get("color", INK),
                lw=kw.get("lw", 0.9), zorder=3, solid_capstyle="round")
        ax.plot([x0, x1], [via_y, via_y], color=kw.get("color", INK),
                lw=kw.get("lw", 0.9), zorder=3, solid_capstyle="round")
        arrow(ax, (x1, via_y), (x1, y1), **kw)
    elif via_x is not None:
        ax.plot([x0, via_x], [y0, y0], color=kw.get("color", INK),
                lw=kw.get("lw", 0.9), zorder=3, solid_capstyle="round")
        ax.plot([via_x, via_x], [y0, y1], color=kw.get("color", INK),
                lw=kw.get("lw", 0.9), zorder=3, solid_capstyle="round")
        arrow(ax, (via_x, y1), (x1, y1), **kw)


def caption_note(ax, x, y, text, *, fs=6.6, color=GREY, ha="left", style="italic"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fs, color=color,
            fontstyle=style, zorder=4, linespacing=1.5)



def panel(ax, x, y, w, title, *, body_h, ec=BLUE, header_fc=BG, body_fc=WHITE,
          fs=8.0, lw=1.2, pad=1.2):
    """A header strip above a body area. Returns (body_box, header_bottom_y).

    The header is sized from its own text, so the body area below it always
    starts clear of the title regardless of font size.
    """
    head_h = text_block_height(title.count("\n") + 1, fs) + 2 * pad
    total = head_h + body_h
    ax.add_patch(Rectangle((x, y), w, total, facecolor=body_fc, edgecolor=ec,
                           linewidth=lw, zorder=2))
    ax.add_patch(Rectangle((x, y + body_h), w, head_h, facecolor=header_fc,
                           edgecolor=ec, linewidth=lw, zorder=2))
    ax.text(x + w / 2, y + body_h + head_h / 2, title, ha="center",
            va="center", fontsize=fs, color=ec, fontweight="bold", zorder=3)
    return Box(x, y, w, body_h), y + body_h


def col_list(ax, x, top, title, items, *, tc, fs=6.8, itemfs=6.3,
             linespacing=1.55):
    """A bold column heading with a list beneath it, stacked in real units."""
    ax.text(x, top - text_block_height(1, fs) / 2, title, ha="left",
            va="center", fontsize=fs, color=tc, fontweight="bold", zorder=3)
    body_top = top - text_block_height(1, fs) - pt(fs * 0.6)
    n = len(items)
    bh = text_block_height(n, itemfs, linespacing)
    ax.text(x, body_top - bh / 2, "\n".join(items), ha="left", va="center",
            fontsize=itemfs, color=INK, linespacing=linespacing, zorder=3)
    return body_top - bh



def boxtop(ax, x, top, w, label, *, min_h=0.0, **kw):
    """Like box(), but anchored by its top edge and grown downward to fit.

    Chaining boxes vertically is then just `top = b.y - gap`, with no need to
    predict how tall the text will make each one.
    """
    lab_lines = label.count("\n") + 1 if label else 0
    sub = kw.get("sub")
    sub_lines = sub.count("\n") + 1 if sub else 0
    fs = kw.get("fs", 8.0)
    subfs = kw.get("subfs", 6.6)
    pad = kw.get("pad", 1.4)
    gap = pt(fs * 0.55) if (lab_lines and sub_lines) else 0.0
    need = (text_block_height(lab_lines, fs) + gap
            + text_block_height(sub_lines, subfs) + 2 * pad)
    h = max(min_h, need)
    return box(ax, x, top - h, w, h, label, **kw)


# ===========================================================================
# Fig 1: Layered overview
# ===========================================================================


def fig_layers():
    fig, ax = new_canvas(7.4, 8.2)
    H = ax.get_ylim()[1]

    x0, w = 4.0, 92.0
    GAP = 2.8
    TITLE_FS = 7.4

    def layer(i, title, top, rows_h):
        """A layer band sized from its title plus the height its rows need.

        Returns the y at which row content may start, which is always clear of
        the band's title.
        """
        head = text_block_height(1, TITLE_FS) + 2.4
        h = head + rows_h + 2.0
        band(ax, x0, top - h, w, h, f"LAYER {i}  {title}", fc=WHITE, ec=RULE,
             fs=TITLE_FS)
        return Box(x0, top - h, w, h), top - head

    top = H - 8.4

    # ---- Layer 1
    l1, c1 = layer(1, "PRESENTATION", top, 13.6)
    bw = 24.0
    cli = boxtop(ax, x0 + 4, c1, bw, "CLI (Typer)", fs=7.2, fc=LIGHTGREY,
                 min_h=4.8)
    gui = boxtop(ax, x0 + 34, c1, bw, "Local GUI (Gradio)", fs=7.2,
                 fc=LIGHTGREY, min_h=4.8)
    pwa = boxtop(ax, x0 + 64, c1, bw, "Remote PWA", fs=7.2, fc=LIGHTGREY,
                 ec=RULE, ls="dashed", min_h=4.8)
    cp = boxtop(ax, x0 + 8, cli.y - 2.6, w - 16,
                "ARTEMIS CONTROL PANEL   \u00b7   one shared view model",
                sub="Chat  \u00b7  Monitor  \u00b7  Configure  \u00b7  "
                    "Approve / Reject  \u00b7  Undo  \u00b7  What I Know",
                fs=7.4, subfs=6.3, bold=True, fc=BG, ec=BLUE)
    for b in (cli, gui, pwa):
        arrow(ax, b.bottom, (b.cx, cp.y + cp.h), lw=0.8)

    # ---- Layer 2
    l2, c2 = layer(2, "INTERACTION AND SESSION", l1.y - GAP, 14.2)
    vs = boxtop(ax, x0 + 6, c2, 38, "Voice Session Manager",
                sub="VAD  \u00b7  STT  \u00b7  barge-in  \u00b7  TTS",
                fs=7.2, subfs=6.2, fc=LIGHTGREY)
    ts = boxtop(ax, x0 + 50, c2, 38, "Text Stream Manager",
                sub="tokens  \u00b7  partials  \u00b7  cancel", fs=7.2,
                subfs=6.2, fc=LIGHTGREY)
    tn = boxtop(ax, x0 + 14, vs.y - 2.6, w - 28, "TURN NORMALISER",
                sub="modality-neutral Turn object", fs=7.4, subfs=6.3,
                bold=True, fc=BG, ec=BLUE)
    for b in (vs, ts):
        arrow(ax, b.bottom, (b.cx, tn.y + tn.h), lw=0.8)

    # ---- Layer 3
    l3, c3 = layer(3, "AI GATEWAY   (orchestrator, not a monolith)",
                   l2.y - GAP, 15.0)
    cw = 20.0
    names = ["Model\nRouter", "Context\nEngine", "Policy\nEngine",
             "Agent\nPlanner"]
    gxs = [x0 + 4 + i * (cw + 2.4) for i in range(4)]
    gb = [boxtop(ax, gx, c3, cw, n, fs=7.2, fc=LIGHTGREY, ec=RULE, min_h=6.2)
          for gx, n in zip(gxs, names)]
    td = boxtop(ax, x0 + 22, gb[0].y - 3.0, w - 44, "TOOL DISPATCHER",
                sub="the single execution chokepoint", fs=7.4, subfs=6.3,
                bold=True, fc=BG, ec=BLUE)
    for b in gb:
        elbow(ax, b.bottom, (td.cx + (b.cx - 50) * 0.30, td.y + td.h),
              via_y=gb[0].y - 1.5, lw=0.75)

    # ---- Layer 4
    l4, c4 = layer(4, "CAPABILITY SERVICES   (the nine features)",
                   l3.y - GAP, 13.4)
    svc = ["Session Resume", "Folder Tidy", "Notes Synthesis",
           "Pattern Watcher", "Code Assistant", "Web Search", "Mail Composer",
           "Document Drafter"]
    sw = (w - 10) / 4 - 1.6
    rowy = c4
    for i, sname in enumerate(svc):
        r, c = divmod(i, 4)
        if c == 0 and r == 1:
            rowy = rowy - 4.0
        boxtop(ax, x0 + 5 + c * (sw + 1.6), rowy, sw, sname, fs=6.5,
               fc=LIGHTGREY, min_h=3.6)
    boxtop(ax, x0 + 5, rowy - 4.4, w - 10,
           "Support:  Workspace Broker   \u00b7   Indexer   \u00b7   "
           "Undo Journal   \u00b7   Approval Broker",
           fs=6.8, fc=BG, ec=BLUE, min_h=3.4)

    # ---- Layer 5
    l5, c5 = layer(5, "DATA PLANE   (local only, never uploaded)",
                   l4.y - GAP, 9.2)
    stores = ["SQLite\nmetadata, sessions,\nrules, audit",
              "Vector Index\nper workspace",
              "Key-Value\nMemory Store",
              "Snapshot Store\nundo blobs",
              "Credential Vault\nOS keyring"]
    dw = (w - 10) / 5 - 1.4
    for i, st in enumerate(stores):
        boxtop(ax, x0 + 5 + i * (dw + 1.4), c5, dw, st, fs=6.3, fc=LIGHTGREY,
               min_h=8.2)

    # ---- Inter-layer arrows
    for a, bnd in ((l1, l2), (l2, l3), (l3, l4), (l4, l5)):
        arrow(ax, (50, a.y), (50, bnd.y + bnd.h), lw=1.0, color=BLUE)

    # ---- Enclosing planes, drawn from the stack's measured extent so they
    # always frame it exactly, whatever the layers' contents.
    plane_bot = l5.y - 5.6
    band(ax, 0.5, plane_bot, 99, (H - 7.4) - plane_bot, "", fc="none",
         ec=BLUE, lw=1.3)
    ax.text(50, H - 2.6, "SECURITY / TRUST PLANE", ha="center", va="center",
            fontsize=8.4, color=BLUE, fontweight="bold", zorder=5)
    ax.text(50, H - 5.2, "cross-cutting: every arrow below crosses this plane",
            ha="center", va="center", fontsize=6.5, color=GREY,
            fontstyle="italic", zorder=5)
    ax.text(50, plane_bot + 2.6, "EXECUTION / PERFORMANCE PLANE",
            ha="center", va="center", fontsize=8.4, color=BLUE,
            fontweight="bold", zorder=5)

    ax.text(50, plane_bot - 3.4,
            "LAYER 6  \u00b7  REMOTE ACCESS PLANE is drawn separately,\n"
            "because nothing in Layers 1 to 5 depends on it.",
            ha="center", va="center", fontsize=6.8, color=GREY,
            fontstyle="italic", linespacing=1.6)

    save(fig, "fig_layers.pdf")


# ===========================================================================
# Fig 2: Request lifecycle
# ===========================================================================


def fig_lifecycle():
    fig, ax = new_canvas(7.2, 4.4)
    H = ax.get_ylim()[1]

    bw = 33.0
    lx, rx = 4.0, 56.0
    GAP = 3.0
    # The branch connector runs in the channel between the columns, so it
    # never crosses a box.
    chan = lx + bw + 5.5

    ax.text(lx + bw / 2, H - 2.2, "Input   (voice  |  text  |  remote)",
            ha="center", va="center", fontsize=7.6, color=BLUE,
            fontweight="bold")

    left = [
        ("Turn Normaliser", "modality erased here"),
        ("Context Engine", "retrieve within workspace bounds only"),
        ("Model Router", "choose tier, enforce egress policy"),
        ("Agent Planner", "produce an explicit, inspectable Plan"),
        ("Policy Engine", "classify every proposed ToolCall"),
    ]
    top = H - 4.4
    prev = None
    for name, sub in left:
        b = boxtop(ax, lx, top, bw, name, sub=sub, fs=7.4, subfs=6.1,
                   fc=WHITE, ec=RULE, min_h=6.4)
        arrow(ax, (b.cx, H - 3.4) if prev is None else prev.bottom, b.top,
              lw=0.9)
        prev = b
        top = b.y - GAP

    dec = boxtop(ax, lx + 4, top, bw - 8, "risk tier?", fs=7.6, fc=BG,
                 ec=BLUE, bold=True, min_h=5.0)
    arrow(ax, prev.bottom, dec.top, lw=0.9)

    # ---- Right column: approval branch, then the execution tail.
    rtop = H - 4.4
    appr = boxtop(ax, rx, rtop, bw, "Approval Broker",
                  sub="preview and diff", fs=7.4, subfs=6.1, fc=T1BG, ec=T1,
                  min_h=6.4)
    user = boxtop(ax, rx, appr.y - GAP, bw, "USER DECIDES",
                  sub="approve  \u00b7  edit  \u00b7  reject", fs=7.4,
                  subfs=6.1, fc=WHITE, ec=T1, bold=True, min_h=6.2)
    arrow(ax, appr.bottom, user.top, lw=0.9, color=T1)

    # Gated: out of the decision, up the channel, into the broker.
    ax.plot([dec.x + dec.w, chan], [dec.cy, dec.cy], color=T1, lw=0.9,
            zorder=3, solid_capstyle="round")
    ax.plot([chan, chan], [dec.cy, appr.cy], color=T1, lw=0.9, zorder=3,
            solid_capstyle="round")
    arrow(ax, (chan, appr.cy), appr.left, lw=0.9, color=T1)
    caption_note(ax, dec.x + dec.w + 1.0, dec.cy + 2.0, "gated", color=T1,
                 style="normal")
    caption_note(ax, rx + bw + 1.2, user.cy,
                 "rejected:\nrecord, explain,\nplan halts", color=GREY)

    tail = [
        ("Undo Journal", "snapshot BEFORE mutation", T1BG, T1),
        ("Tool Dispatcher", "the only component that may act", WHITE, RULE),
        ("Capability Service", "all I/O via the Workspace Broker", WHITE, RULE),
        ("Audit Log", "append-only, hash-chained", WHITE, RULE),
    ]
    top = user.y - GAP * 1.7
    prev = user
    for i, (name, sub, fcc, ecc) in enumerate(tail):
        b = boxtop(ax, rx, top, bw, name, sub=sub, fs=7.4, subfs=6.1,
                   fc=fcc, ec=ecc, min_h=6.4)
        arrow(ax, prev.bottom, b.top, lw=0.9, color=T1 if i == 0 else INK)
        if i == 0:
            caption_note(ax, b.cx + 1.6, (prev.y + b.y + b.h) / 2, "approved",
                         color=T1, style="normal")
        prev = b
        top = b.y - GAP

    # The auto path skips approval and enters the tail directly, drawn in the
    # channel so it stays clear of both columns.
    undo_top = user.y - GAP * 1.7
    ax.plot([dec.cx, dec.cx], [dec.y, dec.y - 3.4], color=T0, lw=0.9,
            zorder=3, solid_capstyle="round")
    ax.plot([dec.cx, chan], [dec.y - 3.4, dec.y - 3.4], color=T0, lw=0.9,
            zorder=3, solid_capstyle="round")
    ax.plot([chan, chan], [dec.y - 3.4, undo_top - 3.2], color=T0, lw=0.9,
            zorder=3, solid_capstyle="round")
    arrow(ax, (chan, undo_top - 3.2), (rx, undo_top - 3.2), lw=0.9, color=T0)
    caption_note(ax, dec.cx + 1.4, dec.y - 2.0, "auto", color=T0,
                 style="normal")

    arrow(ax, prev.bottom, (prev.cx, prev.y - 2.8), lw=0.9)
    ax.text(prev.cx, prev.y - 4.6,
            "Result \u2192 Control Panel\n(and TTS if a voice turn)",
            ha="center", va="center", fontsize=7.2, color=BLUE,
            fontweight="bold", linespacing=1.5)

    save(fig, "fig_lifecycle.pdf")


# ===========================================================================
# Fig 3: Gateway internals
# ===========================================================================


def fig_gateway():
    fig, ax = new_canvas(7.4, 5.6)
    H = ax.get_ylim()[1]

    turn = box(ax, 34, H - 7.0, 32, 5.4, "Normalised Turn", fs=8.0,
               fc=BG, ec=BLUE, bold=True)

    cols = [
        ("MODEL ROUTER", "capability probe\ntier select\nfailover\negress gate"),
        ("CONTEXT ENGINE", "RAG retrieve\nmemory merge\ntoken budget\ncitation map"),
        ("POLICY ENGINE", "risk class\nscope check\ngate or allow\negress rules"),
    ]
    cw = 27.0
    xs = [4.0, 36.5, 69.0]
    top = H - 14.0
    cb = []
    for x, (n, s) in zip(xs, cols):
        cb.append(box(ax, x, top - 15.0, cw, 15.0, n, sub=s, fs=7.4, subfs=6.4,
                      fc=WHITE, ec=RULE, bold=True))
        arrow(ax, turn.bottom, (x + cw / 2, top), lw=0.8)

    planner = box(ax, 8.0, top - 30.0, 42, 10.0, "AGENT PLANNER  (LangGraph)",
                  sub="decompose intent  ·  order steps\ndeclare tool calls  ·  NEVER executes",
                  fs=7.6, subfs=6.4, fc=BG, ec=BLUE, bold=True)
    arrow(ax, cb[0].bottom, (planner.cx - 10, planner.y + planner.h), lw=0.8)
    arrow(ax, cb[1].bottom, (planner.cx + 10, planner.y + planner.h), lw=0.8)

    verdict = box(ax, 56.0, top - 27.5, 40, 7.5, "verdict attached to each call",
                  fs=7.2, fc=T1BG, ec=T1)
    arrow(ax, cb[2].bottom, verdict.top, lw=0.8, color=T1)
    arrow(ax, planner.right, verdict.left, lw=0.9, color=BLUE)
    caption_note(ax, 51.0, planner.cy + 2.6, "Plan", color=BLUE, style="normal")

    disp = box(ax, 26.0, top - 41.0, 48, 8.2, "TOOL DISPATCHER",
               sub="verifies verdict  ·  enforces timeout  ·  emits audit record",
               fs=8.0, subfs=6.4, fc=BG, ec=BLUE, bold=True)
    elbow(ax, verdict.bottom, (disp.cx + 12, disp.y + disp.h),
          via_y=disp.y + disp.h + 3.0, lw=0.9, color=T1)

    svcs = ["File\nService", "Code\nService", "Search\nService",
            "Mail\nService", "Doc\nService"]
    sw = 16.0
    sx0 = 6.0
    for i, s in enumerate(svcs):
        b = box(ax, sx0 + i * (sw + 3.0), 1.5, sw, 7.0, s, fs=6.8,
                fc=LIGHTGREY, ec=RULE)
        elbow(ax, disp.bottom, b.top, via_y=disp.y - 2.6, lw=0.75)

    save(fig, "fig_gateway.pdf")


# ===========================================================================
# Fig 4: Model router tiers and egress gate
# ===========================================================================


def fig_router():
    fig, ax = new_canvas(6.8, 4.6)
    H = ax.get_ylim()[1]

    inputs = ["task complexity\nand context size",
              "workspace cloud\npolicy (opt-in)",
              "model health\nand availability"]
    iw = 26.0
    for i, s in enumerate(inputs):
        b = box(ax, 6 + i * (iw + 5), H - 9.5, iw, 8.0, s, fs=6.9,
                fc=LIGHTGREY, ec=RULE)
        elbow(ax, b.bottom, (50, H - 13.0), via_y=H - 11.5, lw=0.8)

    tiers = [
        ("TIER 0", "Local  (Ollama)", "default", T0, T0BG),
        ("TIER 1", "Gemini", "", BLUE, WHITE),
        ("TIER 2", "OpenAI", "", BLUE, WHITE),
        ("TIER 3", "Anthropic", "", BLUE, WHITE),
    ]
    ty = H - 14.0
    th = 5.0
    for i, (tid, name, note, col, bgc) in enumerate(tiers):
        yy = ty - (i + 1) * (th + 1.2)
        b = box(ax, 14, yy, 72, th, "", fc=bgc, ec=col, lw=0.9)
        ax.text(17.5, b.cy, tid, ha="left", va="center", fontsize=7.4,
                color=col, fontweight="bold")
        ax.text(34, b.cy, name, ha="left", va="center", fontsize=7.4, color=INK)
        if note:
            ax.text(82, b.cy, note, ha="right", va="center", fontsize=6.6,
                    color=col, fontstyle="italic")
    yy = ty - 5 * (th + 1.2)
    box(ax, 14, yy, 72, th, "Any OpenAI-compatible endpoint  (user-added)",
        fs=7.0, fc=WHITE, ec=RULE, ls="dashed")

    caption_note(ax, 88, ty - 3.2 * (th + 1.2),
                 "reachable only\nif the workspace\nallows cloud",
                 color=GREY)

    gate = box(ax, 10, 2.0, 80, 10.5, "EGRESS GATE",
               sub="if tier > 0 and workspace cloud is off  →  refuse, degrade, explain\n"
                   "otherwise  →  redact PII, attach budget, record egress in the audit log",
               fs=8.0, subfs=6.6, fc=T2BG, ec=T2, bold=True)
    arrow(ax, (50, yy), gate.top, lw=1.0, color=T2)

    save(fig, "fig_router.pdf")


# ===========================================================================
# Fig 5: Context assembly
# ===========================================================================


def fig_context():
    fig, ax = new_canvas(6.8, 4.4)
    H = ax.get_ylim()[1]

    srcs = ["Current\nTurn", "Session\nMemory", "Long-Term\nMemory (KV)",
            "Workspace\nIndex", "Retrieved\nChunks", "Tool\nResults"]
    sw = 13.8
    for i, s in enumerate(srcs):
        b = box(ax, 3 + i * (sw + 1.6), H - 9.0, sw, 7.5, s, fs=6.5,
                fc=LIGHTGREY, ec=RULE)
        elbow(ax, b.bottom, (50, H - 12.4), via_y=H - 10.8, lw=0.7)

    stages = [
        ("BOUNDS ASSERTION",
         "every chunk carries a workspace_id; any chunk not matching\n"
         "the active grant is DROPPED and the drop is logged", T2BG, T2),
        ("TOKEN BUDGETER",
         "tier-aware, recency and score weighted;\n"
         "never silently truncates a citation source", BG, BLUE),
        ("CITATION MAP",
         "chunk → file → line or page,\n"
         "carried through to the answer", T0BG, T0),
    ]
    y = H - 13.0
    prev = (50, y + 0.6)
    for name, sub, bgc, col in stages:
        b = box(ax, 14, y - 9.4, 72, 9.4, name, sub=sub, fs=8.0, subfs=6.5,
                fc=bgc, ec=col, bold=True)
        arrow(ax, prev, b.top, lw=0.9, color=col)
        prev = b.bottom
        y -= 9.4 + 3.6

    save(fig, "fig_context.pdf")


# ===========================================================================
# Fig 6: Risk tiers
# ===========================================================================


def fig_tiers():
    fig, ax = new_canvas(7.0, 2.5)
    H = ax.get_ylim()[1]

    tiers = [
        ("T0", "READ", "Reads inside the granted\nworkspace. No mutation,\nno egress.",
         "auto-execute", T0, T0BG),
        ("T1", "REVERSIBLE", "Mutates workspace state,\nfully invertible via\nsnapshot.",
         "configurable, full undo", T1, T1BG),
        ("T2", "OUTWARD", "Leaves the machine: mail,\nweb request, cloud call\nwith workspace content.",
         "always gated", T2, T2BG),
        ("T3", "DESTRUCTIVE", "Deletion, overwrite without\nsnapshot, out-of-workspace\nwrite.",
         "refused, no code path", T3, T3BG),
    ]
    cw = 22.4
    for i, (tid, name, desc, rule, col, bgc) in enumerate(tiers):
        x = 2.0 + i * (cw + 2.0)
        b = box(ax, x, 3.4, cw, H - 7.4, "", fc=WHITE, ec=col, lw=1.1)
        # Coloured cap
        ax.add_patch(Rectangle((x, b.y + b.h - 6.2), cw, 6.2, facecolor=bgc,
                               edgecolor=col, linewidth=1.1, zorder=2))
        ax.text(b.cx, b.y + b.h - 3.1, f"{tid}  ·  {name}", ha="center",
                va="center", fontsize=8.0, color=col, fontweight="bold",
                zorder=3)
        # Centre the description in the space between cap and rule line.
        ax.text(b.cx, (b.y + 7.0 + b.y + b.h - 6.2) / 2, desc, ha="center",
                va="center", fontsize=6.6, color=INK, linespacing=1.6,
                zorder=3)
        ax.text(b.cx, b.y + 3.2, rule, ha="center", va="center", fontsize=6.6,
                color=col, fontweight="bold", zorder=3)

    save(fig, "fig_tiers.pdf")


# ===========================================================================
# Fig 7: Policy evaluation order
# ===========================================================================


def fig_policy_order():
    fig, ax = new_canvas(6.6, 3.4)
    H = ax.get_ylim()[1]

    rows = [
        ("1", "Workspace grant check", "outside the grant?", "DENY", T3, T3BG),
        ("2", "Destructive-op check", "delete or overwrite?", "DENY", T3, T3BG),
        ("3", "Egress check", "leaves the machine?", "GATE", T2, T2BG),
        ("4", "Mutation check", "changes state?", "TIER PER CONFIG", T1, T1BG),
        ("5", "Otherwise", "", "ALLOW", T0, T0BG),
    ]
    rh = 7.4
    y = H - 6.0
    ax.text(50, H - 2.4, "First match wins, so a deny cannot be argued past",
            ha="center", va="center", fontsize=7.2, color=BLUE,
            fontstyle="italic")
    for n, name, test, verdict, col, bgc in rows:
        b = box(ax, 4, y - rh, 92, rh, "", fc=WHITE, ec=RULE, lw=0.85)
        ax.text(8.0, b.cy, n, ha="center", va="center", fontsize=7.6,
                color=BLUE, fontweight="bold", zorder=3)
        ax.text(13.0, b.cy, name, ha="left", va="center", fontsize=7.4,
                color=INK, zorder=3)
        ax.text(46.0, b.cy, test, ha="left", va="center", fontsize=7.0,
                color=GREY, fontstyle="italic", zorder=3)
        vb = Rectangle((74.0, b.y + 1.3), 20.0, rh - 2.6, facecolor=bgc,
                       edgecolor=col, linewidth=0.9, zorder=3)
        ax.add_patch(vb)
        ax.text(84.0, b.cy, verdict, ha="center", va="center", fontsize=6.9,
                color=col, fontweight="bold", zorder=4)
        y -= rh + 1.3

    save(fig, "fig_policy_order.pdf")


# ===========================================================================
# Fig 8: Worked approval example
# ===========================================================================


def fig_approval():
    fig, ax = new_canvas(6.8, 5.4)
    H = ax.get_ylim()[1]

    box(ax, 16, H - 7.0, 68, 5.4, "“Tidy up my thesis folder.”", fs=8.4,
        fc=BG, ec=BLUE, bold=True)

    calls = [
        ("1", "list_dir(/Projects/Thesis)", "T0", "auto", T0, T0BG),
        ("2", "read_metadata(*.pdf, *.docx)", "T0", "auto", T0, T0BG),
        ("3", "create_dir(/Projects/Thesis/Drafts)", "T1", "gated", T1, T1BG),
        ("4", "move_files(12 files → /Drafts)", "T1", "gated", T1, T1BG),
    ]
    ax.text(50, H - 10.0, "Planner emits four proposed calls; the Policy Engine classifies each",
            ha="center", va="center", fontsize=7.0, color=GREY, fontstyle="italic")
    y = H - 12.4
    rh = 5.6
    for n, call, tier, act, col, bgc in calls:
        b = box(ax, 8, y - rh, 84, rh, "", fc=WHITE, ec=RULE, lw=0.85)
        ax.text(11.5, b.cy, n, ha="center", va="center", fontsize=7.2,
                color=BLUE, fontweight="bold", zorder=3)
        ax.text(15.5, b.cy, call, ha="left", va="center", fontsize=7.0,
                color=INK, family="monospace", zorder=3)
        ax.add_patch(Rectangle((66, b.y + 1.0), 10, rh - 2.0, facecolor=bgc,
                               edgecolor=col, linewidth=0.9, zorder=3))
        ax.text(71, b.cy, tier, ha="center", va="center", fontsize=6.8,
                color=col, fontweight="bold", zorder=4)
        ax.text(84, b.cy, act, ha="center", va="center", fontsize=6.9,
                color=col, zorder=3)
        y -= rh + 1.2

    # Approval dialogue
    dy = y - 3.0
    dh = 30.0
    ax.add_patch(Rectangle((10, dy - dh), 80, dh, facecolor=WHITE,
                           edgecolor=T1, linewidth=1.3, zorder=2))
    ax.add_patch(Rectangle((10, dy - 6.0), 80, 6.0, facecolor=T1BG,
                           edgecolor=T1, linewidth=1.3, zorder=2))
    ax.text(50, dy - 3.0, "APPROVAL REQUIRED", ha="center", va="center",
            fontsize=8.4, color=T1, fontweight="bold", zorder=3)

    fields = [
        ("Workspace", "/Projects/Thesis   (granted)"),
        ("Operation", "create 1 folder, move 12 files"),
        ("Risk", "T1, reversible"),
        ("Undo", "available for 30 days"),
        ("Outside", "nothing outside the workspace"),
        ("Egress", "none"),
    ]
    fy = dy - 8.6
    for k, v in fields:
        ax.text(15, fy, k, ha="left", va="center", fontsize=6.9, color=GREY,
                zorder=3)
        ax.text(33, fy, v, ha="left", va="center", fontsize=6.9, color=INK,
                zorder=3)
        fy -= 2.5

    btns = [("Approve", T0), ("Approve and remember", T0),
            ("Edit", GREY), ("Reject", T2)]
    bx = 14.0
    for label, col in btns:
        bwid = 4.0 + len(label) * 1.05
        ax.add_patch(Rectangle((bx, dy - dh + 2.2), bwid, 4.2, facecolor=WHITE,
                               edgecolor=col, linewidth=0.9, zorder=3))
        ax.text(bx + bwid / 2, dy - dh + 4.3, label, ha="center", va="center",
                fontsize=6.6, color=col, zorder=4)
        bx += bwid + 2.2

    arrow(ax, (50, y - 0.4), (50, dy), lw=0.9, color=T1)
    ax.text(50, dy - dh - 3.4,
            "approved  →  Snapshot  →  Execute  →  Audit  →  “Done. Undo available.”",
            ha="center", va="center", fontsize=7.4, color=BLUE,
            fontweight="bold")

    save(fig, "fig_approval.pdf")


# ===========================================================================
# Fig 9: Workspace broker
# ===========================================================================


def fig_broker():
    fig, ax = new_canvas(6.4, 4.4)
    H = ax.get_ylim()[1]

    box(ax, 16, H - 7.0, 68, 5.2,
        "Service asks for   “notes/chapter3.md”   (workspace-relative, always)",
        fs=7.4, fc=BG, ec=BLUE)

    steps = [
        "1.  resolve against the active grant root",
        "2.  canonicalise  (realpath, resolving symlinks)",
        "3.  assert the canonical path is under the grant root",
        "4.  assert not in the deny-list  (system, hidden, credential paths)",
        "5.  assert the operation is within the granted permission",
    ]
    bh = 34.0
    by = H - 12.0 - bh
    ax.add_patch(Rectangle((10, by), 80, bh, facecolor=WHITE, edgecolor=BLUE,
                           linewidth=1.2, zorder=2))
    ax.add_patch(Rectangle((10, by + bh - 5.6), 80, 5.6, facecolor=BG,
                           edgecolor=BLUE, linewidth=1.2, zorder=2))
    ax.text(50, by + bh - 2.8, "WORKSPACE BROKER", ha="center", va="center",
            fontsize=8.4, color=BLUE, fontweight="bold", zorder=3)
    sy = by + bh - 10.4
    for i, s in enumerate(steps):
        col = T2 if i == 1 else INK
        ax.text(15, sy, s, ha="left", va="center", fontsize=7.0, color=col,
                fontweight="bold" if i == 1 else "normal", zorder=3)
        sy -= 4.2
    ax.text(50, by + 3.2,
            "any assertion fails  →  raise, log, do not act",
            ha="center", va="center", fontsize=7.2, color=T2,
            fontweight="bold", zorder=3)
    arrow(ax, (50, H - 7.0), (50, by + bh), lw=0.9)

    arrow(ax, (50, by), (50, by - 4.6), lw=0.9)
    ax.text(50, by - 6.6, "a real path, or a refusal", ha="center",
            va="center", fontsize=7.4, color=BLUE, fontweight="bold")
    caption_note(ax, 92, by + bh - 13.4,
                 "canonicalising\nbefore the bounds\ncheck is what stops\ntraversal escapes",
                 color=T2)

    save(fig, "fig_broker.pdf")


# ===========================================================================
# Fig 10: Memory architecture
# ===========================================================================


def fig_memory():
    fig, ax = new_canvas(7.0, 3.9)
    H = ax.get_ylim()[1]

    root = boxtop(ax, 34, H - 1.5, 32, "ARTEMIS MEMORY", fs=8.4,
                  fc=BG, ec=BLUE, bold=True, min_h=5.0)

    kinds = [
        ("SHORT-TERM", "current turn\nactive plan\nscratch", "volatile (RAM)"),
        ("EPISODIC", "session index\nsummaries\nacross chats", "SQLite"),
        ("LONG-TERM (KV)", "preferences\nfacts, config\nnamed entities", "SQLite"),
        ("WORKSPACE", "file index\nfolder state\nrelations", "SQLite + vector"),
        ("PROCEDURAL", "learned task\npatterns (F4)", "SQLite"),
    ]
    cw = 17.4
    kind_top = root.y - 5.2
    bottoms = []
    for i, (n, body, store) in enumerate(kinds):
        x = 2.0 + i * (cw + 2.4)
        b = boxtop(ax, x, kind_top, cw, n, sub=body, fs=6.8, subfs=6.2,
                   fc=WHITE, ec=RULE, bold=True, min_h=14.0)
        elbow(ax, root.bottom, b.top, via_y=root.y - 2.6, lw=0.75)
        # The store label hangs below the box, measured from its real bottom.
        ax.text(b.cx, b.y - text_block_height(1, 6.3) / 2 - 0.9, store,
                ha="center", va="center", fontsize=6.3, color=GREY,
                fontstyle="italic")
        bottoms.append(b)

    label_floor = min(b.y for b in bottoms) - text_block_height(1, 6.3) - 2.4
    ce = boxtop(ax, 26, label_floor - 4.6, 48, "CONTEXT ENGINE",
                sub="merge  \u00b7  budget  \u00b7  bounds-assert", fs=8.0,
                subfs=6.5, fc=BG, ec=BLUE, bold=True, min_h=7.6)
    for b in bottoms:
        elbow(ax, (b.cx, label_floor), (ce.cx + (b.cx - 50) * 0.22,
              ce.y + ce.h), via_y=label_floor - 2.2, lw=0.7)

    arrow(ax, ce.bottom, (50, ce.y - 4.4), lw=1.0, color=BLUE)
    ax.text(50, ce.y - 6.2, "AI GATEWAY", ha="center", va="center",
            fontsize=8.0, color=BLUE, fontweight="bold")

    save(fig, "fig_memory.pdf")


# ===========================================================================
# Fig 11: Memory versus file index
# ===========================================================================


def fig_memory_vs_index():
    fig, ax = new_canvas(6.6, 2.6)
    H = ax.get_ylim()[1]

    panels = [
        ("OS / FILE INDEX", "“What exists, and where?”",
         "Mechanical.  Derived from the filesystem.\n"
         "Rebuildable at any time.\nCarries no interpretation.", RULE, LIGHTGREY),
        ("ARTEMIS MEMORY", "“What do I know about this workspace,\n"
         "this task, and what happened before?”",
         "Interpretive.  Accumulated.\nLost if deleted.\nRequires consent to build.", BLUE, BG),
    ]
    pw = 45.0
    for i, (title, q, body, col, bgc) in enumerate(panels):
        x = 3.0 + i * (pw + 4.0)
        b = box(ax, x, 4.0, pw, H - 9.0, "", fc=WHITE, ec=col, lw=1.2)
        ax.add_patch(Rectangle((x, b.y + b.h - 6.0), pw, 6.0, facecolor=bgc,
                               edgecolor=col, linewidth=1.2, zorder=2))
        ax.text(b.cx, b.y + b.h - 3.0, title, ha="center", va="center",
                fontsize=8.2, color=col, fontweight="bold", zorder=3)
        ax.text(b.cx, b.y + b.h - 11.0, q, ha="center", va="center",
                fontsize=7.2, color=INK, fontstyle="italic", linespacing=1.6,
                zorder=3)
        ax.text(b.cx, b.y + 6.4, body, ha="center", va="center", fontsize=6.8,
                color=GREY, linespacing=1.7, zorder=3)

    ax.text(50, 1.4,
            "Conflating the two is the mistake that turns a bounded assistant into a surveillance tool",
            ha="center", va="center", fontsize=6.9, color=T2, fontstyle="italic")

    save(fig, "fig_memory_vs_index.pdf")


# ===========================================================================
# Fig 12: Remote access plane
# ===========================================================================


def fig_remote():
    fig, ax = new_canvas(6.4, 5.2)
    H = ax.get_ylim()[1]
    GAP = 5.0

    top = H - 2.0
    dev = boxtop(ax, 22, top, 56, "PHONE  /  TABLET  /  SECOND LAPTOP",
                 sub="Remote PWA (installable)", fs=7.4, subfs=6.3,
                 fc=LIGHTGREY, ec=RULE)

    pages = boxtop(ax, 22, dev.y - GAP, 56, "CLOUDFLARE PAGES",
                   sub="static PWA shell, no user data", fs=7.4, subfs=6.3,
                   fc=WHITE, ec=RULE)
    arrow(ax, dev.bottom, pages.top, lw=0.9)
    caption_note(ax, 80, (dev.y + pages.y + pages.h) / 2, "HTTPS")

    wrk = boxtop(ax, 22, pages.y - GAP, 56, "CLOUDFLARE WORKER",
                 sub="device auth and pairing  \u00b7  token issue and revoke\n"
                     "rate limiting  \u00b7  routes to the right Durable Object\n"
                     "stores no user content",
                 fs=7.4, subfs=6.2, fc=WHITE, ec=RULE)
    arrow(ax, pages.bottom, wrk.top, lw=0.9)

    # Durable Object panel: two columns stacked in real font units.
    holds = ["which authenticated device is",
             "connected to which host",
             "connection liveness",
             "opaque encrypted frames"]
    never = ["plaintext messages",
             "workspace content",
             "embeddings, memory, credentials",
             "decryption keys"]
    col_fs, item_fs = 6.8, 6.3
    body_h = (text_block_height(1, col_fs) + pt(col_fs * 0.6)
              + text_block_height(4, item_fs, 1.55) + 4.2)
    head_h = text_block_height(1, 7.8) + 2 * 1.2
    doy = wrk.y - GAP - head_h - body_h
    dbody, _ = panel(ax, 14, doy, 72, "DURABLE OBJECT  \u00b7  one per pairing",
                     body_h=body_h, fs=7.8)
    inner_top = dbody.y + dbody.h - 2.2
    col_list(ax, 18, inner_top, "HOLDS", holds, tc=T0, fs=col_fs,
             itemfs=item_fs)
    col_list(ax, 52, inner_top, "NEVER HOLDS", never, tc=T2, fs=col_fs,
             itemfs=item_fs)
    arrow(ax, wrk.bottom, (50, doy + body_h + head_h), lw=0.9)

    host = boxtop(ax, 14, doy - GAP * 1.8, 72, "ARTEMIS HOST MACHINE",
                  sub="Remote Bridge: outbound connection only,\n"
                      "no inbound port, no NAT traversal\n"
                      "Same Control Panel view model, same Layer 2 entry,\n"
                      "same gates, no privileged path",
                  fs=8.0, subfs=6.3, fc=BG, ec=BLUE, bold=True)
    arrow(ax, (50, doy), host.top, lw=1.1, color=BLUE)
    caption_note(ax, 88, (doy + host.y + host.h) / 2,
                 "WebSocket,\nend-to-end\nencrypted", color=BLUE)

    save(fig, "fig_remote.pdf")


# ===========================================================================
# Fig 13: Pairing handshake
# ===========================================================================


def fig_pairing():
    fig, ax = new_canvas(6.8, 4.0)
    H = ax.get_ylim()[1]

    lanes = [("HOST", 16.0), ("EDGE", 50.0), ("DEVICE", 84.0)]
    for name, x in lanes:
        ax.text(x, H - 2.6, name, ha="center", va="center", fontsize=8.0,
                color=BLUE, fontweight="bold")
        ax.plot([x, x], [3.0, H - 5.4], color=RULE, lw=0.9, zorder=1)

    steps = [
        (16.0, 50.0, "request pairing", INK, "solid"),
        (50.0, 16.0, "pairing code + Durable Object id", INK, "solid"),
        (None, None, "host displays the code and a QR on the local GUI", GREY, None),
        (84.0, 50.0, "scan or enter the code", INK, "solid"),
        (50.0, 84.0, "challenge", INK, "solid"),
        (84.0, 50.0, "response", INK, "solid"),
        (84.0, 16.0, "end-to-end key exchange, relayed by the edge, which cannot read it", T0, "dashed"),
        (None, None, "HOST OWNER MUST CONFIRM ON THE LOCAL MACHINE", T2, None),
        (16.0, 84.0, "encrypted session established", T0, "solid"),
    ]
    y = H - 7.6
    for x0, x1, label, col, ls in steps:
        if x0 is None:
            ax.text(50, y, label, ha="center", va="center", fontsize=6.9,
                    color=col, fontweight="bold" if col == T2 else "normal",
                    fontstyle="italic" if col == GREY else "normal", zorder=4)
        else:
            arrow(ax, (x0, y), (x1, y), color=col, lw=0.9, ls=ls, shrink=0)
            ax.text((x0 + x1) / 2, y + 1.9, label, ha="center", va="center",
                    fontsize=6.5, color=col, zorder=4)
        y -= 5.2

    ax.text(50, 1.4,
            "Possession of the pairing code alone is never sufficient: compromising the edge cannot pair a device",
            ha="center", va="center", fontsize=6.8, color=T2, fontstyle="italic")

    save(fig, "fig_pairing.pdf")


# ===========================================================================
# Fig 14: Prompt injection defence
# ===========================================================================


def fig_injection():
    fig, ax = new_canvas(6.6, 4.4)
    H = ax.get_ylim()[1]

    layers = [
        ("1", "PROVENANCE TAGGING",
         "Chunks are tagged user, workspace-file, web or tool-result.\n"
         "Only user chunks may originate an intent."),
        ("2", "PLAN, NOT PROSE, IS THE INTERFACE",
         "A tool call must be a well-formed declaration; document text\n"
         "cannot become one by being persuasive."),
        ("3", "POLICY IS OUT-OF-BAND",
         "The Policy Engine reads the ToolCall, never the reasoning text.\n"
         "Nothing in a document can change a verdict."),
        ("4", "THE USER IS THE LAST GATE",
         "Every outward action shows a concrete preview: recipient,\n"
         "content, destination."),
        ("5", "BOUNDS SHRINK THE BLAST RADIUS",
         "Even a fully successful injection is confined to one workspace,\n"
         "cannot delete, and cannot exceed its egress policy."),
    ]
    rh = 11.4
    y = H - 2.0
    for n, title, body in layers:
        b = box(ax, 4, y - rh, 92, rh, "", fc=WHITE, ec=RULE, lw=0.9)
        ax.add_patch(Rectangle((4, b.y), 7.0, rh, facecolor=BG,
                               edgecolor=RULE, linewidth=0.9, zorder=2))
        ax.text(7.5, b.cy, n, ha="center", va="center", fontsize=10.0,
                color=BLUE, fontweight="bold", zorder=3)
        ax.text(14.0, b.cy + 3.0, title, ha="left", va="center", fontsize=7.6,
                color=INK, fontweight="bold", zorder=3)
        ax.text(14.0, b.cy - 2.4, body, ha="left", va="center", fontsize=6.7,
                color=GREY, linespacing=1.6, zorder=3)
        y -= rh + 1.6

    save(fig, "fig_injection.pdf")


# ===========================================================================
# Fig 15: Performance planes
# ===========================================================================


def fig_performance():
    fig, ax = new_canvas(6.8, 4.0)
    H = ax.get_ylim()[1]

    ax.add_patch(Rectangle((4, H - 16.0), 92, 13.0, facecolor=BG,
                           edgecolor=BLUE, linewidth=1.2, zorder=1))
    ax.text(50, H - 5.4, "INTERACTIVE PATH  ·  must feel immediate",
            ha="center", va="center", fontsize=8.2, color=BLUE,
            fontweight="bold", zorder=3)
    steps = ["Input", "Intent", "Plan", "Approve", "Execute", "Result"]
    sw = 12.4
    sx = 9.0
    prev = None
    for s in steps:
        b = box(ax, sx, H - 13.6, sw, 5.4, s, fs=7.0, fc=WHITE, ec=BLUE)
        if prev:
            arrow(ax, prev.right, b.left, lw=0.8, color=BLUE, shrink=0.5)
        prev = b
        sx += sw + 2.4
    ax.text(50, H - 15.0,
            "target: first token under 1 s local, under 2 s cloud",
            ha="center", va="center", fontsize=6.6, color=GREY,
            fontstyle="italic", zorder=3)

    arrow(ax, (50, H - 16.6), (50, H - 21.0), lw=1.0)
    caption_note(ax, 52.5, H - 18.8, "never blocks on", color=GREY)

    qy = H - 29.0
    ax.add_patch(Rectangle((4, qy), 92, 7.0, facecolor=LIGHTGREY,
                           edgecolor=RULE, linewidth=1.0, zorder=1))
    ax.text(50, qy + 3.5, "PRIORITY WORK QUEUE", ha="center", va="center",
            fontsize=8.0, color=INK, fontweight="bold", zorder=3)

    workers = ["File Watch\nand Index", "Embed\nWorker Pool", "RAG\nIngest",
               "Model\nWarm", "Remote\nSync"]
    ww = 16.0
    wx = 6.0
    for wname in workers:
        b = box(ax, wx, qy - 12.0, ww, 8.4, wname, fs=6.6, fc=WHITE, ec=RULE)
        arrow(ax, (b.cx, qy), b.top, lw=0.8)
        wx += ww + 2.5

    ax.text(50, 3.0,
            "BACKGROUND PATH  ·  may take minutes, always cancellable, progress always visible",
            ha="center", va="center", fontsize=7.2, color=BLUE,
            fontstyle="italic")

    save(fig, "fig_performance.pdf")


# ===========================================================================
# Fig 16: Deployment topology
# ===========================================================================


def fig_topology():
    fig, ax = new_canvas(6.6, 4.2)
    H = ax.get_ylim()[1]

    ax.add_patch(Rectangle((3, 12.0), 94, H - 15.0, facecolor="#FBFCFD",
                           edgecolor=BLUE, linewidth=1.3, zorder=1))
    ax.text(5.5, H - 4.6, "USER MACHINE", ha="left", va="center", fontsize=8.0,
            color=BLUE, fontweight="bold", zorder=3)

    core = box(ax, 8, H - 22.0, 84, 11.0, "artemis-core",
               sub="Python, long-running background process\n"
                   "Layers 2, 3, 4 and 5 plus both planes\n"
                   "serves loopback HTTP and WebSocket on 127.0.0.1 only",
               fs=8.4, subfs=6.5, fc=BG, ec=BLUE, bold=True)

    clients = [("artemis-cli", "Typer", 10.0), ("Gradio GUI", "browser", 38.0),
               ("remote-bridge", "outbound WebSocket", 66.0)]
    cb = []
    for name, sub, x in clients:
        b = box(ax, x, H - 34.0, 24.0, 8.0, name, sub=sub, fs=7.2, subfs=6.3,
                fc=WHITE, ec=RULE)
        arrow(ax, (b.cx, core.y), b.top, lw=0.8)
        cb.append(b)

    box(ax, 10, 15.0, 52.0, 7.0, "ollama",
        sub="separate process, local models", fs=7.6, subfs=6.4,
        fc=LIGHTGREY, ec=RULE)

    edge = box(ax, 62, 1.5, 34, 7.0, "Cloudflare  (Worker + DO)", fs=7.6,
               fc=WHITE, ec=RULE, ls="dashed")
    elbow(ax, cb[2].bottom, edge.top, via_y=10.5, lw=0.9, color=BLUE)
    caption_note(ax, 71.5, 11.6, "outbound only", color=BLUE, ha="right")

    save(fig, "fig_topology.pdf")


# ===========================================================================
# Fig 17: Capability services over the shared substrate
# ===========================================================================


def fig_services():
    fig, ax = new_canvas(6.8, 3.2)
    H = ax.get_ylim()[1]

    disp = box(ax, 8, H - 7.4, 84, 5.8, "TOOL DISPATCHER", fs=8.4,
               fc=BG, ec=BLUE, bold=True)

    feats = [
        ("F1", "Session\nResume", T0),
        ("F2", "Folder\nTidy", T1),
        ("F3", "Notes\nSynthesis", T0),
        ("F4", "Pattern\nWatcher", T1),
        ("F5", "Code\nAssistant", T0),
        ("F6", "Web\nSearch", T2),
        ("F7", "Mail\nComposer", T2),
        ("F8", "Document\nDrafter", T1),
        ("F9", "Speech\nI/O", GREY),
    ]
    fw = 9.2
    gapw = 1.4
    total = len(feats) * fw + (len(feats) - 1) * gapw
    fx0 = (100 - total) / 2
    fy = H - 20.0
    for i, (fid, name, col) in enumerate(feats):
        x = fx0 + i * (fw + gapw)
        b = box(ax, x, fy, fw, 9.0, "", fc=WHITE, ec=col, lw=1.0)
        ax.text(b.cx, b.y + b.h - 2.2, fid, ha="center", va="center",
                fontsize=7.0, color=col, fontweight="bold", zorder=3)
        ax.text(b.cx, b.cy - 1.2, name, ha="center", va="center", fontsize=6.0,
                color=INK, linespacing=1.5, zorder=3)
        arrow(ax, (b.cx, disp.y), b.top, lw=0.75)

    sub = box(ax, 12, 3.0, 76, 13.0, "SHARED SUBSTRATE",
              sub="Workspace Broker, for all path resolution\n"
                  "Undo Journal, for all snapshots\n"
                  "Approval Broker, for all gating\n"
                  "Data plane, for all persistence",
              fs=8.0, subfs=6.5, fc=BG, ec=BLUE, bold=True)
    for i in range(len(feats)):
        x = fx0 + i * (fw + gapw) + fw / 2
        elbow(ax, (x, fy), (sub.cx + (x - 50) * 0.55, sub.y + sub.h),
              via_y=fy - 2.6, lw=0.7)

    caption_note(ax, 50, 1.2,
                 "no capability service touches the filesystem, the network or the database directly",
                 color=GREY, ha="center")

    save(fig, "fig_services.pdf")


# ===========================================================================


def main():
    print("Generating ARTEMIS architecture figures")
    for fn in (
        fig_layers,
        fig_lifecycle,
        fig_gateway,
        fig_router,
        fig_context,
        fig_tiers,
        fig_policy_order,
        fig_approval,
        fig_broker,
        fig_memory,
        fig_memory_vs_index,
        fig_remote,
        fig_pairing,
        fig_injection,
        fig_performance,
        fig_topology,
        fig_services,
    ):
        fn()
    print("All figures written to", OUT)


if __name__ == "__main__":
    main()
