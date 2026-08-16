@echo off
REM ============================================================
REM  Sospana Sonke - GitHub setup launcher
REM  Just double-click this file. It runs setup-github.ps1.
REM ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-github.ps1"
echo.
pause
