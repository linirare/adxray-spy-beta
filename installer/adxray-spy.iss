#define MyAppName "ADXRay Spy"
#define MyAppVersion "1.1.0-beta.2.4"
#define MyAppPublisher "linirare"
#define MyAppExeName "adxray-spy.exe"

[Setup]
AppId={{2D92B810-4788-4FC1-A2D4-8918736CFB7A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ADXRay Spy
DefaultGroupName=ADXRay Spy
OutputDir=..\dist\release
OutputBaseFilename=adxray-spy-setup-win-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\adxray-spy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ADXRay Spy"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ADXRay Spy"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 ADXRay Spy"; Flags: nowait postinstall skipifsilent
