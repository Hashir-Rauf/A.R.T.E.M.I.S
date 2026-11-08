"""The owner's controls for remote access, shown in Settings.

The page asks for this section inside a try/except, so with the package deleted the
Settings tab simply has no such section and nothing else changes.
"""

from __future__ import annotations

import html
from typing import Any, Callable

from artemis.data.store import Store
from artemis.remote.bridge import RemoteBridge
from artemis.remote.plane import RemotePlane
from artemis.remote.relay import Relay


def _note(text: str, warn: bool = False) -> str:
    return f'<div class="a-msg{" warn" if warn else ""}">{html.escape(text)}</div>'


def build_remote_section(gr: Any, store: Store, panel_factory: Callable[[], Any]) -> RemotePlane:
    """Add the section to the current Blocks page. Returns the plane, for the host to run."""
    relay = Relay()
    plane = RemotePlane(store, relay)
    bridge = RemoteBridge(store, panel_factory)
    plane.attach(bridge.handle)
    plane.resume()

    def device_choices():
        return [(f"{d.name}" + (" (removed)" if d.revoked else ""), d.id) for d in plane.devices() if not d.revoked]

    def waiting_choices():
        return [(f"{p.name}  ·  safety number {p.safety_number}", p.pairing_id) for p in plane.pending()]

    def folder_choices():
        return [(r["name"], int(r["id"])) for r in store.list_workspaces()]

    with gr.Accordion("Remote access (optional)", open=False):
        gr.HTML(
            '<div class="a-sub">Control ARTEMIS from your phone. It is off until you press '
            "Start. Messages are scrambled on your phone and only unscrambled here, so the "
            "relay in between cannot read them. A device can use only the folders you tick "
            "below, and it can never do more than you can do here. "
            "<b>No relay service is connected in this build yet</b>, so a real phone cannot "
            "connect; these controls are the host side of that feature.</div>"
        )
        start_btn = gr.Button("Start pairing a device")
        code_html = gr.HTML()
        with gr.Row():
            waiting = gr.Dropdown(label="Waiting for you to confirm", choices=waiting_choices(), scale=4)
            check_btn = gr.Button("Check again", scale=1)
            confirm_btn = gr.Button("Confirm: this is my device", variant="primary", scale=2)
            decline_btn = gr.Button("Decline", scale=1)
        with gr.Row():
            devices = gr.Dropdown(label="Paired devices", choices=device_choices(), scale=5)
            remove_btn = gr.Button("Remove device", scale=1)
        folders = gr.CheckboxGroup(
            label="Folders a paired device may use (none by default)",
            choices=folder_choices(),
            value=sorted(bridge.allowed_workspaces()),
        )
        outward = gr.Checkbox(
            label="Emails and web searches must be approved on this computer, never from a device",
            value=bridge.outward_stays_local,
        )
        note = gr.HTML()

    def start():
        offer = plane.begin_pairing()
        return (
            f'<div class="a-msg">Type this code on your device: <b style="font-size:1.4em;letter-spacing:.15em">'
            f"{html.escape(offer.code)}</b><br>It works once and expires in {offer.expires_in // 60} minutes. "
            "Then press Check again, and confirm only if the safety number matches the one on your device.</div>"
        )

    def check():
        return gr.update(choices=waiting_choices()), gr.update(choices=device_choices())

    def confirm(pairing_id):
        if not pairing_id:
            return _note("Choose the device first.", True), *check()
        try:
            device = plane.confirm(pairing_id)
        except LookupError as exc:
            return _note(str(exc), True), *check()
        return _note(f"{device.name} is paired. Tick the folders it may use."), *check()

    def decline(pairing_id):
        if pairing_id:
            plane.reject(pairing_id)
        return _note("Declined. Nothing was paired."), *check()

    def remove(device_id):
        if not device_id:
            return _note("Choose a device first.", True), *check()
        plane.revoke(device_id)
        return _note("Removed. That device can no longer connect."), *check()

    def save_folders(ids):
        chosen = {int(i) for i in (ids or [])}
        for row in store.list_workspaces():
            bridge.allow_workspace(int(row["id"]), int(row["id"]) in chosen)
        return _note("Saved.")

    start_btn.click(start, outputs=code_html)
    check_btn.click(check, outputs=[waiting, devices])
    confirm_btn.click(confirm, inputs=waiting, outputs=[note, waiting, devices])
    decline_btn.click(decline, inputs=waiting, outputs=[note, waiting, devices])
    remove_btn.click(remove, inputs=devices, outputs=[note, waiting, devices])
    folders.change(save_folders, inputs=folders, outputs=note)
    outward.change(lambda on: bridge.set_outward_stays_local(bool(on)), inputs=outward)
    return plane
