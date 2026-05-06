[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$OpenPages,
    [switch]$LaunchInstallers,
    [string]$ThrustmasterInstaller,
    [string]$VJoyInstaller,
    [string]$LogPath = (Join-Path $env:TEMP "helmforge_runtime_setup_check.log")
)

$ErrorActionPreference = "Stop"

$ThrustmasterSupportUrl = "https://support.thrustmaster.com/en/product/t-flight-hotas-one-en/"
$VJoySetupSourceUrl = "https://github.com/BrunnerInnovation/vJoy/releases"

function Write-SetupLog {
    param([string]$Message)

    Write-Output $Message
    $logDirectory = Split-Path -Parent $LogPath
    if ($logDirectory -and -not (Test-Path -LiteralPath $logDirectory)) {
        New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    }
    Add-Content -LiteralPath $LogPath -Value ("{0} {1}" -f (Get-Date -Format "s"), $Message)
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-PresentDeviceNames {
    try {
        return @(Get-PnpDevice -PresentOnly -ErrorAction Stop |
            Where-Object { $_.FriendlyName } |
            ForEach-Object { "{0} {1}" -f $_.FriendlyName, $_.InstanceId })
    }
    catch {
        Write-SetupLog ("Device enumeration warning: {0}" -f $_.Exception.Message)
        return @()
    }
}

function Find-LikelyHotasDevices {
    param([string[]]$DeviceNames)

    return @($DeviceNames | Where-Object {
        $_ -match "Thrustmaster|T\.Flight|T-Flight|HOTAS One|VID_044F.*PID_B68D"
    })
}

function Find-LikelyVJoyState {
    param([string[]]$DeviceNames)

    $deviceMatches = @($DeviceNames | Where-Object { $_ -match "vJoy" })
    $pathMatches = @()
    $candidatePaths = @(
        (Join-Path $env:ProgramFiles "vJoy\x64\vJoyInterface.dll"),
        (Join-Path $env:ProgramFiles "vJoy\vJoyInterface.dll")
    )
    if ($env:ProgramFiles -and ${env:ProgramFiles(x86)}) {
        $candidatePaths += (Join-Path ${env:ProgramFiles(x86)} "vJoy\x86\vJoyInterface.dll")
        $candidatePaths += (Join-Path ${env:ProgramFiles(x86)} "vJoy\vJoyInterface.dll")
    }
    foreach ($path in $candidatePaths) {
        if ($path -and (Test-Path -LiteralPath $path)) {
            $pathMatches += $path
        }
    }

    return [pscustomobject]@{
        DeviceMatches = $deviceMatches
        PathMatches = $pathMatches
        Detected = (($deviceMatches.Count + $pathMatches.Count) -gt 0)
    }
}

Write-SetupLog "HelmForge Runtime Setup Check"
Write-SetupLog "Product: HelmForge"
Write-SetupLog "Technical subtitle: HOTAS Control Panel V3"
Write-SetupLog "Known Thrustmaster target: Thrustmaster T-Flight HOTAS One / Thrustmaster T.Flight Hotas One"
Write-SetupLog ("Dry run: {0}" -f [bool]$DryRun)
Write-SetupLog ("Admin active: {0}" -f (Test-IsAdmin))
Write-SetupLog ("Log path: {0}" -f $LogPath)

$deviceNames = Get-PresentDeviceNames
$hotasMatches = Find-LikelyHotasDevices -DeviceNames $deviceNames
$vjoyState = Find-LikelyVJoyState -DeviceNames $deviceNames
$installedRuntimeSoftware = @(Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall' -ErrorAction SilentlyContinue |
    ForEach-Object { Get-ItemProperty $_.PsPath -ErrorAction SilentlyContinue } |
    Where-Object { $_.DisplayName -match 'Thrustmaster|T\.Flight|vJoy' } |
    Select-Object DisplayName,DisplayVersion,Publisher,InstallLocation)

Write-SetupLog ("Checked present PnP device names: {0}" -f $deviceNames.Count)
if ($installedRuntimeSoftware.Count -gt 0) {
    foreach ($item in $installedRuntimeSoftware) {
        Write-SetupLog ("Installed runtime software: {0} {1} ({2})" -f $item.DisplayName, $item.DisplayVersion, $item.Publisher)
    }
}
else {
    Write-SetupLog "Installed runtime software: no Thrustmaster/vJoy package found in uninstall registry."
}
if ($hotasMatches.Count -gt 0) {
    Write-SetupLog "HOTAS status: T-Flight HOTAS One Detected"
    foreach ($name in $hotasMatches) {
        Write-SetupLog ("  HOTAS match: {0}" -f $name)
    }
}
else {
    Write-SetupLog "HOTAS status: HOTAS Not Connected"
}

if ($vjoyState.Detected) {
    Write-SetupLog "vJoy status: vJoy Detected"
    foreach ($name in $vjoyState.DeviceMatches) {
        Write-SetupLog ("  vJoy device match: {0}" -f $name)
    }
    foreach ($path in $vjoyState.PathMatches) {
        Write-SetupLog ("  vJoy file match: {0}" -f $path)
    }
}
else {
    Write-SetupLog "vJoy status: vJoy Missing"
}

Write-SetupLog "Runtime status: Simulation Mode Active unless physical input and output writes are both verified."
Write-SetupLog "Full Live Runtime Ready: false in Phase 2A unless later post-install verification proves both sides."

if ($OpenPages) {
    Write-SetupLog "Opening official setup pages by request."
    Start-Process $ThrustmasterSupportUrl
    Start-Process $VJoySetupSourceUrl
}

if (-not $LaunchInstallers) {
    Write-SetupLog "No installers launched. Use -LaunchInstallers with explicit installer paths to request installer launch."
    if ($DryRun) {
        Write-SetupLog "Dry run only. No installers launched."
    }
    exit 0
}

if ($DryRun) {
    Write-SetupLog "Dry run only. -LaunchInstallers was present, but no installers launched."
    exit 0
}

$installerPaths = @()
if ($ThrustmasterInstaller) {
    $installerPaths += $ThrustmasterInstaller
}
if ($VJoyInstaller) {
    $installerPaths += $VJoyInstaller
}

if ($installerPaths.Count -eq 0) {
    Write-SetupLog "Installer launch refused: no installer paths were supplied."
    exit 2
}

Write-SetupLog "Installer launch requested. HelmForge will not auto-elevate silently."
Write-SetupLog "Each installer must come from the official Thrustmaster page or the verified vJoy source."
$confirmation = Read-Host "Type LAUNCH INSTALLERS to launch the supplied installer paths"
if ($confirmation -ne "LAUNCH INSTALLERS") {
    Write-SetupLog "Installer launch cancelled: confirmation text did not match."
    exit 3
}

foreach ($installerPath in $installerPaths) {
    if (-not (Test-Path -LiteralPath $installerPath)) {
        Write-SetupLog ("Installer launch refused: path not found: {0}" -f $installerPath)
        exit 4
    }
}

foreach ($installerPath in $installerPaths) {
    Write-SetupLog ("Launching installer: {0}" -f $installerPath)
    Start-Process -FilePath $installerPath -Wait
}

Write-SetupLog "Installer process launch complete. Replug/reboot may be required before detection changes."
exit 0
