@echo off
cd /d "%~dp0"
echo ==================================================
echo   Sospana Sonke - upload the Render build fix
echo ==================================================
echo.
git add -A
git -c commit.gpgsign=false -c user.email="lungani@sospana-sonke.local" -c user.name="Lungani Tshabalala" commit -m "Fix Render build: pin Python 3.12, bump psycopg2-binary" > update-log.txt 2>&1
git push origin main >> update-log.txt 2>&1
type update-log.txt
echo.
echo --------------------------------------------------
echo Finished. Go back to Claude and say "pushed".
echo --------------------------------------------------
pause
