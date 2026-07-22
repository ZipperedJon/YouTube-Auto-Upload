@echo off
REM ============================================================
REM  Builds YouTubeAutoUpload.exe using PyInstaller.
REM  Just double-click this file (or run it from a terminal).
REM ============================================================

setlocal

echo Installing/updating dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo.
  echo ERROR: pip install failed. Make sure Python is installed and on PATH.
  pause
  exit /b 1
)

echo.
echo Building the .exe (this can take a minute)...
python -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "YouTubeAutoUpload" ^
  youtube_auto_upload.py

if errorlevel 1 (
  echo.
  echo ERROR: build failed.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  Done! Your program is here:
echo    dist\YouTubeAutoUpload.exe
echo ============================================================
pause
endlocal
