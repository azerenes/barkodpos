import asyncio
import threading
import logging
from datetime import date
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

BARCODE, NAME, PRICE, STOCK = range(4)


class BarkodPOSBot:
    def __init__(self, app):
        self.app = app
        self.token = ''
        self.allowed_chat_ids = []
        self.application = None
        self._thread = None
        self._loop = None

    def _get_settings(self):
        with self.app.app_context():
            from app.models import Setting
            token_s = Setting.query.filter_by(key='telegram_bot_token').first()
            chat_s = Setting.query.filter_by(key='telegram_allowed_chat_ids').first()
            self.token = (token_s.value or '').strip() if token_s else ''
            raw = (chat_s.value or '').strip() if chat_s else ''
            self.allowed_chat_ids = [int(x.strip()) for x in raw.split(',') if x.strip().lstrip('-').isdigit()]

    def _auth(self, update: Update) -> bool:
        return update.effective_chat.id in self.allowed_chat_ids

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._auth(update):
            await update.message.reply_text('\u274c Yetkiniz yok.')
            return
        await update.message.reply_text(
            '\U0001f44b BarkodPOS Telegram Botuna Ho\u015f Geldiniz!\n\n'
            'Kullan\u0131labilir komutlar:\n'
            '/stok - Kritik stoktaki \u00fcr\u00fcnler\n'
            '/stokkontrol <barkod/urun> - \u00dcr\u00fcn stok sorgula\n'
            '/urunekle - Yeni \u00fcr\u00fcn ekle (ad\u0131m ad\u0131m)\n'
            '/rapor - G\u00fcnl\u00fck sat\u0131\u015f raporu\n'
            '/yardim - Yard\u0131m'
        )

    async def _yardim(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._auth(update):
            await update.message.reply_text('\u274c Yetkiniz yok.')
            return
        await update.message.reply_text(
            '\U0001f4cb Komut Listesi:\n\n'
            '/stok - Stogu kritik seviyenin alt\u0131nda olan \u00fcr\u00fcnleri listeler\n'
            '/stokkontrol <barkod/urun_adi> - Belirli bir \u00fcr\u00fcn\u00fcn stok ve fiyat bilgisini g\u00f6sterir\n'
            '/urunekle - Ad\u0131m ad\u0131m yeni \u00fcr\u00fcn ekleme sihirbaz\u0131\n'
            '/rapor - Bug\u00fcnk\u00fc sat\u0131\u015f raporunu g\u00f6sterir\n'
            '/yardim - Bu mesaj\u0131 g\u00f6sterir'
        )

    async def _stok(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._auth(update):
            await update.message.reply_text('\u274c Yetkiniz yok.')
            return
        with self.app.app_context():
            from app.models import Product
            products = Product.query.filter(
                Product.stock_qty <= Product.min_stock_qty,
                Product.is_active == True
            ).order_by(Product.stock_qty.asc()).all()
            if not products:
                await update.message.reply_text('\u2705 Kritik stokta \u00fcr\u00fcn bulunmuyor.')
                return
            lines = ['\u26a0\ufe0f *Kritik Stoktaki \u00dcr\u00fcnler:*\n']
            for p in products[:50]:
                lines.append(
                    f'\u2022 {p.name}\n'
                    f'  Stok: {float(p.stock_qty or 0):.1f} / Min: {float(p.min_stock_qty or 0):.1f}\n'
                    f'  Barkod: `{p.barcode}`'
                )
            if len(products) > 50:
                lines.append(f'\n...ve {len(products) - 50} \u00fcr\u00fcn daha')
            await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')

    async def _stokkontrol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._auth(update):
            await update.message.reply_text('\u274c Yetkiniz yok.')
            return
        query = ' '.join(context.args)
        if not query:
            await update.message.reply_text('Kullan\u0131m: /stokkontrol <barkod veya \u00fcr\u00fcn ad\u0131>')
            return
        with self.app.app_context():
            from app.models import Product
            product = Product.query.filter(
                (Product.barcode == query) | (Product.name.ilike(f'%{query}%')),
                Product.is_active == True
            ).first()
            if not product:
                await update.message.reply_text('\u274c \u00dcr\u00fcn bulunamad\u0131.')
                return
            is_stockless = product.is_stockless
            durum = '\U0001f4e6 Stoksuz' if is_stockless else '\U0001f4e6 Stoklu'
            await update.message.reply_text(
                f'\U0001f4e6 *{product.name}*\n'
                f'Barkod: `{product.barcode}`\n'
                f'Stok: {float(product.stock_qty or 0):.1f}\n'
                f'Min Stok: {float(product.min_stock_qty or 0):.1f}\n'
                f'Al\u0131\u015f: {float(product.purchase_price or 0):.2f}\u20ba\n'
                f'Sat\u0131\u015f: {float(product.sale_price or 0):.2f}\u20ba\n'
                f'Birim: {product.unit or "Adet"}\n'
                f'Kategori: {product.category.name if product.category else "-"}\n'
                f'Durum: {durum}',
                parse_mode='Markdown'
            )

    async def _urunekle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._auth(update):
            await update.message.reply_text('\u274c Yetkiniz yok.')
            return ConversationHandler.END
        await update.message.reply_text('\u00dcr\u00fcn barkod numaras\u0131n\u0131 girin:')
        return BARCODE

    async def _urunekle_barcode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['barcode'] = update.message.text.strip()
        await update.message.reply_text('\u00dcr\u00fcn ad\u0131n\u0131 girin:')
        return NAME

    async def _urunekle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['name'] = update.message.text.strip()
        await update.message.reply_text('Sat\u0131\u015f fiyat\u0131n\u0131 girin (\u00f6rn: 50):')
        return PRICE

    async def _urunekle_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            context.user_data['price'] = float(update.message.text.strip().replace(',', '.'))
        except ValueError:
            await update.message.reply_text('\u274c Ge\u00e7ersiz fiyat. L\u00fctfen say\u0131 girin:')
            return PRICE
        await update.message.reply_text('Stok miktar\u0131n\u0131 girin (stoksuz \u00fcr\u00fcn i\u00e7in 0):')
        return STOCK

    async def _urunekle_stock(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            stock = float(update.message.text.strip().replace(',', '.'))
        except ValueError:
            await update.message.reply_text('\u274c Ge\u00e7ersiz miktar. L\u00fctfen say\u0131 girin:')
            return STOCK
        with self.app.app_context():
            from app import db
            from app.models import Product
            if Product.query.filter_by(barcode=context.user_data['barcode']).first():
                await update.message.reply_text('\u274c Bu barkod zaten kay\u0131tl\u0131.')
                return ConversationHandler.END
            try:
                p = Product(
                    barcode=context.user_data['barcode'],
                    name=context.user_data['name'],
                    sale_price=context.user_data['price'],
                    stock_qty=stock,
                    min_stock_qty=0,
                    is_stockless=(stock == 0),
                    is_active=True,
                )
                db.session.add(p)
                db.session.commit()
                await update.message.reply_text(
                    f'\u2705 \u00dcr\u00fcn ba\u015far\u0131yla eklendi!\n\n'
                    f'\u0130sim: {p.name}\n'
                    f'Barkod: {p.barcode}\n'
                    f'Fiyat: {float(p.sale_price):.2f}\u20ba\n'
                    f'Stok: {float(p.stock_qty):.1f}'
                )
            except Exception as e:
                db.session.rollback()
                await update.message.reply_text(f'\u274c Hata: {str(e)}')
        return ConversationHandler.END

    async def _urunekle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('\u274c \u0130\u015flem iptal edildi.')
        return ConversationHandler.END

    async def _rapor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._auth(update):
            await update.message.reply_text('\u274c Yetkiniz yok.')
            return
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
            await update.message.reply_text(
                f'\U0001f4ca *Bug\u00fcnk\u00fc Sat\u0131\u015f Raporu*\n\n'
                f'Toplam Sat\u0131\u015f: {count} adet\n'
                f'Toplam Ciro: {total:.2f}\u20ba\n'
                f'Nakit: {cash_total:.2f}\u20ba\n'
                f'Kart: {card_total:.2f}\u20ba\n\n'
                f'Tarih: {today.strftime("%d.%m.%Y")}',
                parse_mode='Markdown'
            )

    async def _error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logging.error(f'Telegram bot error: {context.error}')

    def _build(self):
        self.application = Application.builder().token(self.token).build()
        self.application.add_handler(CommandHandler('start', self._start))
        self.application.add_handler(CommandHandler('yardim', self._yardim))
        self.application.add_handler(CommandHandler('stok', self._stok))
        self.application.add_handler(CommandHandler('stokkontrol', self._stokkontrol))
        self.application.add_handler(CommandHandler('rapor', self._rapor))
        conv = ConversationHandler(
            entry_points=[CommandHandler('urunekle', self._urunekle_start)],
            states={
                BARCODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._urunekle_barcode)],
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._urunekle_name)],
                PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._urunekle_price)],
                STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._urunekle_stock)],
            },
            fallbacks=[CommandHandler('cancel', self._urunekle_cancel)],
        )
        self.application.add_handler(conv)
        self.application.add_error_handler(self._error)

    def run(self):
        self._get_settings()
        if not self.token:
            logging.warning('Telegram bot: token not configured, not starting')
            return
        self._build()
        self.application.run_polling()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        logging.info('Telegram bot thread started')

    def stop(self):
        if self.application:
            self.application.stop()
            self.application = None
