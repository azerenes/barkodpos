@echo off
chcp 65001 >nul
title BarkodPOS Build

cd /d "%~dp0"

echo ===================================
echo   BarkodPOS Windows Uygulama Paketi
echo ===================================
echo.

:: Install PyInstaller if not present
.venv\Scripts\python.exe -m pip install pyinstaller --quiet
if %errorlevel% neq 0 (
    echo [HATA] PyInstaller yuklenemedi
    pause
    exit /b 1
)

echo [1/4] MSVC runtime DLL'leri bulunuyor...

:: Visual C++ runtime DLL'lerini pakete ekle (hicbir ek kurulum gerektirmesin)
set MSVC_DLLS=
set MSVC_SRC=%SystemRoot%\System32

if exist "%MSVC_SRC%\msvcp140.dll" set MSVC_DLLS=%MSVC_DLLS% --add-data "%MSVC_SRC%\msvcp140.dll;."
if exist "%MSVC_SRC%\msvcp140_1.dll" set MSVC_DLLS=%MSVC_DLLS% --add-data "%MSVC_SRC%\msvcp140_1.dll;."
if exist "%MSVC_SRC%\msvcp140_2.dll" set MSVC_DLLS=%MSVC_DLLS% --add-data "%MSVC_SRC%\msvcp140_2.dll;."
if exist "%MSVC_SRC%\vcruntime140.dll" set MSVC_DLLS=%MSVC_DLLS% --add-data "%MSVC_SRC%\vcruntime140.dll;."
if exist "%MSVC_SRC%\vcruntime140_1.dll" set MSVC_DLLS=%MSVC_DLLS% --add-data "%MSVC_SRC%\vcruntime140_1.dll;."
if exist "%MSVC_SRC%\concrt140.dll" set MSVC_DLLS=%MSVC_DLLS% --add-data "%MSVC_SRC%\concrt140.dll;."

echo MSVC DLL eklenecek: %MSVC_DLLS%

echo [2/4] Uygulama paketleniyor...

:: NOT: UPX devre disi (SmartScreen + antivirus yanlis alarm)
.venv\Scripts\pyinstaller --noconfirm --clean --noupx ^
    --name "BarkodPOS" ^
    --windowed ^
    --add-data "app/templates;app/templates" ^
    --add-data "app/static;app/static" ^
    --add-data "app/__init__.py;app" ^
    --add-data "app/models.py;app" ^
    --add-data "app/auth_helper.py;app" ^
    --add-data "app/update_helper.py;app" ^
    --add-data "app/printer_helper.py;app" ^
    --add-data "app/routes;app/routes" ^
    --add-data "config.py;." ^
    --add-data ".env;." ^
    --add-data "updater.bat;." ^
    %MSVC_DLLS% ^
    --hidden-import flask ^
    --hidden-import flask_sqlalchemy ^
    --hidden-import sqlalchemy ^
    --hidden-import pymysql ^
    --hidden-import cryptography ^
    --hidden-import serial ^
    --hidden-import serial.tools.list_ports ^
    --collect-all PyQt5 ^
    --collect-all PyQtWebEngine ^
    desktop_app.py

if %errorlevel% neq 0 (
    echo [HATA] Paketleme basarisiz
    pause
    exit /b 1
)

echo [3/4] Veritabani kopyalaniyor...
if exist instance (
    xcopy /E /I /Y instance "dist\BarkodPOS\instance" >nul
)

:: ANGLE (OpenGL ES -> DirectX) DLL'lerini _internal kokune kopyala
:: Boylece QtWebEngineProcess.exe onlari kolayca bulur
if exist "dist\BarkodPOS\_internal\PyQt5\Qt5\bin\libEGL.dll" (
    copy /Y "dist\BarkodPOS\_internal\PyQt5\Qt5\bin\libEGL.dll" "dist\BarkodPOS\_internal\" >nul
    copy /Y "dist\BarkodPOS\_internal\PyQt5\Qt5\bin\libGLESv2.dll" "dist\BarkodPOS\_internal\" >nul
    copy /Y "dist\BarkodPOS\_internal\PyQt5\Qt5\bin\d3dcompiler_47.dll" "dist\BarkodPOS\_internal\" >nul
    echo ANGLE DLL'leri _internal kokune kopyalandi
)

echo [4/4] Gecici dosyalar temizleniyor...
if exist build rmdir /S /Q build >nul
if exist BarkodPOS.spec del /F /Q BarkodPOS.spec >nul

echo.
echo ===================================
echo   PAKET HAZIR!
echo   dist\BarkodPOS\BarkodPOS.exe
echo ===================================
echo.
echo NOT: Uygulama ilk acilista admin kullanicisini
echo otomatik olusturur.
echo NOT2: UPX kapali (antivirus uyari vermesin diye)
echo       MSVC runtime DLL'leri paketin icine eklendi
echo       (kullanici ek kurulum yapmak zorunda degil)
echo.
pause
