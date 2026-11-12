; VisiLens Windows x64 installer — Inno Setup 6.3 or later.
; Build only from the validated PyInstaller onedir directory.
#ifndef MyAppVersion
  #define MyAppVersion "0.7.0"
#endif

[Setup]
AppId=GiuClab.VisiLens
AppName=VisiLens
AppVersion={#MyAppVersion}
AppVerName=VisiLens {#MyAppVersion}
AppPublisher=GiuClab
AppPublisherURL=https://github.com/GiuClab/VisiLens
AppSupportURL=https://github.com/GiuClab/VisiLens/issues
AppUpdatesURL=https://github.com/GiuClab/VisiLens/releases
AppCopyright=Copyright (c) 2026 GiuClab and VisiLens contributors
DefaultDirName={localappdata}\Programs\VisiLens
DefaultGroupName=VisiLens
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
WizardSizePercent=110
SetupIconFile=..\build\visilens.ico
UninstallDisplayIcon={app}\VisiLens.exe
LicenseFile=..\LICENSE
OutputDir=..\dist\installer
OutputBaseFilename=VisiLens-Setup-{#MyAppVersion}-x64
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=yes
UsePreviousLanguage=yes
VersionInfoProductName=VisiLens
VersionInfoProductVersion={#MyAppVersion}
VersionInfoDescription=VisiLens Windows Setup
VersionInfoCompany=GiuClab
VersionInfoCopyright=Copyright (c) 2026 GiuClab and VisiLens contributors

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The installer does not contain portable.flag or a user's portable settings.
; Preserve PyInstaller's _internal directory and all its runtime dependencies.
Source: "..\dist\VisiLens\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "portable.flag,VisiLensData\*,VisiLensData"

[Icons]
Name: "{autoprograms}\VisiLens"; Filename: "{app}\VisiLens.exe"; IconFilename: "{app}\VisiLens.exe"
Name: "{autodesktop}\VisiLens"; Filename: "{app}\VisiLens.exe"; IconFilename: "{app}\VisiLens.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VisiLens.exe"; Description: "{cm:LaunchProgram,VisiLens}"; Flags: nowait postinstall skipifsilent
