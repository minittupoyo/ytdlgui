import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "main.py"
SPEC = importlib.util.spec_from_file_location("ytdlgui_app", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


def test_settings_path_uses_windows_appdata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(app.platform, "system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert app.settings_path() == tmp_path / "ytdlgui" / "settings.json"


def test_settings_path_uses_macos_application_support(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(app.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(app.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "ignored"))

    assert app.settings_path() == (
        tmp_path / "Library" / "Application Support" / "ytdlgui" / "settings.json"
    )


def test_load_settings_migrates_legacy_macos_file(monkeypatch, tmp_path: Path):
    current = tmp_path / "Library" / "Application Support" / "ytdlgui" / "settings.json"
    legacy = tmp_path / "AppData" / "Roaming" / "ytdlgui" / "settings.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"format": "mp3"}), encoding="utf-8")
    monkeypatch.setattr(app.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(app, "settings_path", lambda: current)
    monkeypatch.setattr(app, "legacy_settings_path", lambda: legacy)

    assert app.load_settings() == {"format": "mp3"}
    assert json.loads(current.read_text(encoding="utf-8")) == {"format": "mp3"}


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


def test_find_tool_prefers_installed_tools_directory(monkeypatch, tmp_path: Path):
    tool = tmp_path / "tools" / "ffmpeg.exe"
    tool.parent.mkdir()
    tool.touch()
    monkeypatch.setattr(app.platform, "system", lambda: "Windows")
    monkeypatch.setattr(app, "install_dir", lambda: tmp_path)
    monkeypatch.setattr(app.shutil, "which", lambda command: "from-path")

    assert app.find_tool("ffmpeg") == str(tool)


def test_subprocess_env_prepends_installed_tools(monkeypatch, tmp_path: Path):
    tools = tmp_path / "tools"
    tools.mkdir()
    monkeypatch.setattr(app, "install_dir", lambda: tmp_path)
    monkeypatch.setenv("PATH", "system-path")
    monkeypatch.setenv("PYTHONHOME", "ignored")

    env = app.subprocess_env()

    assert env["PATH"] == f"{tools}{app.os.pathsep}system-path"
    assert "PYTHONHOME" not in env
    assert env["PYTHONIOENCODING"] == "utf-8"
