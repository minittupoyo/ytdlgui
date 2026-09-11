# Ytdlgui app

## Run the app

### uv

Run as a desktop app:

```bash
uv run flet run
```

Run as a web app:

```bash
uv run flet run --web
```

For more details on running the app, refer to the [Getting Started Guide](https://flet.dev/docs/).

## Build the app

### Android

```bash
flet build apk -v
```

For more details on building and signing `.apk` or `.aab`, refer to the [Android Packaging Guide](https://flet.dev/docs/publish/android/).

### iOS

```bash
flet build ipa -v
```

For more details on building and signing `.ipa`, refer to the [iOS Packaging Guide](https://flet.dev/docs/publish/ios/).

### macOS

```bash
flet build macos -v
```

For more details on building macOS package, refer to the [macOS Packaging Guide](https://flet.dev/docs/publish/macos/).

### Linux

```bash
flet build linux -v
```

For more details on building Linux package, refer to the [Linux Packaging Guide](https://flet.dev/docs/publish/linux/).

### Windows

```bash
flet build windows -v
```

GitHub ActionsのWindowsビルドでは、`yt-dlp`、`ffmpeg`、`ffprobe`、
`deno`を含むポータブルZIPとInno Setupインストーラーを生成します。
インストーラーは管理者権限を必要とせず、既定では
`%LOCALAPPDATA%\Programs\Ytdlgui`へインストールされます。

署名証明書を使用していないため、Windows SmartScreenの警告が表示される
場合があります。配布物はGitHub Releasesから取得し、同時に公開される
`SHA256SUMS.txt`で整合性を確認してください。

For more details on building Windows package, refer to the [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).

### Web

```bash
flet build web -v
```

For more details on building Web app, refer to the [Web Packaging Guide](https://flet.dev/docs/publish/web/).
