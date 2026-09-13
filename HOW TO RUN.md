# How to run ARTEMIS

## Just open it

Double-click **`Start ARTEMIS.bat`** in this folder.

That is the whole thing. Nothing to type, no settings to change. The first time
it runs it may spend a minute installing what it needs, then the window opens.

Want it somewhere easier to reach? Right-click `Start ARTEMIS.bat` →
**Send to** → **Desktop (create shortcut)**. Then it is one double-click from
the desktop, and the shortcut can be renamed and given an icon like any other.

### If it does not open

The launcher explains the problem in the window it opens rather than closing
silently. The usual cause is Python not being installed: get it from
<https://www.python.org/downloads/> and tick **"Add python.exe to PATH"**
during setup.

## Using the window

ARTEMIS starts out able to see nothing at all. It stays that way until a folder
is added, and even then it only ever looks inside the folders chosen.

| To do this | Press |
| --- | --- |
| Let ARTEMIS see a folder | **Add a folder** |
| See what it knows about in one folder | **Show files** on that folder |
| Look for files added or removed since last time | **Check for changes** |
| Make it forget one file | **Show files**, pick the file, **Forget selected file** |
| Make it forget a whole folder | **Forget this folder** on that folder |
| Make it forget everything | **Erase everything ARTEMIS knows** |

**Forget never deletes.** Every one of those buttons removes what ARTEMIS
remembers. Files on the computer are left exactly where they are. The
confirmation box says so each time.

## For the command line, if preferred

```powershell
cd "E:\Education\FAST-NUCES\Final Year Project\A.R.T.E.M.I.S"
$env:PYTHONPATH = "src"
python -m artemis.ui.cli panel     # the window
python -m artemis.ui.cli --help    # everything else
```

Installing the project (`pip install -e .`) removes the need for `PYTHONPATH`
and provides `artemis` and `artemis-panel` as commands anywhere.

## Where ARTEMIS keeps what it knows

Everything lives in `.artemis` inside the user folder
(`C:\Users\<name>\.artemis`), on this computer only. Nothing is sent anywhere.
Setting the `ARTEMIS_HOME` environment variable points it elsewhere, which is
useful for trying things out without touching the real store.
