@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD (
  where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD set "PYCMD=C:\Users\c\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
%PYCMD% scripts\serve_review.py --open
if errorlevel 1 pause
