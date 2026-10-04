"""Capability services: the nine features.

Each service is a plugin behind the uniform tool contract the dispatcher
defines. None touches the filesystem, the network or the database directly:
paths arrive already resolved through the Workspace Broker, so a service cannot
reach outside a grant even by accident (Architecture Table 2, component 12).

Sprint 5 ships the first three, which exercise the read and reversible tiers
end to end:

* `resume`    F1  Pick up where you left off  - T0, no model involvement
* `tidy`      F2  Tidy up a folder            - T1, moves and groups only
* `patterns`  F4  Notice a repeated task      - may propose, never install
"""
