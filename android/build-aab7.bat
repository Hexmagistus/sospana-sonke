@echo off
cd /d "%~dp0"
call build-aab6.bat > build-log7.txt 2>&1
echo.
echo ==== build-aab6.bat finished, exit code %ERRORLEVEL% ====
echo Log written to build-log7.txt
echo.
type build-log7.txt
echo.
echo ==== Press any key to close this window ====
pause
