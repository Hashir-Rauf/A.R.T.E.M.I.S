# ARTEMIS source

Implementation of the architecture in `Docs/Architecture/ARTEMIS-Architecture.md`.
Sprint 2 (Workspace Foundation) is complete; no model is involved at this stage.

## Running it

```bash
pip install -e ".[dev]"      # or: set PYTHONPATH=src
pytest                        # 31 tests

artemis workspace add ./some-folder --name Thesis
artemis workspace list
artemis knows                 # what ARTEMIS currently holds
artemis resolve 1 notes/a.md  # ask the broker; refusals exit 1
artemis verify                # check the audit hash chain
artemis workspace remove 1    # revoke, cascades, leaves your files alone
```

`ARTEMIS_HOME` overrides the store location (default `~/.artemis/`). The tests set
it to a temporary directory, so they never touch a real store.

## Layout

| Path | Role |
| --- | --- |
| `artemis/core/broker.py` | Workspace Broker: the sole path resolver |
| `artemis/core/workspace.py` | Grant lifecycle |
| `artemis/core/indexer.py` | File index and the debounced watcher |
| `artemis/core/disclosure.py` | "What ARTEMIS Knows" panel |
| `artemis/core/errors.py` | Refusal types |
| `artemis/data/store.py` | SQLite system of record, hash-chained audit log |
| `artemis/data/paths.py` | Store locations |
| `artemis/ui/cli.py` | Command line surface |

## Two things worth knowing before you change this code

**Canonicalise before you check containment.** `broker.resolve` calls `realpath`
and only then tests whether the path is inside the grant. Reversing those two
steps accepts a symlink whose own path looks contained but whose target is not.
That ordering is the Sprint 2 stage gate, and `tests/test_broker.py` covers it.

**The store is reached from more than one thread.** The watcher flushes its
debounce buffer on a timer thread, so `Store` opens its connection with
`check_same_thread=False` and serialises every statement behind a lock. Use
`query`, `query_one` or `_write`; reaching into `_conn` directly bypasses the
lock. `tests/test_watcher.py` exists because the first version of the watcher was
silently broken this way while every other test passed.
