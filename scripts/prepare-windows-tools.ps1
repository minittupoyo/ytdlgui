param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

$denoVersion = "2.9.6"
$denoSha256 = "15e5300b0ba3c3695a7621d90160a746ec9e710228cee639afa9d580f6e3cd11"
$denoUrl = "https://github.com/denoland/deno/releases/download/v$denoVersion/deno-x86_64-pc-windows-msvc.zip"

$ffmpegArchive = "ffmpeg-n8.1.2-51-g7ba069f4f1-win64-lgpl-8.1.zip"
$ffmpegSha256 = "5d6986f507d77e876582145834a416c0ef534e357663b5de2892685dfd2e82cc"
$ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-09-10-15-31/$ffmpegArchive"

$toolsDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("ytdlgui-tools-" + [guid]::NewGuid())
New-Item -ItemType Directory -Force -Path $toolsDirectory, $temporaryDirectory | Out-Null

function Get-VerifiedArchive {
    param([string]$Url, [string]$Destination, [string]$ExpectedSha256)
    Invoke-WebRequest -Uri $Url -OutFile $Destination
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Destination).Hash.ToLowerInvariant()
    if ($actual -ne $ExpectedSha256) {
        throw "SHA-256 mismatch for $Url (expected $ExpectedSha256, got $actual)"
    }
}

try {
    $denoZip = Join-Path $temporaryDirectory "deno.zip"
    Get-VerifiedArchive $denoUrl $denoZip $denoSha256
    Expand-Archive -LiteralPath $denoZip -DestinationPath (Join-Path $temporaryDirectory "deno")
    Copy-Item -LiteralPath (Join-Path $temporaryDirectory "deno\deno.exe") -Destination $toolsDirectory

    $ffmpegZip = Join-Path $temporaryDirectory "ffmpeg.zip"
    Get-VerifiedArchive $ffmpegUrl $ffmpegZip $ffmpegSha256
    $ffmpegExtract = Join-Path $temporaryDirectory "ffmpeg"
    Expand-Archive -LiteralPath $ffmpegZip -DestinationPath $ffmpegExtract
    $ffmpegExe = Get-ChildItem -LiteralPath $ffmpegExtract -Filter "ffmpeg.exe" -Recurse | Select-Object -First 1
    $ffprobeExe = Get-ChildItem -LiteralPath $ffmpegExtract -Filter "ffprobe.exe" -Recurse | Select-Object -First 1
    if ($null -eq $ffmpegExe -or $null -eq $ffprobeExe) {
        throw "FFmpeg archive did not contain ffmpeg.exe and ffprobe.exe"
    }
    Copy-Item -LiteralPath $ffmpegExe.FullName -Destination $toolsDirectory
    Copy-Item -LiteralPath $ffprobeExe.FullName -Destination $toolsDirectory
}
finally {
    Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force -ErrorAction SilentlyContinue
}
