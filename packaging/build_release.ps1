[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Clean,
    [switch]$BuildInstaller,
    [switch]$SkipInstaller,
    [string]$InnoPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Phase18Log {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[Phase18D] $Message"
}

function Resolve-RepoRoot {
    param([string]$StartPath = (Get-Location).Path)

    $current = (Resolve-Path -LiteralPath $StartPath).Path
    while ($true) {
        $pyproject = Join-Path $current "pyproject.toml"
        $entryPoint = Join-Path $current "v3_app\main.py"
        if ((Test-Path -LiteralPath $pyproject) -and (Test-Path -LiteralPath $entryPoint)) {
            return $current
        }

        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $current) {
            throw "Could not locate HelmForge repository root from $StartPath"
        }
        $current = $parent
    }
}

function Test-PythonImport {
    param(
        [Parameter(Mandatory = $true)][string]$PythonExe,
        [Parameter(Mandatory = $true)][string]$ModuleName
    )

    & $PythonExe -c "import $ModuleName" *> $null
    return ($LASTEXITCODE -eq 0)
}

function Resolve-InnoCompiler {
    param([string]$RequestedPath)

    if (-not [string]::IsNullOrWhiteSpace($RequestedPath)) {
        if (Test-Path -LiteralPath $RequestedPath -PathType Leaf) {
            return (Resolve-Path -LiteralPath $RequestedPath).Path
        }
        if (Test-Path -LiteralPath $RequestedPath -PathType Container) {
            $candidate = Join-Path $RequestedPath "ISCC.exe"
            if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                return (Resolve-Path -LiteralPath $candidate).Path
            }
        }
        throw "Inno Setup compiler was not found at -InnoPath '$RequestedPath'."
    }

    $pathCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($pathCommand) {
        return $pathCommand.Source
    }

    $commonPaths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $commonPaths) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

$RepoRoot = Resolve-RepoRoot
Set-Location -LiteralPath $RepoRoot

$OutputRoot = Join-Path $RepoRoot "packaging\output"
$BuildRoot = Join-Path $RepoRoot "packaging\build"
$DistRoot = Join-Path $RepoRoot "packaging\dist"
$PackagedAppRoot = Join-Path $DistRoot "HelmForge"
$PackagedExe = Join-Path $PackagedAppRoot "HelmForge.exe"
$EntryPoint = Join-Path $RepoRoot "v3_app\main.py"
$PyProject = Join-Path $RepoRoot "pyproject.toml"
$InnoScript = Join-Path $RepoRoot "packaging\inno\helmforge.iss"
$InstallerOutputRoot = Join-Path $RepoRoot "packaging\installer"
$AppIconPath = Join-Path $RepoRoot "assets\app_icon.ico"

$BuildMode = if ($DryRun) { "DryRun one-folder planning" } else { "PyInstaller one-folder build" }
if ($Clean) {
    $BuildMode = "$BuildMode with clean output"
}
if ($BuildInstaller) {
    $BuildMode = "$BuildMode plus installer compile"
}
if ($SkipInstaller) {
    $BuildMode = "$BuildMode with installer skipped"
}

Write-Phase18Log "Repository root: $RepoRoot"
Write-Phase18Log "Build mode: $BuildMode"
Write-Phase18Log "Phase 18D final packaging QA path over the PyInstaller one-folder build and optional Inno Setup installer compile."
Write-Phase18Log "Entry point: $EntryPoint"
Write-Phase18Log "Output folder: $PackagedAppRoot"

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    throw "Python was not found on PATH."
}
$PythonExe = $PythonCommand.Source
Write-Phase18Log "Python: $PythonExe"

$PyProjectText = Get-Content -LiteralPath $PyProject -Raw
if ($PyProjectText -notmatch 'helmforge = "v3_app.main:main"') {
    throw 'Expected console script missing: helmforge = "v3_app.main:main"'
}
if ($PyProjectText -notmatch 'helmforge-bridge = "bridge_app.main:main"') {
    throw 'Expected console script missing: helmforge-bridge = "bridge_app.main:main"'
}
Write-Phase18Log 'Found expected source entry points: helmforge = "v3_app.main:main" and helmforge-bridge = "bridge_app.main:main"'

foreach ($module in @("PySide6", "pyqtgraph", "v3_app.main", "bridge_app.main")) {
    if (-not (Test-PythonImport -PythonExe $PythonExe -ModuleName $module)) {
        throw "Python module import failed: $module. Run python -m pip install -e . from the repo root."
    }
    Write-Phase18Log "Import check passed: $module"
}

$AppVersion = (& $PythonExe -c "from v3_app.version import APP_VERSION; print(APP_VERSION)").Trim()
if ([string]::IsNullOrWhiteSpace($AppVersion)) {
    throw "Could not read AppVersion from v3_app.version."
}
Write-Phase18Log "App version: $AppVersion"

foreach ($path in @($OutputRoot, $BuildRoot, $DistRoot, $InstallerOutputRoot)) {
    if ($DryRun) {
        Write-Phase18Log "Dry run: would ensure directory $path"
    } else {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
        Write-Phase18Log "Ensured directory $path"
    }
}

