# Repository Guidelines

## Project Structure & Module Organization

- `src/main.py` contains the Flet desktop/web application and download workflow.
- `src/assets/` holds packaged UI assets such as `icon.png` and splash screens.
- `tests/` contains pytest/Flet integration tests; add new tests alongside the behavior they cover.
- `main.py` is a small root-level launcher stub. `main.spec` supports PyInstaller packaging.
- `.github/workflows/build-windows.yml` defines the Windows build artifact workflow. Treat `build/` and `dist/` as generated output.

## Build, Test, and Development Commands

Use `uv` to keep Python and project dependencies consistent:

```powershell
uv run flet run          # Run the desktop app
uv run flet run --web    # Run the browser version
uv run pytest            # Run the test suite
uv run flet test         # Run Flet UI integration tests
uv run flet build windows -v  # Produce a verbose Windows build
```

The application invokes `yt-dlp` and expects `ffmpeg` and `deno` to be available on `PATH`; verify those tools before manually exercising downloads.

## Coding Style & Naming Conventions

Target Python 3.10+ and follow standard PEP 8 conventions: four-space indentation, `snake_case` for functions and variables, `PascalCase` for classes, and lowercase module names. Keep type hints on public helpers and use short, focused event handlers such as `handle_download`. Prefer `pathlib` or existing `os.path` patterns consistently within a change. No formatter or linter is configured, so keep imports grouped (standard library before third-party), remove unused imports, and format code clearly for review.

## Testing Guidelines

Pytest is configured in `pyproject.toml` with `tests/` as the test root and automatic asyncio support. Name files `test_*.py` and tests `test_<behavior>`. For UI changes, use Flet's `flet_app` fixture and stable control keys (for example, `"increment"`) rather than implementation-sensitive selectors. Add regression coverage for download argument construction, validation, and visible status changes when modifying them.

## Commit & Pull Request Guidelines

History uses brief, imperative summaries (often Japanese), such as `Windows環境向けの最適化`. Keep commits small and describe the user-visible change; add a scope when useful, e.g. `download: validate output path`. Pull requests should explain the behavior change, list commands run, link relevant issues, and include screenshots or a short recording for UI changes. Do not commit build artifacts, virtual environments, credentials, or downloaded media.
