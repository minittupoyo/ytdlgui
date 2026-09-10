import flet as ft
import os
import subprocess
import asyncio


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
    async def handle_output_pick(e: ft.Event[ft.TextButton]):
        output_path_field.value = await ft.FilePicker().get_directory_path()

    async def handle_download(e: ft.Event[ft.FloatingActionButton]):
        if not url_input.value or not output_path_field.value:
            page.show_dialog(ft.SnackBar(ft.Text("URLまたは保存先を指定してください")))
            return
        command = "yt-dlp"
        args = [
            "--newline",
            "--color",
            "no_color",
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "-o",
            "%(title)s.%(ext)s",
            "-P",
            os.path.abspath(output_path_field.value),
            "--progress-template",
            "download:[DOWNLOADING]\t%(progress._percent)s\t%(info.title)s",
            url_input.value,
        ]
        page.floating_action_button.disabled = True
        page.floating_action_button.update()
        progress_bar.value = None
        progress_bar.update()
        try:
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert process.stdout is not None

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode(errors='replace').rstrip()
                if text.startswith("[DOWNLOADING]"):
                    _, percent, title = text.split('\t',maxsplit=2)
                    print(round(float(percent) / 100))
                    progress_bar.value = float(percent) / 100
                    page.update()
                    await asyncio.sleep(0)
                    
                else:
                    progress_bar.value = None
                    progress_bar.update()
                    log_text.value += text + "\n"
                    log_text.update()

            status_code = await process.wait()

            if status_code != 0:
                page.show_dialog(ft.SnackBar(ft.Text("処理中にエラーが発生しました")))
                progress_bar.value = 0
            else:
                page.show_dialog(ft.SnackBar(ft.Text("正常にダウンロードできました")))
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
    log_text = ft.Text(size=14,selectable=True)
    log_area = ft.ListView(controls=[log_text], expand=1, auto_scroll=True)
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.PLAY_ARROW, on_click=handle_download
    )
    progress_bar = ft.ProgressBar(value=0,border_radius=ft.BorderRadius.all(4))

    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    ft.Row([url_input]),
                    ft.Row([output_path_field, output_path_btn]),
                    progress_bar,
                    ft.Container(content=log_area, border=ft.Border.all(1),padding=ft.Padding.all(10),border_radius=ft.BorderRadius.all(4), expand=1),
                ],
                expand=1,
            ),
            expand=1,
        )
    )


if __name__ == "__main__":
    fix_path_env()
    ft.run(main)
