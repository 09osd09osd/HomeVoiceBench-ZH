@echo off
setlocal
cd /d "%~dp0"
set "HV_REVIEW_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%HV_REVIEW_PY%" (
  "%HV_REVIEW_PY%" -X utf8 scripts\serve_review.py --open
  goto finish
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -X utf8 scripts\serve_review.py --open
  goto finish
)
where python >nul 2>nul
if not errorlevel 1 (
  python -X utf8 scripts\serve_review.py --open
  goto finish
)
echo Python was not found. Open review\index.html and select the dataset folder.
pause
exit /b 1
:finish
if errorlevel 1 pause
