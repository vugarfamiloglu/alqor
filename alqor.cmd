@echo off
rem Alqor CLI - "alqor yeni ad", "alqor sina", "alqor islet" ...
rem Bu qovlugu PATH-a elave edin ve ya tam yolla cagirin.
setlocal
set PYTHONIOENCODING=utf-8
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0alqorc\alqorc.py" %*
) else (
    python "%~dp0alqorc\alqorc.py" %*
)
exit /b %errorlevel%
