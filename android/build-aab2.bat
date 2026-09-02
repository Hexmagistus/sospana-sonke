@echo off
setlocal enabledelayedexpansion
title Sospana Sonke - Build AAB (v2)
echo ==== Sospana Sonke : build AAB (SDK at C:\Android\Sdk) ====
cd /d "%~dp0"

set "JDK=C:\Program Files\Android\Android Studio\jbr"
set "SDK=C:\Android\Sdk"
if not exist "%JDK%\bin\java.exe" (echo ERROR: JDK not found at %JDK% & exit /b 1)
if not exist "%SDK%\cmdline-tools\latest\bin\sdkmanager.bat" (echo ERROR: sdkmanager not at %SDK% & exit /b 1)
set "PATH=%JDK%\bin;%PATH%"
set "ANDROID_HOME=%SDK%"

echo Writing bubblewrap config...
if not exist "%USERPROFILE%\.bubblewrap" mkdir "%USERPROFILE%\.bubblewrap"
> "%USERPROFILE%\.bubblewrap\config.json" echo {"jdkPath":"C:\\Program Files\\Android\\Android Studio\\jbr","androidSdkPath":"C:\\Android\\Sdk"}

echo Accepting SDK licenses...
(for /L %%i in (1,1,60) do @echo y) | "%SDK%\cmdline-tools\latest\bin\sdkmanager.bat" --licenses >nul 2>&1

echo Installing SDK components (platform-tools, android-35, build-tools 35)...
call "%SDK%\cmdline-tools\latest\bin\sdkmanager.bat" "platform-tools" "platforms;android-35" "build-tools;35.0.0"

if not exist "%~dp0keystore.secrets.bat" (
  echo ERROR: %~dp0keystore.secrets.bat not found.
  echo Create it locally ^(git-ignored, never commit it^) with these two lines:
  echo   set "BUBBLEWRAP_KEYSTORE_PASSWORD=your-password"
  echo   set "BUBBLEWRAP_KEY_PASSWORD=your-password"
  exit /b 1
)
call "%~dp0keystore.secrets.bat"

echo ---- regenerating project ----
call bubblewrap update --skipVersionUpgrade
echo ---- building signed bundle ----
call bubblewrap build --skipPwaValidation

if exist "app-release-bundle.aab" (
  copy /y "app-release-bundle.aab" "%USERPROFILE%\Downloads\SospanaSonke-release.aab" >nul
  echo. & echo ================= SUCCESS ================= & echo AAB at %USERPROFILE%\Downloads\SospanaSonke-release.aab
  for %%A in ("app-release-bundle.aab") do echo AAB size: %%~zA bytes
) else (
  echo. & echo BUILD DID NOT PRODUCE app-release-bundle.aab - see log above.
)
endlocal
