@echo off
title UCircle QA Automation - CLI Mode
chcp 65001 >nul
echo ========================================================
echo   UCircle Video QA Automation - Chế độ Dòng lệnh (CLI)
echo ========================================================
echo.

python main.py
if %errorlevel% neq 0 (
    echo.
    echo [LỖI] Đã xảy ra sự cố khi chạy tool.
)
pause
