@echo off
rem Alqor Studio - IDE-ni acir. Iki defe klikleyin.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0brauzerde-ac.ps1" -Numune studio
if errorlevel 1 pause
