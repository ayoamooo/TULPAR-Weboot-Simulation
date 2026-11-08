@echo off
set "WEBOTS_HOME=C:\Program Files\Webots"
set "TULPAR_WEBOTS=%WEBOTS_HOME%\msys64\mingw64\bin\webotsw.exe"
if not exist "%TULPAR_WEBOTS%" set "TULPAR_WEBOTS=%WEBOTS_HOME%\msys64\mingw64\bin\webots.exe"
if not exist "%TULPAR_WEBOTS%" (
  echo Webots was not found under "%WEBOTS_HOME%".
  pause
  exit /b 1
)
start "" /D "%WEBOTS_HOME%" "%TULPAR_WEBOTS%" --mode=realtime "%~dp0worlds\tulpar_showcase.wbt"
