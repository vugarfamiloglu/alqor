@echo off
rem Alqor - desktop numunesini (06) acir. Iki defe klikleyin.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0brauzerde-ac.ps1" -Numune 06
if errorlevel 1 pause
