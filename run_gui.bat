@echo off
title UCircle QA Automation - GUI Mode
chcp 65001 >nul
echo ========================================================
echo   UCircle Video QA Automation - Khởi động giao diện GUI
echo ========================================================
echo.

REM Kiểm tra python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python trong hệ thống PATH. Vui lòng cài đặt Python 3.10 trở lên.
    pause
    exit /b 1
)

echo Đang khởi chạy ứng dụng giao diện...
python gui.py
if %errorlevel% neq 0 (
    echo.
    echo [LỖI] Có sự cố khi khởi chạy. Vui lòng kiểm tra lại dependencies.
    pause
)
