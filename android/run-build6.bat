@echo off
cd /d "%~dp0"
echo Running build-aab6.bat - full output is being written to build-log6.txt ...
call build-aab6.bat > build-log6.txt 2>&1
echo. >> build-log6.txt
echo EXIT CODE: %errorlevel% >> build-log6.txt
echo.
echo ================================================
echo Build finished. Full output saved to build-log6.txt
echo ================================================
pause
