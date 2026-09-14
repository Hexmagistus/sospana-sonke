@echo off
cd /d "%~dp0"
echo ==================================================
echo   Sospana Sonke - push Career Agent page
echo ==================================================
echo.
taskkill /F /IM git.exe >nul 2>&1
ping -n 3 127.0.0.1 >nul
if exist ".git\index.lock" del /f /q ".git\index.lock"
if exist ".git\HEAD.lock" del /f /q ".git\HEAD.lock"
if exist ".git\config.lock" del /f /q ".git\config.lock"
if exist ".git\refs\heads\main.lock" del /f /q ".git\refs\heads\main.lock"
echo Committing...
git add -A
git -c commit.gpgsign=false -c user.email="lungani@sospana-sonke.local" -c user.name="Lungani Tshabalala" commit -m "Add Sospana Sonke Career Agent page and nav link" > update-log.txt 2>&1
echo Uploading to GitHub...
git push origin main >> update-log.txt 2>&1
echo. >> update-log.txt
echo === recent commits === >> update-log.txt
git log --oneline -5 >> update-log.txt 2>&1
echo.
type update-log.txt
echo.
echo --------------------------------------------------
echo Finished.
echo --------------------------------------------------
pause