if ($Clean) {
    $safeTargets = @($OutputRoot, $BuildRoot, $DistRoot, $InstallerOutputRoot)
    foreach ($target in $safeTargets) {
        $fullTarget = [System.IO.Path]::GetFullPath($target)
        $fullRepo = [System.IO.Path]::GetFullPath($RepoRoot)
        if (-not $fullTarget.StartsWith($fullRepo, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean path outside repo: $fullTarget"
        }
        if (Test-Path -LiteralPath $fullTarget) {
            if ($DryRun) {
                Write-Phase18Log "Dry run: would clean $fullTarget"
            } else {
                Remove-Item -LiteralPath $fullTarget -Recurse -Force
                Write-Phase18Log "Cleaned $fullTarget"
            }
        }
    }
}

foreach ($path in @($OutputRoot, $BuildRoot, $DistRoot, $InstallerOutputRoot)) {
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
    }
}

$PyInstallerAvailable = Test-PythonImport -PythonExe $PythonExe -ModuleName "PyInstaller"
# Planned command starts with: python -m PyInstaller
$PyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--onedir",
    "--windowed",
    "--name", "HelmForge",
    "--distpath", $DistRoot,
    "--workpath", $BuildRoot,
    "--specpath", $OutputRoot,
    "--hidden-import", "pyqtgraph",
    "--hidden-import", "bridge_app.main",
    "--hidden-import", "shared_core.models.workspace",
    "--exclude-module", "pytest",
    "--exclude-module", "tests",
    "--exclude-module", "pyqtgraph.examples",
    "--exclude-module", "PySide6.QtTest",
    "--exclude-module", "numpy._core._multiarray_tests",
    $EntryPoint
)
if (Test-Path -LiteralPath $AppIconPath -PathType Leaf) {
    $PyInstallerArgs = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "HelmForge",
        "--icon", $AppIconPath,
        "--distpath", $DistRoot,
        "--workpath", $BuildRoot,
        "--specpath", $OutputRoot,
        "--hidden-import", "pyqtgraph",
        "--hidden-import", "bridge_app.main",
        "--hidden-import", "shared_core.models.workspace",
        "--exclude-module", "pytest",
        "--exclude-module", "tests",
        "--exclude-module", "pyqtgraph.examples",
        "--exclude-module", "PySide6.QtTest",
        "--exclude-module", "numpy._core._multiarray_tests",
        $EntryPoint
    )
    Write-Phase18Log "Icon wiring: using $AppIconPath"
} else {
    Write-Phase18Log "Icon wiring: assets\app_icon.ico is missing; PyInstaller icon embedding is deferred."
}

$InnoCompiler = Resolve-InnoCompiler -RequestedPath $InnoPath
$InnoArgs = @(
    "/DAppVersion=$AppVersion",
    "/DAppPublisher=HelmForge",
    "/DSourceDir=$PackagedAppRoot",
    "/O$InstallerOutputRoot",
    $InnoScript
)

Write-Phase18Log "Planned one-folder build command:"
Write-Phase18Log "python $($PyInstallerArgs -join ' ')"
Write-Phase18Log "Packaged smoke command after a successful build:"
Write-Phase18Log "packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250"
Write-Phase18Log "Installer output folder: $InstallerOutputRoot"
if ($InnoCompiler) {
    Write-Phase18Log "Inno Setup compiler: $InnoCompiler"
    Write-Phase18Log "Planned installer command: `"$InnoCompiler`" $($InnoArgs -join ' ')"
} else {
    Write-Phase18Log "Inno Setup compiler was not found. Use -InnoPath or install Inno Setup before -BuildInstaller."
}

if ($DryRun) {
    if ($PyInstallerAvailable) {
        Write-Phase18Log "Dry run: PyInstaller is available; omit -DryRun to attempt the one-folder build."
    } else {
        Write-Phase18Log "Dry run: PyInstaller is not importable. Install it before attempting a real build."
    }
    if ($BuildInstaller -and -not $InnoCompiler) {
        Write-Phase18Log "Dry run: -BuildInstaller was requested, but ISCC.exe is missing. A real installer compile would fail."
    }
    Write-Phase18Log "Dry run complete. No build output or installer success is claimed."
    exit 0
}

if (-not $PyInstallerAvailable) {
    throw "PyInstaller is not importable. Install PyInstaller or rerun with -DryRun for planning only."
}

& $PythonExe @PyInstallerArgs
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $PackagedExe)) {
    throw "Expected packaged executable was not created: $PackagedExe"
}

Write-Phase18Log "Build result: one-folder build completed."
Write-Phase18Log "Packaged executable: $PackagedExe"
Write-Phase18Log "Next smoke-test command: packaging\dist\HelmForge\HelmForge.exe --smoke-exit-ms 250"

if ($SkipInstaller -or -not $BuildInstaller) {
    Write-Phase18Log "No installer was created. Pass -BuildInstaller to compile packaging\inno\helmforge.iss when ISCC.exe is available."
    exit 0
}

if (-not $InnoCompiler) {
    throw "Inno Setup compiler was not found, and -BuildInstaller was requested. Install Inno Setup 6, add ISCC.exe to PATH, or pass -InnoPath."
}

if (-not (Test-Path -LiteralPath $InnoScript -PathType Leaf)) {
    throw "Installer script is missing: $InnoScript"
}

Write-Phase18Log "-BuildInstaller was requested; compiling Inno Setup installer."
& $InnoCompiler @InnoArgs
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compiler failed with exit code $LASTEXITCODE"
}

Write-Phase18Log "Installer build completed. Output folder: $InstallerOutputRoot"
