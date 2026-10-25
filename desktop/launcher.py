"""Desktop launcher: runs the app's backend locally and shows it in a native window.

The frontend is pre-built (`reflex export`) with the backend URL fixed to
127.0.0.1:<port> from app_info.json, and this process serves both the static
frontend and the Reflex backend on that port. Run from source with
`python desktop/launcher.py` after a build, or use the packaged exe.
"""

import json
import logging
import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
# Bundled files: the PyInstaller _internal folder, or the project root when run from source.
BUNDLE_DIR = Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parent.parent
INFO = json.loads((BUNDLE_DIR / "desktop" / "app_info.json").read_text(encoding="utf-8"))
APP_NAME = INFO["name"]
PORT = int(INFO["port"])
BASE_URL = f"http://127.0.0.1:{PORT}"
FRONTEND_DIR = BUNDLE_DIR / ".web" / "build" / "client"

# Where the user's data goes: DATA_DIR if set, else %LOCALAPPDATA%\<app name>.
DATA_DIR = Path(
    os.environ.get("DATA_DIR")
    or Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
).resolve()

# Paths the backend's own requests use; everything else is the static frontend.
BACKEND_PREFIXES = ("/_event", "/ping", "/_upload", "/_health", "/_all_routes", "/auth-codespace")


def _setup_environment() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "logs").mkdir(exist_ok=True)
    if FROZEN:
        # A windowed exe has no console; libraries that print would otherwise fail.
        log = open(DATA_DIR / "logs" / "app.log", "a", buffering=1, encoding="utf-8")
        sys.stdout = sys.stderr = log
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    os.environ["DATA_DIR"] = str(DATA_DIR)
    os.environ["REFLEX_ENV_MODE"] = "prod"
    # Use the pre-built frontend; never recompile. (Reflex reads internal settings with a "__" prefix.)
    os.environ["__REFLEX_SKIP_COMPILE"] = "1"
    os.environ["REFLEX_API_URL"] = BASE_URL
    os.environ["REFLEX_WEB_WORKDIR"] = str(BUNDLE_DIR / ".web")  # read-only: compiled page list
    os.environ["REFLEX_STATES_WORKDIR"] = str(DATA_DIR / "states")
    os.environ["REFLEX_DIR"] = str(DATA_DIR / "reflex")
    # Reflex's get_config() looks for rxconfig.py in the cwd only and silently falls back
    # to a default config, so run from the bundle; all writes are redirected above.
    os.chdir(BUNDLE_DIR)
    if str(BUNDLE_DIR) not in sys.path:
        sys.path.insert(0, str(BUNDLE_DIR))
    # Custom extractors (PROGRAM_EXTRACTOR=module:name) can be dropped in <data>\extractors.
    (DATA_DIR / "extractors").mkdir(exist_ok=True)
    sys.path.append(str(DATA_DIR / "extractors"))


class DesktopASGI:
    """Route backend paths and websockets to Reflex, and everything else to the static frontend."""

    def __init__(self, backend, frontend_dir: Path):
        from starlette.staticfiles import StaticFiles

        self.backend = backend
        self.frontend_dir = frontend_dir
        self.static = StaticFiles(directory=frontend_dir, html=True)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"].startswith(BACKEND_PREFIXES):
            await self.backend(scope, receive, send)
            return
        # Serve /add from add.html (the export writes one per page) instead of redirecting to /add/.
        page = scope["path"].strip("/")
        if page and "." not in page.rsplit("/", 1)[-1] and (self.frontend_dir / f"{page}.html").is_file():
            scope = {**scope, "path": f"/{page}.html"}
        await self.static(scope, receive, send)


def _port_in_use() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def _app_responding() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/ping", timeout=2) as resp:
            return resp.status == 200
    except OSError:
        return False


def _start_server():
    import uvicorn

    from app.app import app as reflex_app

    asgi = DesktopASGI(reflex_app(), FRONTEND_DIR)
    server = uvicorn.Server(
        uvicorn.Config(asgi, host="127.0.0.1", port=PORT, log_config=None, lifespan="on")
    )
    thread = threading.Thread(target=server.run, name="server", daemon=True)
    thread.start()
    return server, thread


def _wait_until_ready(timeout: float = 60.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _app_responding():
            return True
        time.sleep(0.25)
    return False


def _window_size(webview, preferred=(1360, 900), fraction=0.9) -> tuple[int, int]:
    """Preferred size, shrunk to fit the primary screen.

    pywebview reports screens in physical pixels but sizes windows in scaled
    (DPI-independent) pixels, so convert using Windows' display scale factor.
    """
    try:
        import ctypes

        scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100 or 1.0
        screen = webview.screens[0]
        max_w, max_h = screen.width / scale * fraction, screen.height / scale * fraction
    except Exception:  # noqa: BLE001 - fall back to the preferred size
        return preferred
    return int(min(preferred[0], max_w)), int(min(preferred[1], max_h))


LOADING_HTML = """<!doctype html><html><body style="font-family:Segoe UI,sans-serif;display:flex;
align-items:center;justify-content:center;height:100vh;margin:0;color:#374151;background:#f9fafb">
<p>Starting {name}…</p></body></html>"""

ERROR_HTML = """<!doctype html><html><body style="font-family:Segoe UI,sans-serif;padding:2rem;color:#374151">
<h2 style="color:#991b1b">{name} couldn't start</h2><p>{message}</p>
<p style="color:#6b7280">Log file: {log}</p></body></html>"""


def main() -> None:
    _setup_environment()
    if "--server-only" in sys.argv:
        # No window: serve on BASE_URL until killed (for testing and troubleshooting).
        server, thread = _start_server()
        logging.info("Server-only mode: %s (ready=%s)", BASE_URL, _wait_until_ready())
        thread.join()
        return
    import webview

    server = thread = None
    error = None
    if _port_in_use():
        if not _app_responding():
            error = f"Port {PORT} is being used by another program."
        # Otherwise the app is already running: just open another window onto it.
    else:
        try:
            server, thread = _start_server()
        except Exception as e:  # noqa: BLE001 - shown to the user, details in the log
            logging.exception("Server failed to start")
            error = f"{type(e).__name__}: {e}"

    width, height = _window_size(webview)
    window = webview.create_window(
        APP_NAME,
        html=LOADING_HTML.format(name=APP_NAME),
        width=width,
        height=height,
        min_size=(420, 600),
    )

    def show_app():
        message = error
        if message is None and not _wait_until_ready():
            message = "The app server did not respond in time."
        if message:
            window.load_html(
                ERROR_HTML.format(name=APP_NAME, message=message, log=DATA_DIR / "logs" / "app.log")
            )
        else:
            window.load_url(BASE_URL + "/")

    webview.start(show_app, private_mode=False, storage_path=str(DATA_DIR / "webview"))

    if server is not None:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
