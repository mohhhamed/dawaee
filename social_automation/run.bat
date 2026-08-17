@echo off
REM ============================================================
REM  تشغيل نظام أتمتة السوشيال ميديا على ويندوز بضغطة واحدة
REM ============================================================
cd /d "%~dp0"

REM أنشئ البيئة الافتراضية أول مرة
if not exist ".venv" (
    echo [1/3] انشاء البيئة الافتراضية...
    python -m venv .venv
)

echo [2/3] تثبيت المتطلبات...
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

REM انسخ ملف الاعدادات اول مرة
if not exist ".env" (
    copy .env.example .env >nul
    echo تم انشاء ملف .env — افتحه واملا المفاتيح عند الحاجة.
)

echo [3/3] تشغيل الخادم على http://127.0.0.1:8000
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
