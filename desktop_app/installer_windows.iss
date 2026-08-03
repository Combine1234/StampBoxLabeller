#define AppName "StampBOX"
#if GetEnv("STAMPBOX_VERSION") == ""
  #define AppVersion "1.0.5"
#else
  #define AppVersion GetEnv("STAMPBOX_VERSION")
#endif
#define AppPublisher "StampBOX"
#define AppExeName "StampBOX.exe"
#ifndef BuildRoot
  #define BuildRoot SourcePath + "..\dist"
#endif

[Setup]
AppId={{6A24ED7F-4A06-4E63-9C7D-0BC8B3AA4256}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
PrivilegesRequired=lowest
OutputDir={#BuildRoot}\installer
OutputBaseFilename=StampBOX-Setup-{#AppVersion}
SetupIconFile={#SourcePath}\assets\StampBOX.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{#BuildRoot}\StampBOX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
