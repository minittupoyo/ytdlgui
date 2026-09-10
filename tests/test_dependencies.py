import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "main.py"
SPEC = importlib.util.spec_from_file_location("ytdlgui_app", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


def test_find_yt_dlp_prefers_bundled_binary(monkeypatch, tmp_path: Path):
    main_file = tmp_path / "main.py"
    binary_name = "yt-dlp.exe" if app.platform.system() == "Windows" else "yt-dlp"
    binary = tmp_path / "assets" / "bin" / binary_name
    binary.parent.mkdir(parents=True)
    binary.touch()

    monkeypatch.setattr(app, "managed_yt_dlp_path", lambda: tmp_path / "managed")
    monkeypatch.setattr(app, "__file__", str(main_file))
    monkeypatch.setattr(app.shutil, "which", lambda command: "from-path")

    assert app.find_yt_dlp() == str(binary)


def test_find_yt_dlp_falls_back_to_path(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(app, "managed_yt_dlp_path", lambda: tmp_path / "managed")
    monkeypatch.setattr(app, "__file__", str(tmp_path / "main.py"))
    monkeypatch.setattr(app.shutil, "which", lambda command: "from-path")

    assert app.find_yt_dlp() == "from-path"


def test_prepare_yt_dlp_copies_bundled_binary(monkeypatch, tmp_path: Path):
    bundled = tmp_path / "bundle" / app.yt_dlp_filename()
    managed = tmp_path / "managed" / app.yt_dlp_filename()
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"yt-dlp")

    monkeypatch.setattr(app, "bundled_yt_dlp_path", lambda: bundled)
    monkeypatch.setattr(app, "managed_yt_dlp_path", lambda: managed)

    assert app.prepare_yt_dlp() == str(managed)
    assert managed.read_bytes() == b"yt-dlp"
