import threading
import time
import json
import urllib.request
import urllib.error
import logging
from datetime import date

BARCODE, NAME, PRICE, STOCK = range(4)


class BarkodPOSBot:
    def __init__(self, app):
        self.app = app
        self.token = ''
        self.allowed_chat_ids = []
        self._thread = None
        self._running = False
        self._last_error = ''
        self._offset = 0
        self._user_data = {}

    def _get_settings(self):
        with self.app.app_context():
            from app.models import Setting
            token_s = Setting.query.filter_by(key='telegram_bot_token').first()
            chat_s = Setting.query.filter_by(key='telegram_allowed_chat_ids').first()
            self.token = (token_s.value or '').strip() if token_s else ''
            raw = (chat_s.value or '').strip() if chat_s else ''
            self.allowed_chat_ids = [int(x.strip()) for x in raw.split(',') if x.strip().lstrip('-').isdigit()]

    def _api(self, method, params=None):
        url = f'https://api.telegram.org/bot{self.token}/{method}'
        data = json.dumps(params).encode() if params else None
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            self._last_error = str(e)
            return None

    def _send(self, chat_id, text, parse_mode=''):
        params = {'chat_id': chat_id, 'text': text}
        if parse_mode:
            params['parse_mode'] = parse_mode
        self._api('sendMessage', params)

    def _auth(self, chat_id):
        return chat_id in self.allowed_chat_ids

    def _handle(self, msg):
        chat_id = msg.get('chat', {}).get('id', 0)
        text = msg.get('text', '').strip()
        if not self._auth(chat_id):
            self._send(chat_id, '\u274c Yetkiniz yok.')
            return
        if text == '/start':
            self._send(chat_id,
                '\U0001f44b BarkodPOS Telegram Botuna Ho\u015f Geldiniz!\n\n'
                'Kullan\u0131labilir komutlar:\n'
                '/stok - Kritik stoktaki \u00fcr\u00fcnler\n'
                '/stokkontrol <barkod/urun> - \u00dcr\u00fcn stok sorgula\n'
                '/urunekle - Yeni \u00fcr\u00fcn ekle (ad\u0131m ad\u0131m)\n'
                '/rapor - G\u00fcnl\u00fck sat\u0131\u015f raporu\n'
                '/yardim - Yard\u0131m')
        elif text == '/yardim':
            self._send(chat_id,
                '\U0001f4cb Komut Listesi:\n\n'
                '/stok - Stogu kritik seviyenin alt\u0131nda olan \u00fcr\u00fcnleri listeler\n'
                '/stokkontrol <barkod/urun_adi> - Belirli bir \u00fcr\u00fcn\u00fcn stok ve fiyat bilgisini g\u00f6sterir\n'
                '/urunekle - Ad\u0131m ad\u0131m yeni \u00fcr\u00fcn ekleme sihirbaz\u0131\n'
                '/rapor - Bug\u00fcnk\u00fc sat\u0131\u015f raporunu g\u00f6sterir\n'
                '/yardim - Bu mesaj\u0131 g\u00f6sterir')
        elif text.startswith('/stokkontrol'):
            query = text[len('/stokkontrol'):].strip()
            if not query:
                self._send(chat_id, 'Kullan\u0131m: /stokkontrol <barkod veya \u00fcr\u00fcn ad\u0131>')
                return
            with self.app.app_context():
                from app.models import Product
                prod = Product.query.filter(
                    (Product.barcode == query) | (Product.name.ilike(f'%{query}%')),
                    Product.is_active == True
                ).first()
                if not prod:
                    self._send(chat_id, '\u274c \u00dcr\u00fcn bulunamad\u0131.')
                    return
                durum = '\U0001f4e6 Stoksuz' if prod.is_stockless else '\U0001f4e6 Stoklu'
                self._send(chat_id,
                    f'\U0001f4e6 *{prod.name}*\n'
                    f'Barkod: `{prod.barcode}`\n'
                    f'Stok: {float(prod.stock_qty or 0):.1f}\n'
                    f'Min Stok: {float(prod.min_stock_qty or 0):.1f}\n'
                    f'Al\u0131\u015f: {float(prod.purchase_price or 0):.2f}\u20ba\n'
                    f'Sat\u0131\u015f: {float(prod.sale_price or 0):.2f}\u20ba\n'
                    f'Birim: {prod.unit or "Adet"}\n'
                    f'Kategori: {prod.category.name if prod.category else "-"}\n'
                    f'Durum: {durum}', parse_mode='Markdown')
        elif text == '/stok':
            with self.app.app_context():
                from app.models import Product
                products = Product.query.filter(
                    Product.stock_qty <= Product.min_stock_qty,
                    Product.is_active == True
                ).order_by(Product.stock_qty.asc()).all()
                if not products:
                    self._send(chat_id, '\u2705 Kritik stokta \u00fcr\u00fcn bulunmuyor.')
                    return
                lines = ['\u26a0\ufe0f *Kritik Stoktaki \u00dcr\u00fcnler:*\n']
                for p in products[:50]:
                    lines.append(
                        f'\u2022 {p.name}\n'
                        f'  Stok: {float(p.stock_qty or 0):.1f} / Min: {float(p.min_stock_qty or 0):.1f}\n'
                        f'  Barkod: `{p.barcode}`')
                if len(products) > 50:
                    lines.append(f'\n...ve {len(products) - 50} \u00fcr\u00fcn daha')
                self._send(chat_id, '\n'.join(lines), parse_mode='Markdown')
        elif text == '/rapor':
            with self.app.app_context():
                from app.models import Sale
                from app import db
                today = date.today()
                sales = Sale.query.filter(
                    db.func.date(Sale.created_at) == today,
                    Sale.status == 'completed'
                ).all()
                total = sum(float(s.grand_total) for s in sales)
                count = len(sales)
                cash_total = sum(float(s.grand_total) for s in sales if s.payment_method == 'cash')
                card_total = total - cash_total
                self._send(chat_id,
                    f'\U0001f4ca *Bug\u00fcnk\u00fc Sat\u0131\u015f Raporu*\n\n'
                    f'Toplam Sat\u0131\u015f: {count} adet\n'
                    f'Toplam Ciro: {total:.2f}\u20ba\n'
                    f'Nakit: {cash_total:.2f}\u20ba\n'
                    f'Kart: {card_total:.2f}\u20ba\n\n'
                    f'Tarih: {today.strftime("%d.%m.%Y")}', parse_mode='Markdown')
        elif text == '/urunekle':
            self._user_data[chat_id] = {'step': 'barcode'}
            self._send(chat_id, '\u00dcr\u00fcn barkod numaras\u0131n\u0131 girin:')
        elif text == '/cancel' and chat_id in self._user_data:
            self._user_data.pop(chat_id, None)
            self._send(chat_id, '\u274c \u0130\u015flem iptal edildi.')
        elif chat_id in self._user_data:
            self._handle_urunekle_step(chat_id, text)
        else:
            self._send(chat_id, 'Bilinmeyen komut. /yardim yaz\u0131n.')

    def _handle_urunekle_step(self, chat_id, text):
        data = self._user_data.get(chat_id)
        if not data:
            return
        step = data.get('step')
        if step == 'barcode':
            data['barcode'] = text
            data['step'] = 'name'
            self._send(chat_id, '\u00dcr\u00fcn ad\u0131n\u0131 girin:')
        elif step == 'name':
            data['name'] = text
            data['step'] = 'price'
            self._send(chat_id, 'Sat\u0131\u015f fiyat\u0131n\u0131 girin (\u00f6rn: 50):')
        elif step == 'price':
            try:
                data['price'] = float(text.replace(',', '.'))
            except ValueError:
                self._send(chat_id, '\u274c Ge\u00e7ersiz fiyat. L\u00fctfen say\u0131 girin:')
                return
            data['step'] = 'stock'
            self._send(chat_id, 'Stok miktar\u0131n\u0131 girin (stoksuz i\u00e7in 0):')
        elif step == 'stock':
            try:
                stock = float(text.replace(',', '.'))
            except ValueError:
                self._send(chat_id, '\u274c Ge\u00e7ersiz miktar. L\u00fctfen say\u0131 girin:')
                return
            self._user_data.pop(chat_id, None)
            with self.app.app_context():
                from app import db
                from app.models import Product
                if Product.query.filter_by(barcode=data['barcode']).first():
                    self._send(chat_id, '\u274c Bu barkod zaten kay\u0131tl\u0131.')
                    return
                try:
                    p = Product(
                        barcode=data['barcode'],
                        name=data['name'],
                        sale_price=data['price'],
                        stock_qty=stock,
                        min_stock_qty=0,
                        is_stockless=(stock == 0),
                        is_active=True,
                    )
                    db.session.add(p)
                    db.session.commit()
                    self._send(chat_id,
                        f'\u2705 \u00dcr\u00fcn ba\u015far\u0131yla eklendi!\n\n'
                        f'\u0130sim: {p.name}\n'
                        f'Barkod: {p.barcode}\n'
                        f'Fiyat: {float(p.sale_price):.2f}\u20ba\n'
                        f'Stok: {float(p.stock_qty):.1f}')
                except Exception as e:
                    db.session.rollback()
                    self._send(chat_id, f'\u274c Hata: {str(e)}')

    def _poll(self):
        params = {'timeout': 30, 'offset': self._offset} if self._offset else {'timeout': 30}
        result = self._api('getUpdates', params)
        if result and result.get('ok'):
            for update in result.get('result', []):
                self._offset = update['update_id'] + 1
                msg = update.get('message')
                if msg:
                    try:
                        self._handle(msg)
                    except Exception as e:
                        logging.error(f'Telegram bot handle error: {e}')

    def run(self):
        self._get_settings()
        if not self.token:
            self._last_error = 'Token yok'
            return
        if not self.allowed_chat_ids:
            self._last_error = 'Chat ID yok'
            return
        self._running = True
        self._last_error = ''
        while self._running:
            try:
                self._poll()
            except Exception as e:
                self._last_error = str(e)
                time.sleep(5)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = False
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._thread = None

    @property
    def status(self):
        alive = self._thread and self._thread.is_alive()
        if not self.token:
            return {'running': False, 'status': 'token_yok'}
        if not self.allowed_chat_ids:
            return {'running': False, 'status': 'chat_id_yok'}
        if alive:
            return {'running': True, 'status': 'calisiyor', 'last_error': self._last_error}
        return {'running': False, 'status': 'durduruldu', 'last_error': self._last_error}
