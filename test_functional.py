"""
BarkodPOS Fonksiyonel Test - Gercek kullanici senaryolari (duzeltilmis)
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

instance = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
for f in os.listdir(instance):
    if f.endswith('.db') or f.endswith('.db-shm') or f.endswith('.db-wal'):
        os.remove(os.path.join(instance, f))

from app import create_app, db
app = create_app()
from app.models import Sale, Product, Customer, Supplier, Expense

PASS = 0; FAIL = 0; ERRORS = []

def test(name, ok, detail=''):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f'  [OK] {name}')
    else:
        FAIL += 1
        msg = f'  [FAIL] {name}' + (f' - {detail}' if detail else '')
        print(msg)
        ERRORS.append(msg)

def section(title):
    print(f'\n=== {title} ===')

with app.test_client() as c:
    section('1. Admin Giris ve Tum Sayfalar')
    c.post('/auth/personel', data={'user_id': '1'}, follow_redirects=True)

    pages = [
        ('/', 'Dashboard'),
        ('/dashboard/', 'Dashboard (alias)'),
        ('/pos/', 'POS'),
        ('/stock/', 'Stok'),
        ('/stock/categories', 'Kategoriler'),
        ('/stock/labels', 'Etiket'),
        ('/stock/price-history', 'Fiyat Gecmisi'),
        ('/stock/set-products', 'Set Urunler'),
        ('/customer/', 'Cari'),
        ('/report/', 'Rapor'),
        ('/settings/', 'Ayarlar'),
        ('/cash/', 'Kasa'),
        ('/supplier/', 'Tedarikci'),
        ('/expense/', 'Gider'),
        ('/stock-count/', 'Stok Sayimi'),
        ('/cash-register/', 'Kasa Acilis/Kapanis'),
        ('/purchase/', 'Stok Giris/Cikis'),
        ('/purchase/invoices', 'Alis Faturasi'),
        ('/purchase/history', 'Stok Hareket Gecmisi'),
        ('/transfer/', 'Transfer'),
        ('/employee/', 'Personel'),
        ('/branch/', 'Subeler'),
    ]
    for url, label in pages:
        resp = c.get(url, follow_redirects=True)
        ok = resp.status_code == 200
        test(f'{label} ({url})', ok, f'HTTP {resp.status_code}' if not ok else '')

    section('2. JSON Endpointler')
    json_urls = ['/report/payment-data', '/report/weekly-data', '/diagnostic/info']
    for url in json_urls:
        resp = c.get(url)
        test(f'{url} JSON', resp.is_json, f'HTTP {resp.status_code}')
        if resp.is_json:
            test(f'{url} veri var', len(resp.get_json()) > 0)

    payment = c.get('/report/payment-data').get_json()
    test('payment-data debt YOK', 'debt' not in payment,
         'hala debt var!' if 'debt' in payment else '')

    diag = c.get('/diagnostic/info').get_json()
    for field in ['version', 'github_owner', 'github_repo', 'os', 'user_id', 'user_name', 'is_admin', 'time']:
        test(f'diagnostic.{field}', field in diag)
    test('diagnostic.version 1.1.2', diag.get('version') == '1.1.2')
    test('diagnostic.github_owner azerenes', diag.get('github_owner') == 'azerenes')

    section('3. Kategori ve Urun Olusturma')
    resp = c.post('/stock/add-category', data={'name': 'Test Kategori'}, follow_redirects=True)
    test('Kategori ekleme', resp.status_code == 200)

    resp = c.post('/stock/add', data={
        'barcode': 'TEST001', 'name': 'Test Urun',
        'category_id': '1', 'purchase_price': '10',
        'sale_price': '25', 'stock_qty': '100',
        'unit': 'Adet', 'tax_rate': '20'
    }, follow_redirects=True)
    test('Urun ekleme', resp.status_code == 200)

    section('4. POS - Hizli Satis')
    resp = c.post('/pos/quick-sale', json={'name': 'Anlik Urun', 'price': '50'})
    test('Hizli satis API', resp.is_json, f'HTTP {resp.status_code}')
    if resp.is_json:
        d = resp.get_json()
        test('Hizli satis basarili', d.get('success') is True or 'product' in d or 'id' in d,
             str(d)[:100])

    section('5. POS - Nakit Satis')
    resp = c.post('/pos/complete-sale', json={
        'items': [{'product_id': 1, 'qty': 2}],
        'payment_method': 'cash', 'discount': 0,
        'total_amount': 50, 'grand_total': 60
    })
    test('Nakit satis API', resp.is_json, f'HTTP {resp.status_code}')
    if resp.is_json:
        d = resp.get_json()
        test('Nakit satis basarili', d.get('success') is True, str(d)[:150])
        test('Fis numarasi var', bool(d.get('receipt_no')), str(d)[:150])

    section('6. POS - Kredi Karti Satis')
    resp = c.post('/pos/complete-sale', json={
        'items': [{'product_id': 1, 'qty': 1}],
        'payment_method': 'credit_card', 'discount': 0,
        'total_amount': 25, 'grand_total': 30
    })
    test('Kartli satis API', resp.is_json, f'HTTP {resp.status_code}')
    if resp.is_json:
        d = resp.get_json()
        test('Kartli satis basarili', d.get('success') is True, str(d)[:150])

    section('7. POS - Veresiye Engellendi')
    resp = c.post('/pos/complete-sale', json={
        'items': [{'product_id': 1, 'qty': 1}],
        'payment_method': 'debt', 'discount': 0,
        'total_amount': 25, 'grand_total': 25
    })
    if resp.is_json:
        d = resp.get_json()
        test('Veresiye reddedildi', d.get('error') is not None, str(d)[:100])

    section('8. Musteri Islemleri')
    resp = c.post('/customer/add', data={
        'name': 'Test Musteri', 'phone': '5551234567',
        'email': 'test@test.com', 'address': 'Test adres'
    }, follow_redirects=True)
    test('Musteri ekleme', resp.status_code == 200)

    resp = c.get('/customer/extract/1')
    test('Hesap ekstresi', resp.status_code == 200)

    section('9. Tedarikci Islemleri')
    resp = c.post('/supplier/add', data={
        'name': 'Test Tedarikci', 'phone': '5559876543'
    }, follow_redirects=True)
    test('Tedarikci ekleme', resp.status_code == 200)

    section('10. Gider Islemleri')
    resp = c.post('/expense/add', data={
        'amount': '150', 'category': 'Kira',
        'description': 'Mart kira', 'payment_method': 'cash'
    }, follow_redirects=True)
    test('Gider ekleme', resp.status_code == 200)

    section('11. Kasa Acilis/Kapanis')
    resp = c.post('/cash-register/open', data={
        'opening_balance': '500', 'notes': 'Test acilis'
    }, follow_redirects=True)
    test('Kasa acma', resp.status_code == 200)

    resp = c.post('/cash-register/close', data={
        'closing_balance': '700'
    }, follow_redirects=True)
    test('Kasa kapama', resp.status_code == 200)

    resp = c.get('/cash-register/detail/1')
    test('Kasa detay', resp.status_code == 200)

    section('12. Stok Sayimi')
    resp = c.post('/stock-count/new', json={})
    test('Stok sayimi olusturma (JSON)', resp.status_code in (200, 400),
         f'HTTP {resp.status_code}')

    section('13. Alis Faturasi')
    resp = c.post('/purchase/invoices/new', data={
        'supplier_id': '1', 'invoice_no': 'FAT001',
        'product_id[]': '1', 'qty[]': '10', 'price[]': '8'
    }, follow_redirects=True)
    test('Fatura kaydi', resp.status_code == 200)

    resp = c.get('/purchase/invoices', follow_redirects=True)
    test('Fatura listesi', resp.status_code == 200)

    resp = c.get('/purchase/invoices/1', follow_redirects=True)
    test('Fatura detay', resp.status_code == 200)

    section('14. Fiyat Yonetimi')
    resp = c.get('/stock/prices/1', follow_redirects=True)
    test('Fiyat yonetim', resp.status_code == 200)

    section('15. 404 Hatasi')
    resp = c.get('/kesinlikle-olmayan-sayfa')
    test('404 sayfasi', resp.status_code == 404)
    test('404 icerik', b'404' in resp.data or b'bulunamad' in resp.data)

    section('16. Veritabani Dogrulama')
    test('Urun kaydi var', Product.query.count() >= 1)
    test('Musteri kaydi var', Customer.query.count() >= 1)
    test('Tedarikci kaydi var', Supplier.query.count() >= 1)
    test('Gider kaydi var', Expense.query.count() >= 1)
    test('Satis kaydi var', Sale.query.count() >= 2,
         f'Sadece {Sale.query.count()} satis')
    completed = Sale.query.filter_by(status='completed').count()
    test('Tamamlanmis satis', completed >= 2, f'{completed} tamamlanmis')

    section('17. Kaynak Kotta debt Taramasi')
    import re
    debt_refs = []
    for root, dirs, files in os.walk('app'):
        for f in files:
            if f.endswith(('.py', '.html')) and not f.endswith('.min.js') and not f.endswith('.min.css'):
                path = os.path.join(root, f)
                with open(path, encoding='utf-8', errors='ignore') as fh:
                    for i, line in enumerate(fh, 1):
                        if re.search(r'\bdebt\b|\bveresiye\b', line, re.IGNORECASE):
                            debt_refs.append(f'{os.path.relpath(path)}:{i}')
    if debt_refs:
        test('debt/veresiye temiz', False, f'{len(debt_refs)} referans: {debt_refs[:5]}')
    else:
        test('debt/veresiye temiz', True)

section('18. Tum Modul Importlari')
mods = [
    'app', 'app.models', 'app.auth_helper', 'app.printer_helper', 'app.update_helper',
    'app.routes.auth', 'app.routes.pos', 'app.routes.stock', 'app.routes.customer',
    'app.routes.report', 'app.routes.employee', 'app.routes.branch', 'app.routes.purchase',
    'app.routes.cash', 'app.routes.settings', 'app.routes.receipt', 'app.routes.transfer',
    'app.routes.supplier', 'app.routes.expense', 'app.routes.stock_count',
    'app.routes.cash_register', 'app.routes.main',
]
import importlib
for m in mods:
    try:
        importlib.reload(importlib.import_module(m))
        test(f'Import: {m}', True)
    except Exception as e:
        test(f'Import: {m}', False, str(e)[:150])

import platform
print(f'\n{"="*50}')
print(f'  SONUC: {PASS} gecti, {FAIL} basarisiz')
print(f'  Platform: {platform.platform()}')
print(f'  Python: {sys.version.split()[0]}')
print(f'{"="*50}')
if ERRORS:
    print('\nBASARISIZ TESTLER:')
    for e in ERRORS:
        print(f'  {e}')

sys.exit(0 if FAIL == 0 else 1)
