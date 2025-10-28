@echo off
title 🔧 بناء ملف EXE لبرنامج People Manager
color 0A

echo ===============================================
echo   جاري إنشاء النسخة التنفيذية من البرنامج...
echo ===============================================
echo.

REM حذف الملفات القديمة لتفادي الأخطاء
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist app_people_manager.spec del app_people_manager.spec

echo 📦 جاري تجهيز PyInstaller...
pyinstaller --noconsole --onefile --clean ^
--add-data "Amiri-Regular.ttf;." ^
--hidden-import numpy.core._methods ^
--hidden-import numpy.lib.format ^
app_people_manager.py

echo.
echo ===============================================
echo ✅ تم إنشاء الملف التنفيذي بنجاح!
echo 📁 المسار: dist\app_people_manager.exe
echo ===============================================
pause
