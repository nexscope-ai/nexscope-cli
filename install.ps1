<#
.SYNOPSIS
    Nexscope CLI installer for Windows.
.DESCRIPTION
    Downloads the standalone nexscope.exe from GitHub Releases, verifies its SHA-256
    checksum and installs it under your user profile. No Python or administrator rights needed.

        irm https://raw.githubusercontent.com/nexscope-ai/nexscope-cli/main/install.ps1 | iex

    A piped script takes no parameters, so use environment variables in that form:

        $env:NEXSCOPE_VERSION = '0.1.2'
        irm https://raw.githubusercontent.com/nexscope-ai/nexscope-cli/main/install.ps1 | iex
.PARAMETER Version
    Install this version instead of the latest release.
.PARAMETER InstallDir
    Defaults to %LOCALAPPDATA%\Programs\nexscope\bin.
.PARAMETER NoVerify
    Skip the SHA-256 checksum check. Not recommended.
.PARAMETER NoPathUpdate
    Do not add the install directory to your user PATH.
#>
[CmdletBinding()]
param(
    [string] $Version = $env:NEXSCOPE_VERSION,
    [string] $InstallDir = $env:NEXSCOPE_INSTALL_DIR,
    [switch] $NoVerify,
    [switch] $NoPathUpdate
)

$ErrorActionPreference = 'Stop'
# The progress bar slows Invoke-WebRequest down considerably in Windows PowerShell.
$ProgressPreference = 'SilentlyContinue'

$Repo = 'nexscope-ai/nexscope-cli'
$Binary = 'nexscope'
$DownloadUrl = if ($env:NEXSCOPE_DOWNLOAD_URL) { $env:NEXSCOPE_DOWNLOAD_URL } else { "https://github.com/$Repo/releases/download" }

# throw, not exit: under `irm | iex`, exit would close the user's PowerShell window before they read the error.
function Fail($message) {
    throw "error: $message"
}

# Windows PowerShell 5.1 defaults to TLS 1.0, which GitHub refuses.
if ($PSVersionTable.PSVersion.Major -lt 6) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
}

# --- Platform ---------------------------------------------------------------

# x64 PowerShell on an ARM64 machine reports AMD64; the real architecture is in PROCESSOR_ARCHITEW6432.
$rawArch = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
switch ($rawArch) {
    'AMD64' { $arch = 'amd64' }
    'ARM64' { $arch = 'arm64' }
    default { Fail "unsupported architecture '$rawArch'; builds exist for amd64 and arm64" }
}

if (-not $Version) {
    try {
        $Version = (Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -UseBasicParsing).tag_name
    } catch {
        Fail "could not find the latest release ($($_.Exception.Message)); retry or set `$env:NEXSCOPE_VERSION"
    }
}
$Version = $Version -replace '^v', ''
$archive = "${Binary}_${Version}_windows_${arch}.zip"
$baseUrl = "$DownloadUrl/v$Version"
if (-not $InstallDir) { $InstallDir = Join-Path $env:LOCALAPPDATA 'Programs\nexscope\bin' }

# --- Download, verify, install ----------------------------------------------

$tmp = Join-Path ([IO.Path]::GetTempPath()) ([IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
try {
    $zip = Join-Path $tmp $archive
    Write-Host "Downloading $Binary $Version (windows/$arch)..."
    try {
        Invoke-WebRequest -Uri "$baseUrl/$archive" -OutFile $zip -UseBasicParsing
    } catch {
        Fail "could not download $baseUrl/$archive; is $Version a released version with binaries? ($($_.Exception.Message))"
    }

    if (-not $NoVerify) {
        $sums = Join-Path $tmp 'checksums.txt'
        try {
            Invoke-WebRequest -Uri "$baseUrl/checksums.txt" -OutFile $sums -UseBasicParsing
        } catch {
            Fail "could not download checksums.txt for $Version"
        }
        $expected = $null
        foreach ($line in Get-Content $sums) {
            $parts = $line.Trim() -split '\s+', 2
            if ($parts.Count -eq 2 -and $parts[1].TrimStart('*') -eq $archive) { $expected = $parts[0].ToLowerInvariant() }
        }
        if (-not $expected) { Fail "$archive is not listed in checksums.txt" }
        $actual = (Get-FileHash -Path $zip -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) {
            Fail "checksum mismatch for ${archive}: got $actual, expected $expected. Do not use this download."
        }
        Write-Host 'Checksum verified.'
    }

    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $extracted = Join-Path $tmp "$Binary.exe"
    if (-not (Test-Path $extracted)) { Fail "the archive does not contain $Binary.exe" }

    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    $target = Join-Path $InstallDir "$Binary.exe"
    try {
        Copy-Item -Path $extracted -Destination $target -Force
    } catch {
        Fail "could not write $target; close any running $Binary and try again ($($_.Exception.Message))"
    }
    # Clear the downloaded-from-internet mark so SmartScreen does not block the first run.
    Unblock-File -Path $target -ErrorAction SilentlyContinue
} finally {
    Remove-Item -Path $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

# --- PATH -------------------------------------------------------------------

if (-not $NoPathUpdate) {
    # Edit the stored user PATH, not $env:PATH, which also contains the machine PATH.
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $entries = @($userPath -split ';' | Where-Object { $_ })
    if ($entries -notcontains $InstallDir) {
        [Environment]::SetEnvironmentVariable('Path', (($entries + $InstallDir) -join ';'), 'User')
        Write-Host "Added $InstallDir to your user PATH."
    }
    if (($env:PATH -split ';') -notcontains $InstallDir) { $env:PATH = "$InstallDir;$env:PATH" }
}

# The install already succeeded; a binary that fails to start must not abort the script here.
$reported = try { & $target --version 2>$null | Select-Object -First 1 } catch { $null }
if (-not $reported) { $reported = $Version }
Write-Host ''
Write-Host "Installed $Binary $reported to $target" -ForegroundColor Green
Write-Host ''
if ((($env:PATH -split ';') -contains $InstallDir)) {
    Write-Host 'Get started (new terminals pick up PATH automatically):'
} else {
    Write-Host "Add $InstallDir to your PATH, then get started:"
}
Write-Host "  $Binary doctor --offline"
Write-Host "  $Binary tools list --search amazon"
