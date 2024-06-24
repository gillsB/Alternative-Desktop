# Alternative-Desktop

Alternative Desktop

So far, a basic barebones example of how to create and build then distribute a python program

##Base Req: Python, pip (https://pip.pypa.io/en/stable/installation/), pyinstaller (pip install pyinstaller), Inno setup compiler (https://jrsoftware.org/isdl.php)

Just for the example Req: pyautogui (pip install pyautogui)

###Step 1:
open command prompt
cd to file location ie. C:\...\github\Alternative-Desktop
create the /dist/AlternativeDesktop.exe 
pyinstaller --onefile --noconsole AlternativeDesktop.py

Should create the folders: build, dist, and AlternativeDesktop.spec

###Step 2: Inno setup, open new: **MAKE SURE TO CHANGE GUID**
```
; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{**GUID**}
AppName=Alternative Desktop
AppVersion=1.0
DefaultDirName={commonpf}\Alternative Desktop
DefaultGroupName=Alternative Desktop
OutputDir=.
OutputBaseFilename=Alternative Desktop Installer
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\AlternativeDesktop.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Alternative Desktop"; Filename: "{app}\main.exe"
Name: "{group}\{cm:UninstallProgram,Alternative Desktop}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Alternative Desktop"; Filename: "{app}\AlternativeDesktop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AlternativeDesktop.exe"; Description: "{cm:LaunchProgram,Alternative Desktop}"; Flags: nowait postinstall skipifsilent

```
Save this file as AlternativeDesktopInstaller.iss

make this into installer
open AlternativeDesktopInstaller.iss, Build -> compile, To get the Installer exe

to install, run .exe


