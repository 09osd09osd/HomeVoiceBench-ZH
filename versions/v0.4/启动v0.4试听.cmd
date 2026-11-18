@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "HOMEVOICE_REVIEW_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%HOMEVOICE_REVIEW_PYTHON%" (
  "%HOMEVOICE_REVIEW_PYTHON%" -X utf8 scripts\serve_review.py --port 18788 --open
) else (
  py -3 scripts\serve_review.py --port 18788 --open
)
if errorlevel 1 pause
