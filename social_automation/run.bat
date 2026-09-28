@echo off
chcp 65001 >nul
REM ============================================================
REM  تشغيل نظام أتمتة السوشيال ميديا على ويندوز بضغطة واحدة
REM ============================================================
cd /d "%~dp0"

REM أنشئ البيئة الافتراضية أول مرة
if not exist ".venv" (
    echo [1/3] انشاء البيئة الافتراضية...
    python -m venv .venv
)

echo [2/3] تثبيت المتطلبات... (قد يستغرق دقيقة او اكثر - انتظر من فضلك)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet --no-cache-dir --disable-pip-version-check
pip install -r requirements.txt --no-cache-dir --disable-pip-version-check

REM انسخ ملف الاعدادات اول مرة
if not exist ".env" (
    copy .env.example .env >nul
    echo تم انشاء ملف .env — افتحه واملا المفاتيح عند الحاجة.
)

echo.
echo [3/3] تشغيل الخادم... افتح المتصفح على:  http://127.0.0.1:8000
echo (لايقاف البرنامج: اضغط Ctrl+C او اغلق هذه النافذة)
echo.
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
