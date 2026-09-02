@echo off
chcp 65001 >nul
title نظام المرتبات الشامل - Payroll System
echo ==============================================
echo   نظام المرتبات الشامل - Payroll System
echo   شركة خاصة + جهة حكومية + عملاء يومي/ساعة
echo ==============================================
echo.

REM ---- التحقق من وجود Python ----
where python >nul 2>nul
if errorlevel 1 (
    echo [خطأ] لم يتم العثور على Python.
    echo يرجى تثبيت Python 3.9 أو أحدث من https://www.python.org/downloads/
    echo ثم تأكد من تحديد خيار "Add Python to PATH" أثناء التثبيت.
    pause
    exit /b 1
)

echo جاري تجهيز المكتبات المطلوبة...
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [تنبيه] حدثت مشكلة أثناء تثبيت المكتبات.
    echo جاري المحاولة مرة أخرى بدون -quiet...
    python -m pip install -r requirements.txt
)

echo.
echo جاري فتح المتصفح تلقائيا...
REM انتظار بسيط حتى يبدأ السيرفر ثم فتح المتصفح
start /b cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

python app.py
pause
