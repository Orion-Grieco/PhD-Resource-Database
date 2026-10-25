; Inno Setup script for the desktop app. build.ps1 compiles it with the values from
; app_info.json passed as /D defines, e.g.:
;   ISCC.exe /DAppName="PhD Program Finder" /DAppVersion=0.1.0 ... desktop\installer.iss
; AppId is written "{{" + GUID because "{" starts an Inno constant.
; Installs per user (no admin prompt). Uninstalling keeps the user's data in
; %LOCALAPPDATA%\<AppName> (database, saved pages, logs).

#ifndef AppName
  #error Run through build.ps1 (AppName and other defines are required)
#endif

[Setup]
AppId={{#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename={#ExeName}-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#ExeName}.exe
CloseApplications=yes
#ifdef IconFile
SetupIconFile={#IconFile}
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Remove files from older versions so stale modules can't linger after an upgrade.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}.exe"
Name: "{group}\{#AppName} data folder"; Filename: "{localappdata}\{#AppName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
