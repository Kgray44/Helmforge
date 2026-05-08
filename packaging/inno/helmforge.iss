; HelmForge Phase 18C installer script.
; This installer installs packaged app files only. User data under {localappdata}\HelmForge is preserved by design.
; It does not install vJoy, HOTAS drivers, services, login auto-start entries, tray managers, or Bridge lifecycle automation.

#define AppName "HelmForge"
#define AppDisplayName "HelmForge - HOTAS Control Panel V3"
#ifndef AppVersion
#define AppVersion "0.1.0-dev"
#endif
#ifndef AppPublisher
#define AppPublisher "HelmForge"
#endif
#ifndef SourceDir
#define SourceDir "..\dist\HelmForge"
#endif
#ifndef AppIcon
#define AppIcon "..\..\assets\app_icon.ico"
#endif

[Setup]
AppId={{7F9285EC-B07E-4D0A-A56F-1EAEF786C60D}
AppName={#AppDisplayName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\HelmForge
DefaultGroupName=HelmForge
DisableProgramGroupPage=yes
OutputDir=..\installer
OutputBaseFilename=HelmForge-Setup-{#AppVersion}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
UninstallDisplayName={#AppDisplayName}
UninstallDisplayIcon={app}\HelmForge.exe
#if FileExists(AppIcon)
SetupIconFile={#AppIcon}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "launchafterinstall"; Description: "Launch HelmForge after install"; GroupDescription: "After installation:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
#if FileExists(AppIcon)
Name: "{group}\HelmForge"; Filename: "{app}\HelmForge.exe"; WorkingDir: "{app}"; IconFilename: "{#AppIcon}"
Name: "{autodesktop}\HelmForge"; Filename: "{app}\HelmForge.exe"; Tasks: desktopicon; WorkingDir: "{app}"; IconFilename: "{#AppIcon}"
#else
Name: "{group}\HelmForge"; Filename: "{app}\HelmForge.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\HelmForge"; Filename: "{app}\HelmForge.exe"; Tasks: desktopicon; WorkingDir: "{app}"
#endif

[Run]
Filename: "{app}\HelmForge.exe"; Description: "Launch HelmForge"; Flags: nowait postinstall skipifsilent; Tasks: launchafterinstall
