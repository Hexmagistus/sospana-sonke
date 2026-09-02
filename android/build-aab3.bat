@echo off
setlocal
title Sospana Sonke - Build AAB (v3)
cd /d "%~dp0"
set "JDK=C:\Program Files\Android\Android Studio\jbr"
set "PATH=%JDK%\bin;%PATH%"
set "ANDROID_HOME=C:\Android\Sdk"
if not exist "%USERPROFILE%\.bubblewrap" mkdir "%USERPROFILE%\.bubblewrap"
copy /y "bwconfig.json" "%USERPROFILE%\.bubblewrap\config.json" >nul
echo ==== bubblewrap config in use: ====
type "%USERPROFILE%\.bubblewrap\config.json"
echo.
if not exist "%~dp0keystore.secrets.bat" (
  echo ERROR: %~dp0keystore.secrets.bat not found.
  echo Create it locally ^(git-ignored, never commit it^) with these two lines:
  echo   set "BUBBLEWRAP_KEYSTORE_PASSWORD=your-password"
  echo   set "BUBBLEWRAP_KEY_PASSWORD=your-password"
  exit /b 1
)
call "%~dp0keystore.secrets.bat"
echo ---- doctor ----
call bubblewrap doctor
echo ---- build ----
call bubblewrap build --skipPwaValidation
if exist "app-release-bundle.aab" (
  copy /y "app-release-bundle.aab" "%USERPROFILE%\Downloads\SospanaSonke-release.aab" >nul
  echo. & echo ================= SUCCESS =================
  for %%A in ("app-release-bundle.aab") do echo AAB size: %%~zA bytes
  echo AAB at %USERPROFILE%\Downloads\SospanaSonke-release.aab
) else ( echo. & echo FAILED-NO-AAB - see log above )
endlocal
