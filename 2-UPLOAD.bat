@echo off
cd /d "%~dp0"
echo ==========================================
echo  Uploading Sospana Sonke to GitHub...
echo  If a "Sign in to GitHub" window appears,
echo  click Authorize (no typing needed).
echo ==========================================
echo.
git push -u origin main > push-log.txt 2>&1
type push-log.txt
echo.
echo ------------------------------------------
echo Finished. Come back to Claude and say "check".
echo ------------------------------------------
pause
