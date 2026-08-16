@echo off
cd /d "%~dp0"
echo ==================================================
echo   Sospana Sonke - force-clear git locks and push
echo ==================================================
echo.
echo Stopping any stuck git processes...
taskkill /F /IM git.exe >nul 2>&1
taskkill /F /IM git-remote-https.exe >nul 2>&1
ping -n 3 127.0.0.1 >nul
echo Removing stale lock files...
if exist ".git\index.lock" del /f /q ".git\index.lock"
if exist ".git\HEAD.lock" del /f /q ".git\HEAD.lock"
if exist ".git\config.lock" del /f /q ".git\config.lock"
if exist ".git\refs\heads\main.lock" del /f /q ".git\refs\heads\main.lock"
if exist ".git\ORIG_HEAD.lock" del /f /q ".git\ORIG_HEAD.lock"
echo.
echo Committing the fix...
git add -A
git -c commit.gpgsign=false -c user.email="lungani@sospana-sonke.local" -c user.name="Lungani Tshabalala" commit -m "Fix Render build: pin Python 3.12, bump psycopg2-binary" > update-log.txt 2>&1
echo Uploading to GitHub...
git push origin main >> update-log.txt 2>&1
echo. >> update-log.txt
echo === recent commits === >> update-log.txt
git log --oneline -3 >> update-log.txt 2>&1
echo.
type update-log.txt
echo.
echo --------------------------------------------------
echo Finished. Go back to Claude and say "pushed3".
echo --------------------------------------------------
pause
