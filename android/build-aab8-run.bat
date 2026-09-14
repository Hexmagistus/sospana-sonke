@echo off
cd /d "%~dp0"
call build-aab8.bat > build-log8.txt 2>&1
echo.
echo ==== build-aab8.bat finished, exit code %ERRORLEVEL% ====
echo Log written to build-log8.txt
echo.
type build-log8.txt
echo.
echo ==== Press any key to close this window ====
pause
