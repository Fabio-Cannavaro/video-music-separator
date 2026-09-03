@echo off
chcp 65001 >nul
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo 전용 Python 환경이 없습니다.
    echo README.md의 기본 환경 설치를 먼저 진행해 주세요.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "app\sound_separator_app.py"
if errorlevel 1 pause
