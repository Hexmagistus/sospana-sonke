@echo off
setlocal
title Sospana Sonke - Build AAB (v4)
cd /d "%~dp0"
set "JDK17=C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot"
set "PATH=%JDK17%\bin;%PATH%"
echo ---- setting bubblewrap config ----
call bubblewrap updateConfig --jdkPath "%JDK17%" --androidSdkPath "C:\Android\Sdk"
echo ---- doctor ----
call bubblewrap doctor
if not exist "%~dp0keystore.secrets.bat" (
  echo ERROR: %~dp0keystore.secrets.bat not found.
  echo Create it locally ^(git-ignored, never commit it^) with these two lines:
  echo   set "BUBBLEWRAP_KEYSTORE_PASSWORD=your-password"
  echo   set "BUBBLEWRAP_KEY_PASSWORD=your-password"
  exit /b 1
)
call "%~dp0keystore.secrets.bat"
echo ---- build ----
call bubblewrap build --skipPwaValidation
if exist "app-release-bundle.aab" (
  copy /y "app-release-bundle.aab" "%USERPROFILE%\Downloads\SospanaSonke-release.aab" >nul
  echo. & echo ================= SUCCESS =================
  for %%A in ("app-release-bundle.aab") do echo AAB size: %%~zA bytes
  echo AAB at %USERPROFILE%\Downloads\SospanaSonke-release.aab
) else ( echo. & echo FAILED-NO-AAB - see log )
endlocal
