# Nora installer for Windows PowerShell.
$ErrorActionPreference = "Stop"

$Repo = "git+https://github.com/Z-Jared/nora.git"

Write-Host "Installing Nora..."

$PythonCommand = $null
foreach ($candidate in @("py", "python3", "python")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) {
        $PythonCommand = $candidate
        break
    }
}

if (-not $PythonCommand) {
    Write-Error "Python 3.9+ was not found. Install Python first, then run this installer again."
    exit 1
}

$VersionText = & $PythonCommand -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$Version = [version]$VersionText
if ($Version -lt [version]"3.9") {
    Write-Error "Python >= 3.9 required, found $VersionText"
    exit 1
}

Write-Host "Python $VersionText found."

& $PythonCommand -m pip install --user $Repo

$UserBase = & $PythonCommand -m site --user-base
$ScriptsDir = Join-Path $UserBase "Scripts"

Write-Host ""
Write-Host "Installation complete!"
Write-Host ""
Write-Host "  nora         Start the CLI"
Write-Host "  nora-serve   Start the HTTP server with Web UI"
Write-Host ""

$noraCommand = Get-Command nora -ErrorAction SilentlyContinue
if (-not $noraCommand) {
    Write-Host "'nora' is not currently in your PATH." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Add this directory to your user PATH:"
    Write-Host "  $ScriptsDir"
    Write-Host ""
    Write-Host "Then open a new PowerShell window and run: nora"
}
