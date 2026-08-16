@echo off
cd /d "%~dp0"
echo ==================================================
echo   Sospana Sonke - clear lock, commit, upload fix
echo ==================================================
echo.
if exist ".git\index.lock" (
  echo Removing stale git lock file...
  del /f /q ".git\index.lock"
)
echo Committing the fix...
git add -A
git -c commit.gpgsign=false -c user.email="lungani@sospana-sonke.local" -c user.name="Lungani Tshabalala" commit -m "Fix Render build: pin Python 3.12, bump psycopg2-binary" > update-log.txt 2>&1
echo Uploading to GitHub...
git push origin main >> update-log.txt 2>&1
echo.
type update-log.txt
echo.
echo --------------------------------------------------
echo Finished. Go back to Claude and say "pushed2".
echo --------------------------------------------------
pause
