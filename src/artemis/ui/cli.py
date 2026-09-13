"""Command line control surface.

A client of the core, never a way around it. In particular the CLI resolves paths
through the Workspace Broker like everything else, so `artemis resolve` is a way
to observe the boundary rather than a way to step over it.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from artemis.core.broker import Operation, WorkspaceBroker
from artemis.core.disclosure import DisclosurePanel
from artemis.core.errors import BoundaryRefusal, WorkspaceError
from artemis.core.indexer import Indexer
from artemis.core.workspace import WorkspaceManager
from artemis.data import paths
from artemis.data.store import Store

app = typer.Typer(
    add_completion=False,
    help="ARTEMIS: a bounded, opt-in desktop assistant.",
)
workspace_app = typer.Typer(help="Grant, list and revoke workspaces.")
app.add_typer(workspace_app, name="workspace")

console = Console()


def _store() -> Store:
    return Store()


@workspace_app.command("add")
def workspace_add(
    folder: Path = typer.Argument(..., help="Folder to opt in."),
    name: str = typer.Option(None, "--name", help="Display name for the workspace."),
    read_only: bool = typer.Option(False, "--read-only", help="Grant read access only."),
    allow_cloud: bool = typer.Option(
        False, "--allow-cloud", help="Permit cloud model calls for this workspace."
    ),
) -> None:
    """Opt a folder in as a workspace, then index it."""
    with _store() as store:
        manager = WorkspaceManager(store)
        try:
            ws = manager.grant(
                folder,
                name=name,
                permission="read_only" if read_only else "read_write",
                cloud_policy="cloud_allowed" if allow_cloud else "local_only",
            )
        except WorkspaceError as exc:
            console.print(f"[red]Cannot grant:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        indexer = Indexer(store, WorkspaceBroker(store))
        count = indexer.scan(ws.id)

    console.print(
        f"[green]Granted[/green] workspace [bold]{ws.name}[/bold] "
        f"(id {ws.id}) at {ws.root}"
    )
    console.print(f"Indexed {count} file(s). Permission: {ws.permission}.")


@workspace_app.command("list")
def workspace_list() -> None:
    """List every granted workspace."""
    with _store() as store:
        rows = WorkspaceManager(store).list()
        counts = {w.id: store.count_files(w.id) for w in rows}

    if not rows:
        console.print("No workspaces granted. ARTEMIS can see nothing.")
        return

    table = Table(title="Granted workspaces")
    for column in ("ID", "Name", "Root", "Permission", "Cloud", "Files"):
        table.add_column(column)
    for w in rows:
        table.add_row(
            str(w.id), w.name, str(w.root), w.permission, w.cloud_policy,
            str(counts[w.id]),
        )
    console.print(table)


@workspace_app.command("remove")
def workspace_remove(
    workspace_id: int = typer.Argument(..., help="Workspace id to revoke."),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt."),
) -> None:
    """Revoke a grant. Removes what ARTEMIS knows, never the user's files."""
    with _store() as store:
        manager = WorkspaceManager(store)
        ws = manager.get(workspace_id)
        if ws is None:
            console.print(f"[red]No workspace with id {workspace_id}.[/red]")
            raise typer.Exit(code=1)
        if not yes:
            confirm = typer.confirm(
                f"Revoke '{ws.name}' and delete everything ARTEMIS holds about it?"
            )
            if not confirm:
                console.print("Left unchanged.")
                return
        manager.revoke(workspace_id)
    console.print(
        f"[green]Revoked.[/green] Your files at {ws.root} were not touched."
    )


@app.command("scan")
def scan(workspace_id: int = typer.Argument(..., help="Workspace to re-index.")) -> None:
    """Re-index a workspace from disk."""
    with _store() as store:
        indexer = Indexer(store, WorkspaceBroker(store))
        count = indexer.scan(workspace_id)
    console.print(f"Indexed {count} file(s).")


@app.command("resolve")
def resolve(
    workspace_id: int = typer.Argument(..., help="Workspace to resolve against."),
    reference: str = typer.Argument(..., help="Workspace-relative reference."),
    write: bool = typer.Option(False, "--write", help="Resolve for writing."),
) -> None:
    """Ask the broker to resolve a reference, and show what it decides."""
    with _store() as store:
        broker = WorkspaceBroker(store)
        try:
            resolved = broker.resolve(
                workspace_id,
                reference,
                Operation.WRITE if write else Operation.READ,
            )
        except BoundaryRefusal as exc:
            console.print(f"[red]Refused[/red] ({exc.reason.value}): {exc.detail}")
            console.print("[dim]The refusal was written to the audit log.[/dim]")
            raise typer.Exit(code=1) from exc
    console.print(f"[green]Resolved[/green] {resolved.rel_path}")
    console.print(f"  {resolved.path}")


@app.command("knows")
def knows(
    workspace_id: int = typer.Option(
        None, "--workspace", help="Limit to one workspace."
    ),
) -> None:
    """Show everything ARTEMIS currently holds."""
    with _store() as store:
        snapshot = DisclosurePanel(store).snapshot(workspace_id)
        usage = DisclosurePanel.disk_usage()

    table = Table(title="What ARTEMIS Knows")
    table.add_column("Holds")
    table.add_column("Count", justify="right")
    table.add_column("Deletable")
    for row in snapshot.rows:
        table.add_row(row.label, str(row.count), "yes" if row.deletable else "no")
    console.print(table)

    for row in snapshot.rows:
        if row.detail:
            console.print(f"\n[bold]{row.label}[/bold]")
            for item in row.detail:
                console.print(f"  {item}")

    console.print(f"\nStore: {paths.artemis_home()}  ({usage / 1024:.1f} KiB)")


@app.command("forget")
def forget(
    workspace_id: int = typer.Argument(..., help="Workspace the file belongs to."),
    rel_path: str = typer.Argument(..., help="Workspace-relative path to forget."),
) -> None:
    """Drop one file from the index. The file itself is left alone."""
    with _store() as store:
        DisclosurePanel(store).forget_file(workspace_id, rel_path)
    console.print(f"[green]Forgotten:[/green] {rel_path} (the file is untouched)")


@app.command("panel")
def panel() -> None:
    """Open the "What ARTEMIS Knows" desktop window."""
    try:
        from artemis.ui.panel import launch
    except ImportError as exc:  # pragma: no cover - depends on the install
        console.print(f"[red]The panel needs PySide6:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=launch())


@app.command("web")
def web(
    port: int = typer.Option(None, "--port", help="Port to serve on."),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Do not open a browser tab automatically."
    ),
) -> None:
    """Open the ARTEMIS web interface, served on this machine only."""
    try:
        from artemis.ui.web import launch
    except ImportError as exc:  # pragma: no cover - depends on the install
        console.print(f"[red]The web interface needs Gradio:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print("[cyan]Starting ARTEMIS...[/cyan]  (press Ctrl+C to stop)")
    launch(inbrowser=not no_browser, port=port)


@app.command("verify")
def verify() -> None:
    """Check that the audit log's hash chain is intact."""
    with _store() as store:
        ok = store.verify_audit_chain()
    if ok:
        console.print("[green]Audit chain intact.[/green]")
    else:
        console.print("[red]Audit chain broken: an entry was altered or removed.[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
