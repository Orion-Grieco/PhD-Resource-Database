<#
.SYNOPSIS
    Build the desktop app: export the frontend, bundle with PyInstaller, smoke-test, make the installer.

.DESCRIPTION
    Name, version, and port come from desktop\app_info.json. Outputs:
      dist\<ExeName>\<ExeName>.exe              the app folder (runnable as-is)
      dist\installer\<ExeName>-<ver>-setup.exe  the installer (needs Inno Setup 6)

.EXAMPLE
    .\build.ps1                  # full build
    .\build.ps1 -SkipInstaller   # app folder only
    .\build.ps1 -SkipFrontend    # reuse the last frontend export (Python-only changes)
#>
param(
    [switch]$SkipFrontend,
    [switch]$SkipSmokeTest,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

function Step($message) { Write-Host "`n==> $message" -ForegroundColor Cyan }
function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    # Tools like PyInstaller log to stderr. With "Stop", Windows PowerShell 5.1 turns that
    # into a terminating error whenever output is redirected, so judge by exit code instead.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Exe @Arguments 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) { "$($_.TargetObject)" } else { "$_" }
        }
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed with exit code $LASTEXITCODE" }
}

$Info = Get-Content (Join-Path $Root "desktop\app_info.json") -Raw | ConvertFrom-Json
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Reflex = Join-Path $Root ".venv\Scripts\reflex.exe"
$AppDir = Join-Path $Root "dist\$($Info.exe_name)"
$AppExe = Join-Path $AppDir "$($Info.exe_name).exe"
Write-Host "$($Info.name) $($Info.version) (port $($Info.port))"

# 1. Python environment -------------------------------------------------------
Step "Checking Python environment"
if (-not (Test-Path $Python)) {
    throw "No .venv found. Create it first: python -m venv .venv; .venv\Scripts\python -m pip install -r requirements.txt"
}
Invoke-Checked $Python @("-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", "requirements-build.txt")

# 2. Frontend -----------------------------------------------------------------
if ($SkipFrontend) {
    Step "Skipping frontend export (reusing .web\build\client)"
    if (-not (Test-Path ".web\build\client\index.html")) { throw "No previous frontend export found; run without -SkipFrontend." }
} else {
    Step "Exporting frontend (backend URL http://127.0.0.1:$($Info.port))"
    $previousApiUrl = $env:REFLEX_API_URL
    $env:REFLEX_API_URL = "http://127.0.0.1:$($Info.port)"
    try {
        Invoke-Checked $Reflex @("export", "--frontend-only", "--no-zip", "--env", "prod")
    } finally {
        $env:REFLEX_API_URL = $previousApiUrl
    }
}

# 3. Bundle -------------------------------------------------------------------
Step "Bundling with PyInstaller"
Invoke-Checked $Python @("-m", "PyInstaller", "desktop\PhDProgramFinder.spec", "--distpath", "dist", "--workpath", "build", "--noconfirm", "--log-level", "WARN")

# 4. Smoke test ---------------------------------------------------------------
if ($SkipSmokeTest) {
    Step "Skipping smoke test"
} else {
    Step "Smoke-testing the bundled app"
    if (Get-NetTCPConnection -State Listen -LocalPort $Info.port -ErrorAction SilentlyContinue) {
        throw "Port $($Info.port) is in use (is the app running?). Close it and rebuild, or use -SkipSmokeTest."
    }
    $testData = Join-Path ([IO.Path]::GetTempPath()) "$($Info.exe_name)-smoke-$PID"
    $previousDataDir = $env:DATA_DIR
    $env:DATA_DIR = $testData
    $proc = Start-Process -FilePath $AppExe -ArgumentList "--server-only" -PassThru
    $env:DATA_DIR = $previousDataDir
    try {
        $ok = $false
        foreach ($i in 1..60) {
            Start-Sleep -Seconds 1
            if ($proc.HasExited) { break }
            try {
                $ping = Invoke-WebRequest "http://127.0.0.1:$($Info.port)/ping" -UseBasicParsing -TimeoutSec 2
                $page = Invoke-WebRequest "http://127.0.0.1:$($Info.port)/add" -UseBasicParsing -TimeoutSec 5
                if ($ping.StatusCode -eq 200 -and $page.StatusCode -eq 200 -and (Test-Path "$testData\programs.db")) { $ok = $true; break }
            } catch { }
        }
        if (-not $ok) {
            $log = "$testData\logs\app.log"
            if (Test-Path $log) { Get-Content $log -Tail 30 | Write-Host }
            throw "Smoke test failed: the bundled app did not serve pages (log above)."
        }
        Write-Host "Bundled app served pages and created its database."
    } finally {
        if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
        Start-Sleep -Seconds 1
        Remove-Item $testData -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 5. Installer ----------------------------------------------------------------
if ($SkipInstaller) {
    Step "Skipping installer"
} else {
    Step "Building installer"
    $iscc = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) {
        throw "Inno Setup 6 not found. Install it (winget install -e --id JRSoftware.InnoSetup), or use -SkipInstaller."
    }
    $defines = @(
        "/DAppName=$($Info.name)",
        "/DAppVersion=$($Info.version)",
        "/DAppPublisher=$($Info.publisher)",
        "/DAppId=$($Info.app_id)",
        "/DExeName=$($Info.exe_name)",
        "/DSourceDir=$AppDir",
        "/DOutputDir=$(Join-Path $Root 'dist\installer')"
    )
    $icon = Join-Path $Root "desktop\icon.ico"
    if (Test-Path $icon) { $defines += "/DIconFile=$icon" }
    Invoke-Checked $iscc ($defines + @("/Q", "desktop\installer.iss"))
}

Step "Done"
Write-Host "App folder: $AppDir"
if (-not $SkipInstaller) {
    Write-Host "Installer:  $(Join-Path $Root "dist\installer\$($Info.exe_name)-$($Info.version)-setup.exe")"
}
