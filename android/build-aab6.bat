@echo off
setlocal enabledelayedexpansion
title Sospana Sonke - Build AAB (v6)
cd /d "%~dp0"
echo ==== Sospana Sonke : build AAB (v6) ====
echo Working dir: %CD%

REM ---- JDK 17 (required by current Bubblewrap/Gradle/AGP combo) ----
set "JDK17=C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot"
if not exist "%JDK17%\bin\java.exe" (
  echo ERROR: JDK 17 not found at %JDK17%
  echo Install Temurin 17 from https://adoptium.net/temurin/releases/?version=17 or update this path.
  exit /b 1
)
set "PATH=%JDK17%\bin;%PATH%"

REM ---- Android SDK ----
set "SDK=C:\Android\Sdk"
if not exist "%SDK%\cmdline-tools\latest\bin\sdkmanager.bat" (
  echo ERROR: sdkmanager not found under %SDK%\cmdline-tools\latest
  exit /b 1
)
set "ANDROID_HOME=%SDK%"

echo ---- creating tools junction (Bubblewrap expects SDK\tools\bin\sdkmanager) ----
if not exist "%SDK%\tools\bin\sdkmanager.bat" (
  if exist "%SDK%\tools" rmdir "%SDK%\tools" 2>nul
  mklink /J "%SDK%\tools" "%SDK%\cmdline-tools\latest" >nul
) else ( echo tools junction already present )

echo ---- accepting SDK licenses ----
(for /L %%i in (1,1,60) do @echo y) | "%SDK%\cmdline-tools\latest\bin\sdkmanager.bat" --licenses >nul 2>&1

echo ---- installing build-tools 36.1.0 + platform android-36 (current Play Console target API) ----
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

echo ---- regenerating project from twa-manifest.json ----
call bubblewrap update --skipVersionUpgrade

echo ---- building signed bundle (Gradle daemon disabled via gradle.properties - avoids the ----
echo ---- "Unable to establish loopback connection" socket error seen in earlier attempts)   ----
call bubblewrap build --skipPwaValidation

if exist "app-release-bundle.aab" (
  copy /y "app-release-bundle.aab" "%USERPROFILE%\Downloads\SospanaSonke-release.aab" >nul
  echo.
  echo ================= SUCCESS =================
  for %%A in ("app-release-bundle.aab") do echo AAB size: %%~zA bytes
  echo AAB at %USERPROFILE%\Downloads\SospanaSonke-release.aab
  echo.
  echo ---- UPLOAD KEY SHA-256 (for reference - Play App Signing will issue its own for distribution) ----
  "%JDK17%\bin\keytool" -list -v -keystore android.keystore -alias sospana -storepass "%BUBBLEWRAP_KEYSTORE_PASSWORD%" | findstr /i "SHA256:"
) else (
  echo.
  echo FAILED-NO-AAB - see log above.
  echo If you still see "Unable to establish loopback connection": temporarily disconnect
  echo any VPN ^(e.g. ProtonVPN^) and disable antivirus real-time protection, then retry -
  echo those are the most common causes of that specific error on Windows.
)
endlocal
