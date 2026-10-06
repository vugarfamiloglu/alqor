@echo off
rem Alqor - numuneni brauzerde acir. Iki defe klikleyin.
rem Basqa numune: Brauzerde-ac.cmd 05   (05 veb, 06 desktop, 08 vidjetler)
set NUMUNE=%1
if "%NUMUNE%"=="" set NUMUNE=08
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0brauzerde-ac.ps1" -Numune %NUMUNE%
if errorlevel 1 pause
