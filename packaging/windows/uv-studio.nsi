!ifndef UV_RELEASE_ROOT
  !error "UV_RELEASE_ROOT must point to the already verified portable release root"
!endif
!ifndef UV_RELEASE_ID
  !error "UV_RELEASE_ID must be supplied by the release build"
!endif
!ifndef UV_PRODUCT_VERSION
  !error "UV_PRODUCT_VERSION must be supplied by the release build"
!endif
!ifndef UV_OUTPUT_FILE
  !error "UV_OUTPUT_FILE must be supplied by the release build"
!endif

!include "MUI2.nsh"
!include "LogicLib.nsh"

Unicode true
Name "UV Studio"
OutFile "${UV_OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\UV Studio"
RequestExecutionLevel user
SetCompressor zlib
ShowInstDetails show
ShowUninstDetails show
BrandingText "UV Studio"

Var VerifyExit
Var VerifyOutput

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\versions\${UV_RELEASE_ID}\backend\uv-studio-backend.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch UV Studio"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function VerifyInstalledRelease
  nsExec::ExecToStack /TIMEOUT=300000 '"$INSTDIR\versions\${UV_RELEASE_ID}\backend\uv-studio-backend.exe" --verify-release'
  Pop $VerifyExit
  Pop $VerifyOutput
FunctionEnd

Function RecordVerificationFailure
  CreateDirectory "$LOCALAPPDATA\UV Studio"
  CreateDirectory "$LOCALAPPDATA\UV Studio\logs"
  FileOpen $1 "$LOCALAPPDATA\UV Studio\logs\installer-verification-error.txt" w
  FileWrite $1 "release=${UV_RELEASE_ID}$\r$\n"
  FileWrite $1 "verifier_exit=$VerifyExit$\r$\n"
  FileWrite $1 "$VerifyOutput$\r$\n"
  FileClose $1
FunctionEnd

Section "UV Studio" SEC_MAIN
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  CreateDirectory "$INSTDIR\versions"
  ; A diagnostic belongs only to the current installation attempt.
  Delete "$LOCALAPPDATA\UV Studio\logs\installer-verification-error.txt"

  ; Exact reinstall: reuse only an already deep-verified identical release.
  IfFileExists "$INSTDIR\versions\${UV_RELEASE_ID}\backend\uv-studio-backend.exe" 0 install_release
  Call VerifyInstalledRelease
  StrCmp $VerifyExit "0" activate_release
  RMDir /r "$INSTDIR\versions\${UV_RELEASE_ID}"

install_release:
  SetOutPath "$INSTDIR\versions\${UV_RELEASE_ID}"
  File /r "${UV_RELEASE_ROOT}\*"

  ; The copied payload is not activated until its own D-044 deep verifier accepts it.
  Call VerifyInstalledRelease
  StrCmp $VerifyExit "0" activate_release
  Call RecordVerificationFailure
  RMDir /r "$INSTDIR\versions\${UV_RELEASE_ID}"
  ; /SD keeps /S installations fail-closed instead of waiting on an invisible dialog.
  MessageBox MB_ICONSTOP|MB_OK "UV Studio installation failed integrity verification. No shortcut was activated. See the UV Studio logs directory for diagnostics." /SD IDOK
  SetErrorLevel 2
  Quit

activate_release:
  FileOpen $0 "$INSTDIR\current-release.txt" w
  FileWrite $0 "${UV_RELEASE_ID}$\r$\n"
  FileClose $0

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\UV Studio"
  CreateShortcut "$SMPROGRAMS\UV Studio\UV Studio.lnk" "$INSTDIR\versions\${UV_RELEASE_ID}\backend\uv-studio-backend.exe"
  CreateShortcut "$SMPROGRAMS\UV Studio\Uninstall UV Studio.lnk" "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UV Studio" "DisplayName" "UV Studio"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UV Studio" "DisplayVersion" "${UV_PRODUCT_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UV Studio" "DisplayIcon" "$INSTDIR\versions\${UV_RELEASE_ID}\backend\uv-studio-backend.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UV Studio" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UV Studio" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UV Studio" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UV Studio" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UV Studio" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current

  Delete "$SMPROGRAMS\UV Studio\UV Studio.lnk"
  Delete "$SMPROGRAMS\UV Studio\Uninstall UV Studio.lnk"
  RMDir "$SMPROGRAMS\UV Studio"

  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UV Studio"

  Delete "$INSTDIR\current-release.txt"
  RMDir /r "$INSTDIR\versions"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  ; Deliberately do not touch $LOCALAPPDATA\UV Studio. D-045 user data survives uninstall.
SectionEnd
