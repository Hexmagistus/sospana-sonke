@echo off
setlocal enabledelayedexpansion
title Sospana Sonke - Build AAB (v8)
cd /d "%~dp0"
echo ==== Sospana Sonke : build AAB (v8) ====
echo Working dir: %CD%

REM ---- JDK 17, via a space-free junction (bubblewrap's internal java.exe ----
REM ---- invocation for apksigner/zipalign does not quote paths with spaces, ----
REM ---- and "C:\Program Files\Eclipse Adoptium\..." breaks it) ----
set "JDK17REAL=C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot"
set "JDK17=C:\jdk17-nospace"
if not exist "%JDK17REAL%\bin\java.exe" (
  echo ERROR: JDK 17 not found at %JDK17REAL%
  exit /b 1
)
if not exist "%JDK17%\bin\java.exe" (
  if exist "%JDK17%" rmdir "%JDK17%" 2>nul
  mklink /J "%JDK17%" "%JDK17REAL%" >nul
)
if not exist "%JDK17%\bin\java.exe" (
  echo ERROR: failed to create space-free JDK junction at %JDK17%
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

echo ---- bubblewrap config + doctor (pointing at space-free JDK path: %JDK17%) ----
call bubblewrap updateConfig --jdkPath "%JDK17%" --androidSdkPath "%SDK%"
call bubblewrap doctor

if not exist "%~dp0keystore.secrets.bat" (
  echo ERROR: %~dp0keystore.secrets.bat not found.
  exit /b 1
)
call "%~dp0keystore.secrets.bat"

echo ---- regenerating project from twa-manifest.json ----
call bubblewrap update --skipVersionUpgrade

echo ---- building signed bundle ----
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
)
endlocal
