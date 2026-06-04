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

echo [1/3] Uygulama paketleniyor...

if exist "C:\upx\upx.exe" (
    set UPX_DIR=C:\upx
) else if exist "%USERPROFILE%\Downloads\upx-4.2.4-win64\upx.exe" (
    set UPX_DIR=%USERPROFILE%\Downloads\upx-4.2.4-win64
) else (
    set UPX_DIR=
)

if not "%UPX_DIR%"=="" (
    set UPX_ARG=--upx-dir "%UPX_DIR%"
) else (
    set UPX_ARG=
)

.venv\Scripts\pyinstaller --noconfirm --clean %UPX_ARG% ^
    --name "BarkodPOS" ^
    --windowed ^
    --add-data "app/templates;app/templates" ^
    --add-data "app/static;app/static" ^
    --add-data "app/__init__.py;app" ^
    --add-data "app/models.py;app" ^
    --add-data "app/auth_helper.py;app" ^
    --add-data "app/update_helper.py;app" ^
    --add-data "app/routes;app/routes" ^
    --add-data "config.py;." ^
    --add-data ".env;." ^
    --add-data "updater.bat;." ^
    --hidden-import flask ^
    --hidden-import flask_sqlalchemy ^
    --hidden-import sqlalchemy ^
    --hidden-import pymysql ^
    --hidden-import cryptography ^
    --collect-all PyQt5 ^
    --collect-all PyQtWebEngine ^
    desktop_app.py

if %errorlevel% neq 0 (
    echo [HATA] Paketleme basarisiz
    pause
    exit /b 1
)

echo [2/3] Veritabani kopyalaniyor...
if exist instance (
    xcopy /E /I /Y instance "dist\BarkodPOS\instance" >nul
)

echo [3/3] README ve sikca sorulan sorular kopyalaniyor...
if exist README.md copy /Y README.md "dist\BarkodPOS\README.md" >nul

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
echo.
pause
