# Desktop build

Packages the app as a Windows program: a launcher exe that runs the backend
locally and shows the app in its own window (Edge WebView2), plus an installer.

## Install

1. Build the installer (below), or use the last one in `dist\installer\` (gitignored,
   so your editor may hide it).
2. Run `dist\installer\PhDProgramFinder-<version>-setup.exe`. It installs for your
   user only, with no admin prompt. Optionally tick "Create a desktop shortcut".
3. Start **PhD Program Finder** from the Start menu or desktop shortcut.

Uninstall from Settings → Apps. Your data folder is kept.
Inno Setup is only needed to build the installer, not to install or run the app.

## Build

```powershell
.\build.ps1                 # export frontend → PyInstaller → smoke test → installer
.\build.ps1 -SkipFrontend   # Python-only changes: reuse the last frontend export
.\build.ps1 -SkipInstaller  # app folder only (no Inno Setup needed)
```

Needs the project `.venv` (with `requirements.txt`) and, for the installer,
Inno Setup 6 (`winget install -e --id JRSoftware.InnoSetup --scope user`).
The script installs `requirements-build.txt` itself.

Outputs:

- `dist\PhDProgramFinder\PhDProgramFinder.exe` (the app folder; runs as-is)
- `dist\installer\PhDProgramFinder-<version>-setup.exe`

## Releasing a new version

Bump `version` in `app_info.json`, run `.\build.ps1`, run the new setup exe.
It upgrades in place; your data is untouched.

## How it works

- `app_info.json`: name, version, publisher, port, installer id. Read by the
  launcher, the PyInstaller spec, and the installer. Keep `app_id` fixed
  forever (it's how upgrades find the existing install).
- The frontend is exported with its backend URL fixed to `127.0.0.1:<port>`
  (only reachable from this computer). Changing `port` requires a full build.
- `launcher.py` serves the static frontend and the Reflex backend on that port
  with uvicorn, then opens the window. Closing the window stops the server. If
  the app is already running, a second launch just opens another window.
- `installer.iss` installs per user to `%LOCALAPPDATA%\Programs\PhD Program Finder`
  (no admin prompt), with Start menu and optional desktop shortcuts.

## Where things live (installed app)

| What | Where |
| --- | --- |
| Program | `%LOCALAPPDATA%\Programs\PhD Program Finder` |
| Database, saved pages | `%LOCALAPPDATA%\PhD Program Finder` (Start menu has a shortcut) |
| Log | `%LOCALAPPDATA%\PhD Program Finder\logs\app.log` |
| Custom extractors | `%LOCALAPPDATA%\PhD Program Finder\extractors\` |

Set `DATA_DIR` to use a different data folder. The installed app's data is
separate from the dev server's `data\` folder in the project.

To use your own extractor in the installed app, put `my_model.py` in the
`extractors` folder and set `PROGRAM_EXTRACTOR=my_model:Model` (user
environment variable). The bundle only includes this project's dependencies, so
an extractor that needs extra packages (e.g. torch) must run outside it, for
example by calling a local model server over HTTP.

## Troubleshooting

`PhDProgramFinder.exe --server-only` runs the server without a window on
`http://127.0.0.1:<port>`; check `logs\app.log` in the data folder.
