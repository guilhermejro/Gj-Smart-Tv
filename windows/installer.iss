; Inno Setup 6.3+ — instalação por usuário, sem privilégios de administrador.
#define MyAppName "GJ Smart TV"
#define MyAppVersion "0.2.0"

[Setup]
AppId={{B3E6A1D2-6F0B-4C77-9C52-5A1F0E2D9A41}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\installer
OutputBaseFilename=GJ-Smart-TV-Setup-{#MyAppVersion}
SetupIconFile=..\app\resources\icon.ico
UninstallDisplayIcon={app}\gj-smart-tv.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; Flags: unchecked

[Files]
Source: "..\dist\gj-smart-tv\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\gj-smart-tv.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\gj-smart-tv.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\gj-smart-tv.exe"; Description: "Abrir o {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\gj-smart-tv');
    if DirExists(DataDir) then
      if MsgBox('Remover também suas fontes IPTV, favoritos, histórico e logs?',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
