@echo off
setlocal
title Sospana Sonke - Build AAB (v5)
cd /d "%~dp0"
set "JDK17=C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot"
set "PATH=%JDK17%\bin;%PATH%"
set "SDK=C:\Android\Sdk"
set "ANDROID_HOME=%SDK%"

echo ---- creating tools junction (Bubblewrap expects SDK\tools\bin\sdkmanager) ----
if not exist "%SDK%\tools\bin\sdkmanager.bat" (
  if exist "%SDK%\tools" rmdir "%SDK%\tools" 2>nul
  mklink /J "%SDK%\tools" "%SDK%\cmdline-tools\latest"
) else ( echo tools junction already present )

echo ---- accepting licenses ----
(for /L %%i in (1,1,60) do @echo y) | "%SDK%\cmdline-tools\latest\bin\sdkmanager.bat" --licenses >nul 2>&1
echo ---- installing build-tools 36.1.0 + platform android-36 ----
call "%SDK%\cmdline-tools\latest\bin\sdkmanager.bat" "build-tools;36.1.0" "platforms;android-36" "platform-tools"

echo ---- bubblewrap config + doctor ----
call bubblewrap updateConfig --jdkPath "%JDK17%" --androidSdkPath "%SDK%"
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
