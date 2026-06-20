import sys, os, threading, time, urllib.request, atexit, signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# QtWebEngine crash fix: sandbox + GPU + OpenGL sorunlarını önle
os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--no-sandbox --disable-gpu --disable-software-rasterizer --use-gl=swiftshader --disable-accelerated-2d-canvas --disable-accelerated-video-decode --ignore-gpu-blocklist'
os.environ['QT_OPENGL'] = 'angle'
os.environ['QSG_RENDERER_LOOP'] = 'basic'
os.environ['QT_QUICK_BACKEND'] = 'software'

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSplashScreen, QSystemTrayIcon, QMenu, QFileDialog
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineDownloadItem
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QFont, QPainter, QColor, QIcon

from app import create_app

FLASK_HOST = '127.0.0.1'
FLASK_PORT = 5000
BASE_URL = f'http://{FLASK_HOST}:{FLASK_PORT}'

def get_icon():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'barkodpos.ico')
    return QIcon(p) if os.path.exists(p) else QIcon()

flask_app = create_app()
flask_thread = None

def flask_ready():
    try:
        r = urllib.request.urlopen(f'{BASE_URL}/auth/personel', timeout=2)
        return r.status == 200
    except Exception:
        return False

def run_flask():
    flask_app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, use_reloader=False)

def make_splash():
    from PyQt5.QtGui import QPixmap, QPainter
    pixmap = QPixmap(400, 280)
    pixmap.fill(QColor('#1a1a2e'))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.white)
    p.setFont(QFont('Segoe UI', 28, QFont.Bold))
    p.drawText(pixmap.rect(), Qt.AlignCenter, 'BarkodPOS')
    p.setPen(QColor('#aaaaaa'))
    p.setFont(QFont('Segoe UI', 12))
    r = pixmap.rect().adjusted(0, 50, 0, 0)
    p.drawText(r, Qt.AlignCenter, 'Başlatılıyor...')
    p.end()
    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    return splash

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('BarkodPOS')
        self.resize(1280, 800)
        self.setMinimumSize(800, 600)

        self.browser = QWebEngineView()
        self.browser.page().profile().downloadRequested.connect(self.handle_download)
        self.browser.setUrl(QUrl(BASE_URL))
        self.setCentralWidget(self.browser)

        tray_menu = QMenu()
        show_action = tray_menu.addAction('Göster')
        show_action.triggered.connect(self.show_and_raise)
        quit_action = tray_menu.addAction('Çıkış')
        quit_action.triggered.connect(self.do_quit)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip('BarkodPOS')
        ico = get_icon()
        self.tray_icon.setIcon(ico if not ico.isNull() else self.style().standardIcon(self.style().SP_ComputerIcon))
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_clicked)
        self.tray_icon.show()

    def handle_download(self, download: QWebEngineDownloadItem):
        suggested = download.suggestedFileName() or 'export.csv'
        file_path, _ = QFileDialog.getSaveFileName(self, 'Dosyayı Kaydet', suggested)
        if file_path:
            download.setPath(file_path)
            download.accept()

    def show_and_raise(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def tray_clicked(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_and_raise()

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage('BarkodPOS', 'Arka planda çalışıyor.', QSystemTrayIcon.Information, 2000)
            event.ignore()
        else:
            event.accept()

    def do_quit(self):
        self.tray_icon.hide()
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName('BarkodPOS')
    app.setOrganizationName('BarkodPOS')
    app_icon = get_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    splash = make_splash()
    splash.show()
    app.processEvents()

    global flask_thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    timeout = 30
    while not flask_ready() and timeout > 0:
        time.sleep(1)
        timeout -= 1
        splash.showMessage(f'\nSunucu başlatılıyor... ({30 - timeout}s)', Qt.AlignCenter, QColor('#aaaaaa'))
        app.processEvents()

    splash.close()

    if not flask_ready():
        error_html = '''
        <html><body style="background:#1a1a2e;color:white;font-family:sans-serif;
        display:flex;align-items:center;justify-content:center;height:100vh;margin:0;
        flex-direction:column;text-align:center">
        <h1>Sunucu Başlatılamadı</h1>
        <p>Flask sunucusu 30 saniye içinde başlamadı.</p>
        <p style="color:#888">Güncelleme sırasında dosyalar bozulmuş olabilir.<br>
        Lütfen <a href="https://github.com/azerenes/barkodpos/releases" style="color:#4da6ff">
        en son sürümü</a> indirip tekrar kurun.</p>
        </body></html>
        '''
        import tempfile
        err_path = os.path.join(tempfile.gettempdir(), 'barkodpos_error.html')
        with open(err_path, 'w', encoding='utf-8') as f:
            f.write(error_html)
        window = MainWindow()
        window.browser.setUrl(QUrl.fromLocalFile(err_path))
    else:
        window = MainWindow()
    window.show()

    def cleanup():
        os._exit(0)

    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
