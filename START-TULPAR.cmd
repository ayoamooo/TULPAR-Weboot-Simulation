@echo off
set "TULPAR_WEBOTS=C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
if not exist "%TULPAR_WEBOTS%" (
  echo Webots was not found at the configured path.
  pause
  exit /b 1
)
start "" "%TULPAR_WEBOTS%" --mode=realtime "%~dp0worlds\tulpar_showcase.wbt"
