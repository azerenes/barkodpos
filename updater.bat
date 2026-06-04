@echo off
chcp 65001 >nul
title BarkodPOS Güncelleme
echo BarkodPOS güncelleniyor...
timeout /t 3 /nobreak >nul

:: Eski _internal klasörünü temizle
if exist "%~dp0_internal" (
    rmdir /s /q "%~dp0_internal" >nul 2>&1
)

:: Yeni dosyaları kopyala (update_root değişkeni update_helper.py tarafından yazılır)
REM Bu dosya update_helper.py tarafından dinamik oluşturulur.

echo Güncelleme tamam!
start "" "%~dp0BarkodPOS.exe"

:: Kendini sil
(goto) 2>nul & del "%~f0"
