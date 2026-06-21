import os, sys, json, urllib.request, urllib.error, zipfile, tempfile, shutil, subprocess, ssl

CURRENT_VERSION = '1.3.0'
GITHUB_OWNER = 'azerenes'
GITHUB_REPO = 'BarkodPOS'

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def check_update():
    ctx = ssl.create_default_context()
    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BarkodPOS'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return {'error': f'GitHub\'a bağlanılamadı: {str(e)}'}

    tag = data.get('tag_name', '')
    remote_version = tag.lstrip('v')
    if not remote_version:
        return {'error': 'Sürüm bilgisi alınamadı'}

    has_update = _compare_versions(remote_version, CURRENT_VERSION) > 0
    download_url = None
    for asset in data.get('assets', []):
        name = asset.get('name', '')
        if name.endswith('.zip') and 'BarkodPOS' in name:
            download_url = asset.get('browser_download_url')
            break

    return {
        'current_version': CURRENT_VERSION,
        'remote_version': remote_version,
        'has_update': has_update,
        'download_url': download_url,
        'notes': data.get('body', '').strip(),
        'tag_name': tag,
    }

def _compare_versions(v1, v2):
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]
    for a, b in zip(parts1, parts2):
        if a != b:
            return a - b
    return len(parts1) - len(parts2)

def download_and_apply(info):
    url = info.get('download_url')
    if not url:
        return {'error': 'İndirme linki bulunamadı'}

    tmp = tempfile.mkdtemp(prefix='barkodpos_update_')
    zip_path = os.path.join(tmp, 'update.zip')

    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'BarkodPOS'})
        with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            downloaded = 0
            with open(zip_path, 'wb') as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return {'error': f'İndirme hatası: {str(e)}'}

    extract_dir = os.path.join(tmp, 'extracted')
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return {'error': f'Zip açma hatası: {str(e)}'}

    items = os.listdir(extract_dir)
    if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
        update_root = os.path.join(extract_dir, items[0])
    else:
        update_root = extract_dir

    app_dir = get_app_dir()
    bat_path = os.path.join(app_dir, 'updater.bat')

    bat_content = f"""@echo off
chcp 65001 >nul
title BarkodPOS Güncelleme
echo BarkodPOS güncelleniyor...

:: Flask sunucusunun kapanmasi icin bekle
timeout /t 2 /nobreak >nul

:: Eski sureci zorla kapat
taskkill /f /im BarkodPOS.exe >nul 2>&1
timeout /t 3 /nobreak >nul

:: Eski dosyalari temizle (birden fazla deneme)
set RETRY=0
:RETRY_INTERNAL
if exist "%~dp0_internal" (
    rmdir /s /q "%~dp0_internal" >nul 2>&1
    if exist "%~dp0_internal" (
        set /a RETRY+=1
        if !RETRY! lss 5 (
            timeout /t 2 /nobreak >nul
            goto RETRY_INTERNAL
        )
    )
)

:: Yeni dosyalari kopyala
xcopy /E /I /Y "{update_root}\\_internal" "%~dp0_internal" >nul 2>&1
copy /Y "{update_root}\\BarkodPOS.exe" "%~dp0\\BarkodPOS.exe" >nul 2>&1

:: Gecici dosyalari temizle
rmdir /s /q "{tmp}" >nul 2>&1

echo Güncelleme tamam!
start "" "%~dp0BarkodPOS.exe"

:: Kendini sil
(goto) 2>nul & del "%~f0"
"""
    try:
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return {'error': f'Güncelleme betiği oluşturulamadı: {str(e)}'}

    return {
        'success': True,
        'bat_path': bat_path,
        'tmp_dir': tmp,
    }
