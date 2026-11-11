"""Figures added to the report in the third deliverable: the ER diagram (4.9.1), the class diagram (6.5)
and the navigation flow of the interface (4.8). Run from this folder:  python gen_report_figures.py

The ER diagram mirrors the CREATE TABLE statements in src/artemis/data/store.py and the class diagram
mirrors the classes and members in src/artemis/core, so that the figures stay true to the code.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon

OUT = os.path.dirname(os.path.abspath(__file__))
INK, BLUE, GREY, RULE = "#1F2937", "#2B5FA5", "#6B7280", "#9CA3AF"
HEAD, BG, WHITE = "#DCE8F5", "#F5F8FC", "#FFFFFF"
GREEN, AMBER, RED = "#2E7D5B", "#B7791F", "#B03A48"
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                     "text.color": INK, "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.03})


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.set_aspect("equal"); ax.axis("off")
    return fig, ax


def table_box(ax, x, y, w, name, rows, fs=7.6, rh=0.172, hh=0.26, ec=BLUE, hfc=HEAD, dashed=False):
    """Entity box. rows are (marker, text). y is the bottom edge. Returns (x, y, w, h)."""
    h = hh + rh * len(rows) + 0.05
    ax.add_patch(Rectangle((x, y), w, h, fc=WHITE, ec=ec, lw=1.0, ls="--" if dashed else "-", zorder=2))
    ax.add_patch(Rectangle((x, y + h - hh), w, hh, fc=hfc, ec=ec, lw=1.0, zorder=3))
    ax.text(x + w / 2, y + h - hh / 2, name, ha="center", va="center", fontsize=fs + 0.8, fontweight="bold", color=ec, zorder=4)
    for i, (mk, tx) in enumerate(rows):
        yy = y + h - hh - rh * (i + 0.62) - 0.02
        if mk:
            ax.text(x + 0.07, yy, mk, ha="left", va="center", fontsize=fs - 0.8, fontweight="bold",
                    color=AMBER if mk == "PK" else GREEN, zorder=4)
        ax.text(x + 0.40, yy, tx, ha="left", va="center", fontsize=fs, zorder=4)
    return (x, y, w, h)


def line(ax, p, q, ls="-", color=BLUE, lw=1.0, z=1):
    ax.plot([p[0], q[0]], [p[1], q[1]], ls=ls, color=color, lw=lw, zorder=z, solid_capstyle="butt")


def label(ax, x, y, t, fs=7.2, color=INK, ha="center", bold=False, bg=True):
    ax.text(x, y, t, ha=ha, va="center", fontsize=fs, color=color, fontweight="bold" if bold else "normal", zorder=6,
            bbox=dict(fc="white", ec="none", pad=0.6) if bg else None)


# --------------------------------------------------------------------------------------------------
def fig_er():
    W, H = 6.7, 7.9
    fig, ax = canvas(W, H)
    w = 1.95
    ws = table_box(ax, 2.37, 4.55, w, "workspaces", [("PK", "id"), ("", "name"), ("", "root  (unique, canonical)"), ("", "permission"), ("", "cloud_policy"), ("", "created_at")])
    fi = table_box(ax, 0.15, 6.0, w, "file_index", [("PK", "id"), ("FK", "workspace_id"), ("", "rel_path"), ("", "mtime"), ("", "size"), ("", "content_hash"), ("", "file_type"), ("", "indexed_at")])
    mk = table_box(ax, 2.37, 6.55, w, "memory_kv", [("PK", "id"), ("FK", "workspace_id  (nullable)"), ("", "key"), ("", "value"), ("", "updated_at")])
    ar = table_box(ax, 4.6, 6.4, w, "automation_rules", [("PK", "id"), ("FK", "workspace_id"), ("", "description"), ("", "status"), ("", "created_at")])
    se = table_box(ax, 0.15, 4.35, w, "sessions", [("PK", "id"), ("FK", "workspace_id"), ("", "started_at"), ("", "ended_at"), ("", "resume_state")])
    pr = table_box(ax, 4.6, 4.9, w, "policy_rules", [("PK", "id"), ("FK", "workspace_id"), ("", "operation"), ("", "decision"), ("", "created_at")])
    tu = table_box(ax, 0.15, 2.65, w, "turns", [("PK", "id"), ("FK", "session_id"), ("", "ts"), ("", "role"), ("", "content")])
    uj = table_box(ax, 4.6, 2.85, w, "undo_journal", [("PK", "id"), ("FK", "workspace_id"), ("", "plan_id"), ("", "forward_op"), ("", "inverse_op"), ("", "snapshot_ref"), ("", "created_at")])
    au = table_box(ax, 2.37, 2.5, w, "audit_log", [("PK", "id"), ("", "ts"), ("", "workspace_id  (no FK)"), ("", "event"), ("", "outcome"), ("", "detail"), ("", "prev_hash"), ("", "entry_hash")], ec=RED, hfc="#F8E3E6", dashed=False)

    cx = ws[0] + ws[2] / 2
    # workspace to children (identifying one-to-many, cascade)
    def rel(a, b, pa, pb, mid=None):
        line(ax, pa, pb)
        label(ax, pa[0] + (pb[0] - pa[0]) * 0.10 + (0.1 if pb[0] >= pa[0] else -0.1), pa[1] + (pb[1] - pa[1]) * 0.10, "1", 7.4, BLUE, bold=True)
        label(ax, pb[0] - (pb[0] - pa[0]) * 0.10 - (0.1 if pb[0] >= pa[0] else -0.1), pb[1] - (pb[1] - pa[1]) * 0.10, "N", 7.4, BLUE, bold=True)
    rel(ws, mk, (cx, ws[1] + ws[3]), (cx, mk[1]))
    rel(ws, fi, (ws[0], ws[1] + ws[3] - 0.35), (fi[0] + fi[2], fi[1] + 0.45))
    rel(ws, ar, (ws[0] + ws[2], ws[1] + ws[3] - 0.25), (ar[0], ar[1] + 0.55))
    rel(ws, se, (ws[0], ws[1] + 0.45), (se[0] + se[2], se[1] + 0.55))
    rel(ws, pr, (ws[0] + ws[2], ws[1] + 0.8), (pr[0], pr[1] + 0.55))
    rel(ws, uj, (ws[0] + ws[2], ws[1] + 0.25), (uj[0], uj[1] + 0.9))
    rel(se, tu, (se[0] + w / 2, se[1]), (tu[0] + w / 2, tu[1] + tu[3]))
    # audit log: references the workspace, no cascade
    line(ax, (cx, ws[1]), (cx, au[1] + au[3]), ls=(0, (4, 3)), color=RED)
    label(ax, cx, ws[1] - 0.17, "references only; no cascade", 7.2, RED)
    label(ax, cx + 0.16, ws[1] - 0.04, "", 7)
    label(ax, cx - 0.65, (ws[1] + au[1] + au[3]) / 2 + 0.01, "audit record survives revocation", 6.8, RED, bg=False) if False else None

    # application-level tables
    ax.add_patch(FancyBboxPatch((0.08, 0.1), 6.54, 2.02, boxstyle="round,pad=0.0,rounding_size=0.08", fc=BG, ec=RULE, lw=0.9, ls="--", zorder=0))
    ax.text(0.2, 1.95, "Application-level tables, not owned by any workspace", fontsize=8.0, fontweight="bold", color=GREY, va="center")
    cs = table_box(ax, 0.2, 0.28, 1.7, "chat_sessions", [("PK", "id"), ("", "title"), ("", "created_at"), ("", "updated_at")])
    ct = table_box(ax, 2.37, 0.25, 1.95, "chat_turns", [("PK", "id"), ("FK", "session_id"), ("", "said"), ("", "reply"), ("", "created_at")])
    table_box(ax, 4.6, 0.95, 1.95, "app_settings", [("PK", "key"), ("", "value")])
    table_box(ax, 4.6, 0.25, 1.95, "schema_meta", [("PK", "key"), ("", "value")])
    line(ax, (cs[0] + cs[2], cs[1] + 0.55), (ct[0], ct[1] + 0.55))
    label(ax, cs[0] + cs[2] + 0.1, cs[1] + 0.55, "1", 7.4, BLUE, bold=True)
    label(ax, ct[0] - 0.1, ct[1] + 0.55, "N", 7.4, BLUE, bold=True)

    # key
    ax.text(0.15, 7.78, "PK  primary key", fontsize=7.4, color=AMBER, fontweight="bold", va="center")
    ax.text(1.35, 7.78, "FK  foreign key, ON DELETE CASCADE", fontsize=7.4, color=GREEN, fontweight="bold", va="center")
    ax.text(3.85, 7.78, "1 / N  one to many", fontsize=7.4, color=BLUE, fontweight="bold", va="center")
    fig.savefig(os.path.join(OUT, "fig_er.pdf"), transparent=True); plt.close(fig); print("fig_er")


# --------------------------------------------------------------------------------------------------
def class_box(ax, x, y, w, name, attrs, meths, stereotype="", ec=BLUE, hfc=HEAD, fs=6.9, rh=0.152):
    n = len(attrs) + len(meths)
    hh = 0.43 if stereotype else 0.28
    h = hh + rh * n + 0.12
    ax.add_patch(Rectangle((x, y), w, h, fc=WHITE, ec=ec, lw=1.0, zorder=2))
    ax.add_patch(Rectangle((x, y + h - hh), w, hh, fc=hfc, ec=ec, lw=1.0, zorder=3))
    if stereotype:
        ax.text(x + w / 2, y + h - 0.1, stereotype, ha="center", va="center", fontsize=fs - 0.6, color=GREY, zorder=4)
        ax.text(x + w / 2, y + h - 0.29, name, ha="center", va="center", fontsize=fs + 1.2, fontweight="bold", color=ec, zorder=4)
    else:
        ax.text(x + w / 2, y + h - hh / 2, name, ha="center", va="center", fontsize=fs + 1.2, fontweight="bold", color=ec, zorder=4)
    yy = y + h - hh - 0.05
    for a_ in attrs:
        yy -= rh
        ax.text(x + 0.06, yy + rh / 2, a_, ha="left", va="center", fontsize=fs, zorder=4)
    sep = yy - 0.02
    ax.plot([x, x + w], [sep, sep], color=ec, lw=0.7, zorder=3)
    yy = sep - 0.03
    for m in meths:
        yy -= rh
        ax.text(x + 0.06, yy + rh / 2, m, ha="left", va="center", fontsize=fs, zorder=4)
    return (x, y, w, h)


def arrow(ax, p, q, kind="assoc", color=INK, ls="-"):
    """kind: assoc (open arrow), dep (dashed open arrow), comp (filled diamond at p)."""
    import numpy as np
    ax.plot([p[0], q[0]], [p[1], q[1]], ls=ls, color=color, lw=1.0, zorder=1)
    d = np.array([q[0] - p[0], q[1] - p[1]], float); L = np.hypot(*d)
    if L == 0:
        return
    u = d / L; n = np.array([-u[1], u[0]])
    if kind in ("assoc", "dep"):
        a = np.array(q) - u * 0.13
        ax.add_patch(Polygon([q, a + n * 0.055, a - n * 0.055], closed=False, fill=False, ec=color, lw=1.0, zorder=3))
    if kind == "comp":
        a = np.array(p) + u * 0.0
        pts = [a, a + u * 0.1 + n * 0.05, a + u * 0.2, a + u * 0.1 - n * 0.05]
        ax.add_patch(Polygon(pts, closed=True, fc=INK, ec=INK, lw=0.8, zorder=3))


def fig_class():
    W, H = 6.7, 7.9
    fig, ax = canvas(W, H)
    vo = "#FBF1DF"
    TOP = 7.55
    def top(h): return TOP - h
    # row 1: the four immutable value objects
    rs = class_box(ax, 0.1, 0, 1.55, "Resolved", ["+ path: Path", "+ workspace_id: int", "+ rel_path: str", "+ operation: Operation"], [], "<<immutable>>", ec=AMBER, hfc=vo)
    rs = (rs[0], top(rs[3]), rs[2], rs[3]); ax.clear(); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    rs = class_box(ax, 0.1, top(1.25), 1.55, "Resolved", ["+ path: Path", "+ workspace_id: int", "+ rel_path: str", "+ operation: Operation"], [], "<<immutable>>", ec=AMBER, hfc=vo)
    plan = class_box(ax, 1.75, top(1.4), 1.5, "Plan", ["+ plan_id: str", "+ intent: str", "+ calls: tuple[ToolCall]"], ["+ summarise(): str", "+ to_json(): str"], "<<immutable>>", ec=AMBER, hfc=vo)
    plan = (plan[0], top(plan[3]), plan[2], plan[3])
    ax.patches.clear() if False else None
    return_vals = None
    fig.clf(); fig, ax = canvas(W, H)
    def put(x, w, name, attrs, meths, st, ec=BLUE, hfc=HEAD, y_top=None, y=None):
        # draw with the top edge at y_top (or bottom at y)
        tmp_h = (0.43 if st else 0.28) + 0.152 * (len(attrs) + len(meths)) + 0.12
        yy = (y_top - tmp_h) if y_top is not None else y
        return class_box(ax, x, yy, w, name, attrs, meths, st, ec=ec, hfc=hfc)
    rs = put(0.1, 1.55, "Resolved", ["+ path: Path", "+ workspace_id: int", "+ rel_path: str", "+ operation: Operation"], [], "<<immutable>>", AMBER, vo, y_top=TOP)
    plan = put(1.75, 1.5, "Plan", ["+ plan_id: str", "+ intent: str", "+ calls: tuple[ToolCall]"], ["+ summarise(): str", "+ to_json(): str"], "<<immutable>>", AMBER, vo, y_top=TOP)
    call = put(3.55, 1.5, "ToolCall", ["+ operation: str", "+ workspace_id: int", "+ paths: tuple[str]", "+ arguments: dict", "+ call_id: str"], ["+ describe(): str", "+ fingerprint(): str"], "<<immutable>>", AMBER, vo, y_top=TOP)
    verd = put(5.2, 1.45, "Verdict", ["+ call_id: str", "+ tier: Tier", "+ decision: Decision", "+ reason: str", "+ rule_applied: str", "+ remembered: bool"], ["+ needs_approval(): bool", "+ refused(): bool", "+ matches(call): bool"], "<<immutable>>", AMBER, vo, y_top=TOP)
    # row 2: services
    wb = put(0.1, 1.55, "WorkspaceBroker", [], ["+ resolve(ws, ref, op)", "+ is_within_grant(ws, path)"], "<<service>>", y=3.55)
    ab = put(1.7, 1.55, "ApprovalBroker", [], ["+ submit(plan, verdicts)", "+ build_preview(...)", "+ approve(plan_id, remember)", "+ reject(plan_id, reason)", "+ expire(plan_id)", "+ is_approved(plan_id)"], "<<service>>", y=3.0)
    pe = put(3.65, 2.95, "PolicyEngine", [], ["+ classify(call): Verdict", "+ classify_plan(plan): dict", "+ highest_tier(verdicts): Tier", "+ remember(call, mode)", "+ forget_rule(rule_id)"], "<<service>>", y=3.25)
    # row 3
    uj = put(0.1, 1.7, "UndoJournal", [], ["+ record_write(...)", "+ record_move(...)", "+ record_mkdir(...)", "+ entries_for_plan(plan_id)", "+ undo_plan(plan_id)"], "<<service>>", y=0.25)
    td = put(2.1, 2.9, "ToolDispatcher", ["- handlers: dict[str, Handler]"], ["+ register(operation, handler)", "+ execute(call, verdict, plan_id)", "+ execute_plan(plan, verdicts)"], "<<service>>  the only component that acts", RED, "#F8E3E6", y=0.25)

    # Plan 1 <>-- 1..* ToolCall
    arrow(ax, (plan[0] + plan[2], plan[1] + plan[3] - 0.6), (call[0], plan[1] + plan[3] - 0.6), "comp")
    label(ax, 3.4, plan[1] + plan[3] - 0.45, "1..*", 7.0, bg=False)
    # WorkspaceBroker creates Resolved
    arrow(ax, (0.6, wb[1] + wb[3]), (0.6, rs[1]), "dep", ls="--"); label(ax, 0.6, 5.0, "creates", 7)
    # PolicyEngine reads ToolCall, creates Verdict
    arrow(ax, (4.1, pe[1] + pe[3]), (4.1, call[1]), "dep", ls="--"); label(ax, 4.1, 4.9, "reads", 7)
    arrow(ax, (6.2, pe[1] + pe[3]), (6.2, verd[1]), "dep", ls="--"); label(ax, 6.2, 4.9, "creates", 7)
    # ApprovalBroker holds Plan; uses PolicyEngine
    arrow(ax, (2.5, ab[1] + ab[3]), (2.5, plan[1]), "assoc"); label(ax, 2.5, 5.1, "holds pending", 7)
    arrow(ax, (ab[0] + ab[2], ab[1] + 0.9), (pe[0], pe[1] + 0.9), "assoc"); label(ax, 3.45, ab[1] + 0.9 + 0.12, "uses", 6.8)
    # PolicyEngine uses WorkspaceBroker (route above ApprovalBroker)
    yv = 5.0 - 0.0
    ypath = ab[1] + ab[3] + 0.25
    ax.plot([pe[0] + 0.5, pe[0] + 0.5, 1.35, 1.35], [pe[1] + pe[3], ypath, ypath, wb[1] + wb[3]], color=INK, lw=1.0, zorder=1)
    import numpy as np
    a_ = np.array([1.35, wb[1] + wb[3]]); ax.add_patch(Polygon([a_, a_ + [0.055, 0.13], a_ + [-0.055, 0.13]], closed=False, fill=False, ec=INK, lw=1.0, zorder=3))
    label(ax, 2.2, ypath, "uses", 7)
    # ToolDispatcher: asks ApprovalBroker, resolves again through WorkspaceBroker, records in UndoJournal
    arrow(ax, (3.0, td[1] + td[3]), (2.9, ab[1]), "assoc"); label(ax, 2.95, 2.0, "asks", 7)
    arrow(ax, (td[0] + 0.2, td[1] + td[3]), (0.95, wb[1]), "assoc"); label(ax, 1.3, 2.45, "resolves again", 7)
    arrow(ax, (td[0], td[1] + 0.5), (uj[0] + uj[2], uj[1] + 0.5), "assoc"); label(ax, 1.95, uj[1] + 0.5 + 0.13, "records", 6.8)
    ax.text(0.1, 7.78, "Solid arrow: dependency held by the class.   Dashed arrow: creates or reads.   Filled diamond: composition.", fontsize=7.0, color=GREY, va="center")
    fig.savefig(os.path.join(OUT, "fig_class.pdf"), transparent=True); plt.close(fig); print("fig_class")


# --------------------------------------------------------------------------------------------------
def fig_nav():
    W, H = 6.7, 3.5
    fig, ax = canvas(W, H)
    def node(x, y, w, h, t, sub="", ec=BLUE, fc=HEAD):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.07", fc=fc, ec=ec, lw=1.1, zorder=2))
        ax.text(x + w / 2, y + h / 2 + (0.1 if sub else 0), t, ha="center", va="center", fontsize=8.6, fontweight="bold", color=ec, zorder=3)
        if sub:
            ax.text(x + w / 2, y + h / 2 - 0.13, sub, ha="center", va="center", fontsize=6.9, color=GREY, zorder=3)
        return (x, y, w, h)
    work = node(2.55, 1.6, 1.6, 0.8, "Work", "ask, tidy, voice, chats")
    appr = node(4.9, 2.4, 1.6, 0.8, "Approval card", "preview, approve, reject", ec=AMBER, fc="#FBF1DF")
    res = node(4.9, 0.9, 1.6, 0.8, "Result and Undo", "what changed", ec=GREEN, fc="#E4F2EA")
    fol = node(0.2, 2.4, 1.6, 0.8, "Folders", "add, list, remove")
    kn = node(0.2, 0.9, 1.6, 0.8, "What it knows", "see and erase")
    st = node(2.55, 0.25, 1.6, 0.7, "Settings", "models, mail, remote")
    def ar(p, q, t="", dy=0.0, dx=0.0):
        arrow(ax, p, q, "assoc", color=INK)
        if t:
            label(ax, (p[0] + q[0]) / 2 + dx, (p[1] + q[1]) / 2 + dy, t, 7.0)
    ar((work[0] + work[2], work[1] + 0.6), (appr[0], appr[1] + 0.25), "plan needs a decision", dy=0.32, dx=-0.15)
    ar((appr[0] + 0.8, appr[1]), (res[0] + 0.8, res[1] + res[3]), "approve", dx=0.0)
    ar((res[0], res[1] + 0.4), (work[0] + work[2], work[1] + 0.2), "back to the chat", dy=-0.28, dx=0.0)
    ar((appr[0], appr[1] + 0.55), (work[0] + work[2] - 0.1, work[1] + work[3]), "reject", dy=0.18, dx=-0.15) if False else None
    ar((fol[0] + fol[2], fol[1] + 0.4), (work[0], work[1] + 0.6), "choose a folder", dy=0.3)
    
    for nd in (fol, kn, st):
        pass
    ax.text(3.35, 0.02, "Folders, What it knows and Settings are reachable at any time and are not part of the request path.", fontsize=7.0, color=GREY, ha="center", va="center")
    fig.savefig(os.path.join(OUT, "fig_nav.pdf"), transparent=True); plt.close(fig); print("fig_nav")


if __name__ == "__main__":
    fig_er(); fig_class(); fig_nav()
