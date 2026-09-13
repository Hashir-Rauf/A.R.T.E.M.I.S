"""The ARTEMIS window: what it knows, and how to take it away.

Written for someone who has never read the architecture document. Three rules
shaped it, and they are worth keeping if this file is edited:

1. **No hidden preconditions.** An earlier version had a single "Revoke" button
   that acted on whichever workspace was selected in a list. Adding a workspace
   left the selector on "All workspaces", so the button showed an explanatory
   dialogue instead of doing anything, and it read as broken. Every action now
   lives on the card for the thing it acts on, so there is nothing to select
   first and nothing to guess.

2. **Plain words.** The person using this did not choose the vocabulary in the
   architecture document. "Folders ARTEMIS can see", not "granted workspaces".
   "Forget", never "delete", because ARTEMIS deleting the user's files is exactly
   the fear the design exists to answer.

3. **State the limit, not just the feature.** Empty states say what ARTEMIS
   cannot do, because that is the reassuring part. Confirmations say what will
   survive, not only what will go.

The window holds no state the backend does not own: every action ends in
`refresh()`, which re-queries the stores.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from artemis.core.broker import WorkspaceBroker
from artemis.core.disclosure import DisclosurePanel
from artemis.core.errors import WorkspaceError
from artemis.core.indexer import Indexer
from artemis.core.workspace import WorkspaceManager
from artemis.data import paths
from artemis.data.store import Store

# Kept for callers and tests written against the previous layout.
ALL_WORKSPACES = -1

STYLE = """
QWidget { font-size: 10pt; }
QLabel#Title { font-size: 17pt; font-weight: 600; }
QLabel#Subtitle { color: #555; }
QLabel#SectionHeading { font-size: 12pt; font-weight: 600; }
QLabel#CardName { font-size: 12pt; font-weight: 600; }
QLabel#CardPath { color: #555; }
QLabel#Muted { color: #666; }
QFrame#Card {
    background: #ffffff;
    border: 1px solid #d8d8d8;
    border-radius: 6px;
}
QFrame#EmptyCard {
    background: #fbfbfb;
    border: 1px dashed #c8c8c8;
    border-radius: 6px;
}
QPushButton { padding: 6px 14px; }
QPushButton#Primary { font-weight: 600; padding: 8px 18px; }
QPushButton#Danger { color: #a4262c; }
"""


def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #e2e2e2;")
    return line


class WorkspaceCard(QFrame):
    """One granted folder, with its own actions attached to it.

    Putting the actions on the card is the fix for the selection trap: a button
    here can only ever mean "this folder", so there is no prior selection step
    for the user to miss.
    """

    def __init__(self, window: KnowledgeWindow, workspace, file_count: int) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._window = window
        self._workspace = workspace

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        name = QLabel(workspace.name)
        name.setObjectName("CardName")
        layout.addWidget(name)

        path = QLabel(str(workspace.root))
        path.setObjectName("CardPath")
        path.setWordWrap(True)
        layout.addWidget(path)

        access = (
            "can read files here"
            if workspace.permission == "read_only"
            else "can read and change files here, with your approval"
        )
        summary = QLabel(
            f"{file_count} file{'s' if file_count != 1 else ''} known  ·  ARTEMIS {access}"
        )
        summary.setObjectName("Muted")
        layout.addWidget(summary)

        buttons = QHBoxLayout()
        show = QPushButton("Show files")
        show.setToolTip("List every file ARTEMIS knows about in this folder.")
        show.clicked.connect(lambda: window.show_files_for(workspace.id))

        recheck = QPushButton("Check for changes")
        recheck.setToolTip("Look for files added, changed or removed since last time.")
        recheck.clicked.connect(lambda: window.rescan_workspace(workspace.id))

        forget = QPushButton("Forget this folder")
        forget.setObjectName("Danger")
        forget.setToolTip("ARTEMIS forgets this folder. Your files are not deleted.")
        forget.clicked.connect(lambda: window.confirm_forget_workspace(workspace.id))

        for b in (show, recheck, forget):
            buttons.addWidget(b)
        buttons.addStretch(1)
        layout.addLayout(buttons)


class KnowledgeWindow(QMainWindow):
    """Shows everything ARTEMIS holds, and lets the user take any of it away."""

    def __init__(self, store: Store) -> None:
        super().__init__()
        self._store = store
        self._manager = WorkspaceManager(store)
        self._broker = WorkspaceBroker(store)
        self._indexer = Indexer(store, self._broker)
        self._panel = DisclosurePanel(store)
        self._focus_workspace: int | None = None
        self._rows: list = []

        self.setWindowTitle("ARTEMIS - What it knows about you")
        self.setStyleSheet(STYLE)
        self.resize(980, 680)
        self._build()
        self.refresh()

    # -- construction ------------------------------------------------------

    def _build(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 18, 22, 14)
        outer.setSpacing(12)

        title = QLabel("What ARTEMIS knows about you")
        title.setObjectName("Title")
        outer.addWidget(title)

        subtitle = QLabel(
            "ARTEMIS can only see folders you add here. Everything it knows is "
            "stored on this computer and has not been sent anywhere. You can take "
            "any of it away at any time."
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        outer.addWidget(_hline())

        add_row = QHBoxLayout()
        heading = QLabel("Folders ARTEMIS can see")
        heading.setObjectName("SectionHeading")
        add_row.addWidget(heading)
        add_row.addStretch(1)

        self.add_button = QPushButton("Add a folder")
        self.add_button.setObjectName("Primary")
        self.add_button.setToolTip("Choose a folder for ARTEMIS to look at.")
        self.add_button.clicked.connect(self.on_add_workspace)
        add_row.addWidget(self.add_button)
        outer.addLayout(add_row)

        # Cards, one per granted folder.
        self.cards_area = QScrollArea()
        self.cards_area.setWidgetResizable(True)
        self.cards_area.setFrameShape(QFrame.Shape.NoFrame)
        self.cards_host = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch(1)
        self.cards_area.setWidget(self.cards_host)
        outer.addWidget(self.cards_area, stretch=3)

        # File list, hidden until asked for. Volunteering a wall of filenames
        # to someone who just wanted to add a folder is not helpful.
        self.files_panel = QWidget()
        files_layout = QVBoxLayout(self.files_panel)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(6)

        files_header = QHBoxLayout()
        self.files_heading = QLabel("Files ARTEMIS knows about")
        self.files_heading.setObjectName("SectionHeading")
        files_header.addWidget(self.files_heading)
        files_header.addStretch(1)
        self.forget_file_button = QPushButton("Forget selected file")
        self.forget_file_button.setToolTip(
            "ARTEMIS forgets this file. The file itself stays on your computer."
        )
        self.forget_file_button.clicked.connect(self.on_forget_item)
        self.forget_file_button.setEnabled(False)
        files_header.addWidget(self.forget_file_button)
        hide = QPushButton("Hide")
        hide.clicked.connect(self.hide_files)
        files_header.addWidget(hide)
        files_layout.addLayout(files_header)

        self.detail_list = QListWidget()
        self.detail_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.detail_list.currentRowChanged.connect(
            lambda row: self.forget_file_button.setEnabled(row >= 0)
        )
        files_layout.addWidget(self.detail_list)
        self.files_panel.setVisible(False)
        outer.addWidget(self.files_panel, stretch=2)

        outer.addWidget(_hline())

        # The summary line, in plain words rather than a table of internals.
        self.summary_label = QLabel()
        self.summary_label.setObjectName("Muted")
        self.summary_label.setWordWrap(True)
        outer.addWidget(self.summary_label)

        footer = QHBoxLayout()
        self.details_button = QPushButton("Show technical details")
        self.details_button.setToolTip("Everything ARTEMIS stores, item by item.")
        self.details_button.clicked.connect(self.show_technical_details)
        footer.addWidget(self.details_button)

        self.erase_button = QPushButton("Erase everything ARTEMIS knows")
        self.erase_button.setObjectName("Danger")
        self.erase_button.setToolTip(
            "Remove everything ARTEMIS has stored. Your own files are not deleted."
        )
        self.erase_button.clicked.connect(self.confirm_erase_everything)
        footer.addWidget(self.erase_button)
        footer.addStretch(1)
        outer.addLayout(footer)

        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())

    # -- data --------------------------------------------------------------

    def refresh(self) -> None:
        """Re-read every store. The window never caches what it shows."""
        # Rebuild the cards. Taking a widget out of a layout does not unparent
        # it, so without setParent(None) the old cards stay children of the
        # host, keep rendering in the dead space below the list, and accumulate
        # on every refresh. deleteLater alone is not enough because the widget
        # survives until the event loop next runs, which may be after the next
        # repaint.
        while self.cards_layout.count() > 1:  # keep the trailing stretch
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        workspaces = self._manager.list()
        if workspaces:
            for ws in workspaces:
                card = WorkspaceCard(self, ws, self._store.count_files(ws.id))
                self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        else:
            self.cards_layout.insertWidget(0, self._empty_card())

        # The focused folder may have just been forgotten.
        if self._focus_workspace is not None and not any(
            w.id == self._focus_workspace for w in workspaces
        ):
            self.hide_files()

        self._rows = self._panel.snapshot(self._focus_workspace).rows
        if self.files_panel.isVisible() and self._focus_workspace is not None:
            self._populate_files(self._focus_workspace)

        self._update_summary(workspaces)

    def _empty_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("EmptyCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 22, 18, 22)
        headline = QLabel("ARTEMIS cannot see anything on this computer.")
        headline.setObjectName("CardName")
        headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel(
            "It stays that way until you add a folder. Even then, it only ever "
            "looks inside the folders you choose."
        )
        body.setObjectName("Muted")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(headline)
        layout.addWidget(body)
        return card

    def _update_summary(self, workspaces: list) -> None:
        rows = {r.label: r for r in self._rows}
        files = rows["Files indexed"].count if "Files indexed" in rows else 0
        actions = rows["Actions recorded"].count if "Actions recorded" in rows else 0
        usage = DisclosurePanel.disk_usage() / 1024

        if not workspaces:
            self.summary_label.setText(
                "Nothing stored. ARTEMIS has no access to any folder."
            )
        else:
            self.summary_label.setText(
                f"ARTEMIS knows about {files} file"
                f"{'s' if files != 1 else ''} in {len(workspaces)} folder"
                f"{'s' if len(workspaces) != 1 else ''}, and has recorded {actions} "
                f"action{'s' if actions != 1 else ''} it took. "
                f"All of it is on this computer only ({usage:.0f} KB)."
            )
        self.statusBar().showMessage(f"Stored in {paths.artemis_home()}")

    def _populate_files(self, workspace_id: int) -> None:
        self.detail_list.clear()
        for row in self._store.list_files(workspace_id):
            self.detail_list.addItem(row["rel_path"])
        ws = self._manager.get(workspace_id)
        if ws is not None:
            self.files_heading.setText(f"Files ARTEMIS knows about in '{ws.name}'")
        self.forget_file_button.setEnabled(self.detail_list.currentRow() >= 0)

    # -- actions -----------------------------------------------------------

    def on_add_workspace(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Choose a folder for ARTEMIS to look at"
        )
        if not folder:
            return
        self.grant_folder(Path(folder))

    def grant_folder(self, folder: Path, name: str | None = None) -> bool:
        """Add a folder and index it. Separated so tests can call it directly."""
        try:
            ws = self._manager.grant(folder, name=name)
        except WorkspaceError as exc:
            QMessageBox.warning(self, "Cannot add that folder", str(exc))
            return False
        count = self._indexer.scan(ws.id)
        self.refresh()
        self.statusBar().showMessage(
            f"Added '{ws.name}'. ARTEMIS now knows about {count} file"
            f"{'s' if count != 1 else ''} in it."
        )
        return True

    def show_files_for(self, workspace_id: int) -> None:
        self._focus_workspace = workspace_id
        self._rows = self._panel.snapshot(workspace_id).rows
        self._populate_files(workspace_id)
        self.files_panel.setVisible(True)

    def hide_files(self) -> None:
        self._focus_workspace = None
        self.files_panel.setVisible(False)
        self.detail_list.clear()
        self.forget_file_button.setEnabled(False)

    def rescan_workspace(self, workspace_id: int) -> None:
        before = self._store.count_files(workspace_id)
        after = self._indexer.scan(workspace_id)
        self.refresh()
        if after == before:
            message = "Nothing has changed since last time."
        else:
            difference = after - before
            direction = "now knows about" if difference > 0 else "has forgotten"
            message = (
                f"Checked. ARTEMIS {direction} {abs(difference)} more file"
                f"{'s' if abs(difference) != 1 else ''}."
            )
        self.statusBar().showMessage(message)

    def confirm_forget_workspace(self, workspace_id: int) -> None:
        ws = self._manager.get(workspace_id)
        if ws is None:
            return
        count = self._store.count_files(workspace_id)
        box = QMessageBox(self)
        box.setWindowTitle("Forget this folder?")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(f"Make ARTEMIS forget '{ws.name}'?")
        box.setInformativeText(
            f"It will forget the {count} file{'s' if count != 1 else ''} it knows "
            f"about here and lose access to the folder.\n\n"
            f"Your files in {ws.root} are NOT deleted. Nothing in that folder "
            f"changes."
        )
        forget = box.addButton("Forget it", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Keep it", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(forget)
        box.exec()
        if box.clickedButton() is forget:
            self.revoke_workspace(workspace_id)

    def revoke_workspace(self, workspace_id: int) -> None:
        """Forget a folder. Separated so tests can call it without a dialogue."""
        ws = self._manager.get(workspace_id)
        name = ws.name if ws else "folder"
        if self._focus_workspace == workspace_id:
            self.hide_files()
        self._manager.revoke(workspace_id)
        self.refresh()
        self.statusBar().showMessage(
            f"ARTEMIS has forgotten '{name}'. Your files were not touched."
        )

    def on_forget_item(self) -> None:
        item = self.detail_list.currentItem()
        if item is None or self._focus_workspace is None:
            return
        self.forget_file(self._focus_workspace, item.text())

    def forget_file(self, workspace_id: int, rel_path: str) -> None:
        """Drop one file from the index. The file on disk is left alone."""
        self._panel.forget_file(workspace_id, rel_path)
        self.refresh()
        self.statusBar().showMessage(
            f"ARTEMIS has forgotten '{rel_path}'. The file itself is untouched."
        )

    def confirm_erase_everything(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Erase everything?")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText("Make ARTEMIS forget everything?")
        box.setInformativeText(
            "Every folder, every file it knows about, and its record of what it "
            "did will be erased.\n\nNone of your own files are deleted."
        )
        erase = box.addButton("Erase everything", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is erase:
            self.erase_everything()

    def erase_everything(self) -> None:
        """Forget every folder. Separated so tests can call it directly."""
        self.hide_files()
        for ws in self._manager.list():
            self._manager.revoke(ws.id)
        self.refresh()
        self.statusBar().showMessage(
            "ARTEMIS has forgotten everything. Your files were not touched."
        )

    def show_technical_details(self) -> None:
        """The full store breakdown, for anyone who wants to audit it."""
        rows = self._panel.snapshot(self._focus_workspace).rows
        lines = []
        for row in rows:
            deletable = "" if row.deletable else "   (kept as a permanent record)"
            lines.append(f"{row.label}: {row.count}{deletable}")
        box = QMessageBox(self)
        box.setWindowTitle("Technical details")
        box.setText("Everything ARTEMIS is storing")
        box.setInformativeText("\n".join(lines))
        box.setDetailedText(f"Stored in: {paths.artemis_home()}")
        box.exec()

    # -- compatibility -----------------------------------------------------

    def selected_workspace_id(self) -> int:
        """The folder the file list is showing, or ALL_WORKSPACES for none.

        Retained because the previous layout exposed it; actions no longer
        depend on a selection, which is what made this concept a trap.
        """
        return self._focus_workspace if self._focus_workspace is not None else ALL_WORKSPACES


def launch() -> int:
    """Open the window. Returns the Qt exit code."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ARTEMIS")
    font = QFont()
    font.setPointSize(10)
    app.setFont(font)
    store = Store()
    window = KnowledgeWindow(store)
    window.show()
    try:
        return app.exec()
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(launch())
