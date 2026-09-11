import asyncio
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import flet as ft


def config_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base_dir = Path(
            os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        )
    elif system == "Darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        base_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base_dir / "ytdlgui"


def settings_path() -> Path:
    return config_dir() / "settings.json"


def legacy_settings_path() -> Path:
    return Path.home() / "AppData" / "Roaming" / "ytdlgui" / "settings.json"


def load_settings() -> dict[str, object]:
    current_path = settings_path()
    paths = [current_path]
    legacy_path = legacy_settings_path()
    if platform.system() != "Windows" and legacy_path != current_path:
        paths.append(legacy_path)

    for path in paths:
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(settings, dict):
            continue
        if path == legacy_path:
            save_settings(settings)
        return settings
    return {}


def save_settings(settings: dict[str, object]) -> None:
    try:
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def yt_dlp_filename() -> str:
    return "yt-dlp.exe" if platform.system() == "Windows" else "yt-dlp"


def bundled_yt_dlp_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "bin" / yt_dlp_filename()


def managed_yt_dlp_path() -> Path:
    return settings_path().parent / "bin" / yt_dlp_filename()


def install_dir() -> Path:
    """Return the directory containing the installed/portable executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_tool(command: str) -> str | None:
    """Find a bundled Windows tool before falling back to the system PATH."""
    filename = f"{command}.exe" if platform.system() == "Windows" else command
    bundled_path = install_dir() / "tools" / filename
    if bundled_path.is_file():
        return str(bundled_path)
    return shutil.which(command)


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env["PYTHONIOENCODING"] = "utf-8"
    tools_dir = install_dir() / "tools"
    if tools_dir.is_dir():
        env["PATH"] = os.pathsep.join(
            [str(tools_dir), env.get("PATH", "")]
        ).rstrip(os.pathsep)
    return env


def prepare_yt_dlp() -> str | None:
    managed_path = managed_yt_dlp_path()
    if managed_path.is_file():
        return str(managed_path)

    bundled_path = bundled_yt_dlp_path()
    if bundled_path.is_file():
        try:
            managed_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled_path, managed_path)
            managed_path.chmod(managed_path.stat().st_mode | 0o111)
            return str(managed_path)
        except OSError:
            return str(bundled_path)

    return shutil.which("yt-dlp")


def find_yt_dlp() -> str | None:
    managed_path = managed_yt_dlp_path()
    if managed_path.is_file():
        return str(managed_path)

    bundled_path = bundled_yt_dlp_path()
    if bundled_path.is_file():
        return str(bundled_path)
    return shutil.which("yt-dlp")


def check_dependencies() -> list[str]:
    missing: list[str] = []

    if find_yt_dlp() is None:
        missing.append("yt-dlp")
    for command in ("deno", "ffmpeg"):
        if find_tool(command) is None:
            missing.append(command)

    return missing


def fix_path_env() -> None:
    shell = os.environ.get("SHELL", "/bin/sh")
    try:
        result = subprocess.run(
            [shell, "-ilc", "printf '%s' \"$PATH\""],
            capture_output=True,
            text=True,
            check=True,
        )
        path = result.stdout.strip()
        if path:
            os.environ["PATH"] = path
    except (subprocess.CalledProcessError, OSError):
        pass


def main(page: ft.Page):

    async def check_yt_dlp_update() -> None:
        command = prepare_yt_dlp()
        if command is None:
            return

        status_text.value = "yt-dlpの更新を確認しています..."
        page.floating_action_button.disabled = True
        page.update()
        process: asyncio.subprocess.Process | None = None
        try:
            creationflags = 0
            if platform.system() == "Windows":
                creationflags = subprocess.CREATE_NO_WINDOW
            process = await asyncio.create_subprocess_exec(
                command,
                "-U",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                creationflags=creationflags,
            )
            output, _ = await asyncio.wait_for(process.communicate(), timeout=60)
            message = output.decode("utf-8", errors="replace").strip()
            if message:
                append_log(message)
            if process.returncode != 0:
                append_log(
                    "yt-dlpの更新確認に失敗しました。"
                    "現在のバージョンを使用します。"
                )
        except (OSError, asyncio.TimeoutError) as error:
            append_log(f"yt-dlpの更新確認に失敗しました: {error}")
            if (
                isinstance(error, asyncio.TimeoutError)
                and process is not None
                and process.returncode is None
            ):
                process.kill()
                await process.wait()
        finally:
            status_text.value = "準備完了"
            page.floating_action_button.disabled = False
            page.update()

    def init():
        settings = load_settings()
        default_output_path = os.path.join(os.path.expanduser("~"), "Downloads")
        output_path_field.value = settings.get("output_path", default_output_path)
        selected_format = settings.get("format", "mp4")
        if selected_format not in ("mp4", "mkv", "mp3", "aac", "flac"):
            selected_format = "mp4"
        format_dropdown.value = selected_format
        quality_dropdown.options = quality_options(selected_format)
        quality_values = {option.key for option in quality_dropdown.options}
        quality_dropdown.value = settings.get("quality", "auto")
        if quality_dropdown.value not in quality_values:
            quality_dropdown.value = "auto"
        filename_template.value = settings.get(
            "filename_template", "%(title)s.%(ext)s"
        )
        playlist_mode.value = bool(settings.get("playlist_mode", False))
        embed_thumbnail.value = bool(settings.get("embed_thumbnail", False))
        crop_thumbnail.value = bool(settings.get("crop_thumbnail", False))
        album_mode.visible = selected_format in ("mp3", "aac", "flac")
        album_mode.value = album_mode.visible and bool(settings.get("album_mode", False))
        if album_mode.value:
            playlist_mode.value = True
            playlist_mode.disabled = True
            update_filename_template()
        page.update()
        missing = check_dependencies()
        if missing:
            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text(
                        "必要なソフトが見つかりませんでした", weight=ft.FontWeight.BOLD
                    ),
                    content=ft.Text(
                        f"以下のコマンドが利用できません:\n\n" + "\n".join(missing)
                    ),
                    actions=[
                        ft.TextButton("閉じる", on_click=lambda e: page.pop_dialog())
                    ],
                )
            )

    async def handle_output_pick(e: ft.Event[ft.TextButton]):
        path = await ft.FilePicker().get_directory_path(
            dialog_title="保存先を選択", initial_directory=os.path.expanduser("~")
        )
        if path is not None:
            output_path_field.value = path
            output_path_field.update()
            persist_settings()

    def persist_settings() -> None:
        save_settings(
            {
                "output_path": output_path_field.value,
                "format": format_dropdown.value,
                "quality": quality_dropdown.value,
                "filename_template": filename_template.value,
                "playlist_mode": bool(playlist_mode.value),
                "album_mode": bool(album_mode.value),
                "embed_thumbnail": bool(embed_thumbnail.value),
                "crop_thumbnail": bool(crop_thumbnail.value),
            }
        )

    def handle_settings_change(e: ft.Event[ft.Control]) -> None:
        persist_settings()

    def build_args() -> list[str]:
        selected_format = format_dropdown.value or "mp4"
        selected_quality = quality_dropdown.value or "auto"
        args = [
            "--newline",
            "--color",
            "no_color",
            "-o",
            filename_template.value or "%(title)s.%(ext)s",
            "-P",
            os.path.abspath(output_path_field.value),
            "--progress-template",
            "download:[DOWNLOADING]\t%(progress._percent)s\t%(info.title)s",
        ]

        if platform.system() == "Windows":
            args.extend(["--encoding","utf-8"])

        if selected_format in ("mp4", "mkv"):
            height = {"4k": "2160", "2k": "1440", "1080p": "1080", "720p": "720"}
            selector = "bestvideo+bestaudio/best"
            if selected_quality != "auto":
                selector = (
                    f"bestvideo[height<={height[selected_quality]}]"
                    f"+bestaudio/best[height<={height[selected_quality]}]"
                )
            args.extend(["-f", selector, "--merge-output-format", selected_format])
        else:
            args.extend(["-x", "--audio-format", selected_format])
            args.extend(
                [
                    "--audio-quality",
                    "0" if selected_quality == "auto" else selected_quality,
                ]
            )

        args.append(
            "--yes-playlist"
            if playlist_mode.value or album_mode.value
            else "--no-playlist"
        )
        if embed_thumbnail.value or crop_thumbnail.value or album_mode.value:
            args.append("--embed-thumbnail")
        if crop_thumbnail.value or album_mode.value:
            args.extend(
                [
                    "--convert-thumbnails",
                    "jpg",
                    "--postprocessor-args",
                    "ThumbnailsConvertor+ffmpeg_o:-vf crop=\"'min(iw,ih)':'min(iw,ih)':'(iw-ow)/2':'(ih-oh)/2'\"",
                ]
            )
        if album_mode.value:
            args.extend(
                [
                    "--embed-metadata",
                    "--parse-metadata",
                    "%(album|playlist_title)s:%(meta_album)s",
                    "--parse-metadata",
                    "%(playlist_index)02d:%(meta_track)s",
                    "--parse-metadata",
                    "%(uploader|)s:%(meta_artist)s",
                ]
            )

        args.append(url_input.value)
        return args

    def quality_options(selected_format: str) -> list[ft.DropdownOption]:
        options = {
            "mp4": [
                ("auto", "自動"),
                ("4k", "4K"),
                ("2k", "2K"),
                ("1080p", "1080p"),
                ("720p", "720p"),
            ],
            "mkv": [
                ("auto", "自動"),
                ("4k", "4K"),
                ("2k", "2K"),
                ("1080p", "1080p"),
                ("720p", "720p"),
            ],
            "mp3": [
                ("auto", "自動"),
                ("320k", "320k"),
                ("256k", "256k"),
                ("192k", "192k"),
                ("128k", "128k"),
            ],
            "aac": [
                ("auto", "自動"),
                ("320k", "320k"),
                ("256k", "256k"),
                ("192k", "192k"),
                ("128k", "128k"),
            ],
            "flac": [("auto", "自動")],
        }
        return [
            ft.DropdownOption(key=key, text=label)
            for key, label in options[selected_format]
        ]

    def handle_format_select(e: ft.Event[ft.Dropdown]):
        quality_dropdown.options = quality_options(e.control.value or "mp4")
        quality_dropdown.value = "auto"
        quality_dropdown.update()
        album_mode.visible = (e.control.value or "mp4") in ("mp3", "aac", "flac")
        if not album_mode.visible:
            album_mode.value = False
            playlist_mode.disabled = False
            update_filename_template()
        album_mode.update()
        persist_settings()

    def update_filename_template() -> None:
        if album_mode.value:
            filename_template.value = (
                "%(album|playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s"
            )
        elif playlist_mode.value:
            filename_template.value = (
                "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s"
            )
        else:
            filename_template.value = "%(title)s.%(ext)s"
        filename_template.update()

    def handle_playlist_mode_change(e: ft.Event[ft.Checkbox]):
        update_filename_template()
        persist_settings()

    def handle_album_mode_change(e: ft.Event[ft.Checkbox]):
        playlist_mode.value = bool(e.control.value)
        playlist_mode.disabled = bool(e.control.value)
        playlist_mode.update()
        update_filename_template()
        persist_settings()

    def append_log(line: str) -> None:
        lines = (log_text.value or "").splitlines()
        lines.append(line)
        log_text.value = "\n".join(lines[-500:])
        log_text.update()

    async def handle_download(e: ft.Event[ft.FloatingActionButton]):
        if not url_input.value or not output_path_field.value:
            page.show_dialog(ft.SnackBar(ft.Text("URLまたは保存先を指定してください")))
            return
        command = find_yt_dlp()
        if command is None:
            page.show_dialog(ft.SnackBar(ft.Text("yt-dlpが見つかりませんでした")))
            return
        args = build_args()
        persist_settings()
        page.floating_action_button.disabled = True
        page.floating_action_button.update()
        progress_bar.value = None
        progress_bar.update()
        status_text.value = "ダウンロードの準備をしています..."
        status_text.update()
        try:
            creationflags = 0
            env = subprocess_env()
            if platform.system() == "Windows":
                creationflags = subprocess.CREATE_NO_WINDOW
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                creationflags=creationflags,
            )
            assert process.stdout is not None

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text.startswith("[DOWNLOADING]"):
                    _, percent, title = text.split("\t", maxsplit=2)
                    progress_bar.value = float(percent) / 100
                    status_text.value = f"{title[:50]}をダウンロード中..."
                    page.update()
                    await asyncio.sleep(0)

                else:
                    progress_bar.value = None
                    progress_bar.update()
                    append_log(text)

            status_code = await process.wait()

            if status_code != 0:
                page.show_dialog(ft.SnackBar(ft.Text("処理中にエラーが発生しました")))
                status_text.value = "処理中にエラーが発生しました"
                progress_bar.value = 0
            else:
                page.show_dialog(ft.SnackBar(ft.Text("正常にダウンロードできました")))
                status_text.value = "正常にダウンロードできました"
                progress_bar.value = 1
        finally:
            page.floating_action_button.disabled = False
            page.update()
            await asyncio.sleep(0)

    page.padding = 16
    url_input = ft.TextField(hint_text="URLを入力", label="URL", expand=1)
    output_path_btn = ft.TextButton(
        content=ft.Text("選択"), icon=ft.Icons.FOLDER, on_click=handle_output_pick
    )
    output_path_field = ft.TextField(read_only=True, expand=1)
    format_dropdown = ft.Dropdown(
        label="フォーマット",
        value="mp4",
        options=[
            ft.DropdownOption(key=name, text=name)
            for name in ("mp4", "mkv", "mp3", "aac", "flac")
        ],
        on_select=handle_format_select,
        expand=1,
    )
    quality_dropdown = ft.Dropdown(
        label="品質",
        value="auto",
        options=quality_options("mp4"),
        on_select=handle_settings_change,
        expand=1,
    )
    filename_template = ft.TextField(
        label="ファイル名テンプレート",
        value="%(title)s.%(ext)s",
        on_change=handle_settings_change,
        expand=1,
    )
    playlist_mode = ft.Checkbox(
        label="プレイリストモード", on_change=handle_playlist_mode_change
    )
    album_mode = ft.Checkbox(
        label="アルバムモード", visible=False, on_change=handle_album_mode_change
    )
    embed_thumbnail = ft.Checkbox(
        label="サムネイルを埋め込む", on_change=handle_settings_change
    )
    crop_thumbnail = ft.Checkbox(
        label="サムネイルを中央で正方形にクロップ",
        on_change=handle_settings_change,
    )
    log_text = ft.Text(size=14, selectable=True, font_family="monospace")
    log_area = ft.ListView(controls=[log_text], expand=1, auto_scroll=True)
    tabs = ft.Tabs(
        length=2,
        expand=1,
        content=ft.Column(
            expand=1,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="ログ", icon=ft.Icons.SUBJECT),
                        ft.Tab(label="設定", icon=ft.Icons.SETTINGS),
                    ]
                ),
                ft.TabBarView(
                    expand=1,
                    controls=[
                        ft.Container(
                            content=log_area,
                            border=ft.Border.all(1),
                            padding=ft.Padding.all(10),
                            border_radius=ft.BorderRadius.all(4),
                            expand=1,
                        ),
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Container(
                                                content=format_dropdown,
                                                expand=1,
                                            ),
                                            ft.Container(
                                                content=quality_dropdown,
                                                expand=1,
                                            ),
                                        ]
                                    ),
                                    ft.Row(controls=[filename_template]),
                                    ft.Row(
                                        controls=[
                                            ft.Container(
                                                content=playlist_mode,
                                                expand=1,
                                            ),
                                            ft.Container(
                                                content=embed_thumbnail,
                                                expand=1,
                                            ),
                                        ]
                                    ),
                                    ft.Row(
                                        controls=[
                                            ft.Container(
                                                content=album_mode,
                                                expand=1,
                                            ),
                                            ft.Container(
                                                content=crop_thumbnail,
                                                expand=1,
                                            ),
                                        ]
                                    ),
                                ],
                                tight=True,
                            ),
                            padding=ft.Padding.all(10),
                        ),
                    ],
                ),
            ],
        ),
    )
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.PLAY_ARROW, on_click=handle_download
    )
    status_text = ft.Text(value="準備完了", size=12)
    progress_bar = ft.ProgressBar(value=0, border_radius=ft.BorderRadius.all(4))

    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    ft.Row([url_input]),
                    ft.Row([output_path_field, output_path_btn]),
                    ft.Column(controls=[status_text, progress_bar]),
                    tabs,
                ],
                expand=1,
            ),
            expand=1,
        )
    )

    init()
    page.run_task(check_yt_dlp_update)


if __name__ == "__main__":
    if platform.system() != "Windows":
        fix_path_env()
    ft.run(main)
