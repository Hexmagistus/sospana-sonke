@echo off
setlocal enabledelayedexpansion
title Sospana Sonke - Build AAB
echo ==== Sospana Sonke : building signed Android App Bundle ====

cd /d "%~dp0"
echo Working dir: %CD%

REM ---- detect JDK (needs 17+) ----
set "JDK="
if exist "%JAVA_HOME%\bin\java.exe" set "JDK=%JAVA_HOME%"
if not defined JDK if exist "C:\Program Files\Android\Android Studio\jbr\bin\java.exe" set "JDK=C:\Program Files\Android\Android Studio\jbr"
if not defined JDK for /d %%D in ("%USERPROFILE%\.jdks\*") do if exist "%%D\bin\java.exe" set "JDK=%%D"
if not defined JDK (echo ERROR: No JDK found. Open Android Studio once, or set JAVA_HOME. & exit /b 1)
echo JDK: !JDK!

REM ---- detect Android SDK ----
set "SDK="
if exist "%ANDROID_HOME%\platform-tools" set "SDK=%ANDROID_HOME%"
if not defined SDK if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools" set "SDK=%LOCALAPPDATA%\Android\Sdk"
if not defined SDK if exist "%USERPROFILE%\android-sdk\platform-tools" set "SDK=%USERPROFILE%\android-sdk"
if not defined SDK if exist "%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools" set "SDK=%USERPROFILE%\AppData\Local\Android\Sdk"
if not defined SDK (echo ERROR: Android SDK not found. Open Android Studio - SDK Manager once. & exit /b 1)
echo SDK: !SDK!

set "PATH=!JDK!\bin;%PATH%"

REM ---- bubblewrap config (skips first-run JDK/SDK download prompts) ----
if not exist "%USERPROFILE%\.bubblewrap" mkdir "%USERPROFILE%\.bubblewrap"
set "J=!JDK:\=\\!"
set "S=!SDK:\=\\!"
> "%USERPROFILE%\.bubblewrap\config.json" echo {"jdkPath":"!J!","androidSdkPath":"!S!"}
echo Wrote bubblewrap config.

REM ---- ensure bubblewrap ----
call bubblewrap --version >nul 2>&1
if errorlevel 1 (echo Installing bubblewrap... & call npm install -g @bubblewrap/cli)

REM ---- upload keystore ----
if not exist "android.keystore" (
  echo Creating upload keystore...
  "!JDK!\bin\keytool" -genkeypair -v -keystore android.keystore -alias sospana -keyalg RSA -keysize 2048 -validity 10000 -storepass ***REMOVED*** -keypass ***REMOVED*** -dname "CN=Sospana Sonke, O=Sospana Sonke, L=Johannesburg, C=ZA"
) else ( echo Keystore already exists - reusing. )

set "BUBBLEWRAP_KEYSTORE_PASSWORD=***REMOVED***"
set "BUBBLEWRAP_KEY_PASSWORD=***REMOVED***"

echo ---- generating Android project from twa-manifest.json ----
call bubblewrap update --skipVersionUpgrade
echo ---- building signed bundle ----
call bubblewrap build --skipPwaValidation

if exist "app-release-bundle.aab" (
  copy /y "app-release-bundle.aab" "%USERPROFILE%\Downloads\SospanaSonke-release.aab" >nul
  echo.
  echo ================= SUCCESS =================
  echo AAB: %USERPROFILE%\Downloads\SospanaSonke-release.aab
) else (
  echo.
  echo BUILD DID NOT PRODUCE app-release-bundle.aab - see log above.
)

echo.
echo ---- UPLOAD KEY SHA-256 (for Digital Asset Links / testing) ----
"!JDK!\bin\keytool" -list -v -keystore android.keystore -alias sospana -storepass ***REMOVED*** | findstr /i "SHA256:"
echo.
echo NOTE: For production, use the App signing SHA-256 from Play Console after upload.
endlocal
