import socket, time

def _esc(*args):
    return bytes(args)

def _init():
    return b'\x1b\x40'

def _align(n):
    return b'\x1b\x61' + bytes([n])

def _bold(n):
    return b'\x1b\x45' + bytes([n])

def _double(n):
    return b'\x1b\x21' + bytes([0x10 if n else 0x00])

def _text(s, encoding='cp857'):
    return s.encode(encoding, errors='replace')

def _feed(n=1):
    return b'\x1b\x64' + bytes([n])

def _cut(m=1):
    return b'\x1d\x56' + bytes([m])

def _bar(n):
    return b'\x1d\x48' + bytes([n])

def build_receipt(sale, items, company_name):
    buf = bytearray()
    buf += _init()
    buf += _align(1)
    buf += _double(1)
    buf += _text(company_name or '')
    buf += _double(0)
    buf += _feed()
    buf += _align(1)
    buf += _text('FIS')
    buf += _feed()
    buf += _align(0)
    buf += _text('-' * 42)
    buf += _feed()
    buf += _text(f'Fis No: {sale.receipt_no}')
    buf += _feed()
    buf += _text(f'Tarih: {sale.created_at.strftime("%d.%m.%Y %H:%M")}')
    buf += _feed()
    if sale.customer:
        buf += _text(f'Musteri: {sale.customer.name}')
        buf += _feed()
    buf += _text('-' * 42)
    buf += _feed()
    buf += _bold(1)
    buf += _text(f'{"Urun":20s} {"Adet":>6s} {"Tutar":>10s}')
    buf += _feed()
    buf += _bold(0)
    buf += _text('-' * 42)
    buf += _feed()
    for item in items:
        name = (item.product_name or '')[:18]
        qty = f'{item.quantity:.2f}'
        total = f'{item.total_price:.2f}'
        buf += _text(f'{name:20s} {qty:>6s} {total:>10s}')
        buf += _feed()
    buf += _text('-' * 42)
    buf += _feed()
    buf += _text(f'{"Ara Toplam:":>30s} {sale.total_amount:.2f}')
    buf += _feed()
    if sale.tax_amount and float(sale.tax_amount) > 0:
        buf += _text(f'{"KDV:":>30s} {sale.tax_amount:.2f}')
        buf += _feed()
    if sale.discount and float(sale.discount) > 0:
        buf += _text(f'{"Indirim:":>30s} -{sale.discount:.2f}')
        buf += _feed()
    buf += _bold(1)
    buf += _text(f'{"GENEL TOPLAM:":>30s} {sale.grand_total:.2f}')
    buf += _feed()
    buf += _bold(0)
    buf += _text(f'Odeme: {sale.payment_method}')
    buf += _feed()
    buf += _feed()
    buf += _align(1)
    buf += _text('Iyi gunler dileriz!')
    buf += _feed(3)
    buf += _cut(1)
    return bytes(buf)

def print_receipt(sale_id):
    from app.models import Sale, SaleItem, Setting
    from app import db
    sale = Sale.query.get(sale_id)
    if not sale:
        return {'error': 'Satis bulunamadi'}
    items = SaleItem.query.filter_by(sale_id=sale_id).all()
    ptype = ''
    paddr = ''
    cname = ''
    try:
        def gs(k, d=''):
            s = Setting.query.filter_by(key=k).first()
            return s.value if s else d
        ptype = gs('printer_type', 'none')
        paddr = gs('printer_address', '')
        cname = gs('company_name', '')
    except:
        pass
    if ptype == 'none' or not paddr:
        return {'error': 'Yazici ayarlanmamis. Ayarlar sayfasindan yapilandirin.'}
    data = build_receipt(sale, items, cname)
    try:
        if ptype == 'serial':
            import serial
            with serial.Serial(paddr, 9600, timeout=5) as ser:
                ser.write(data)
        elif ptype == 'tcp':
            if ':' in paddr:
                addr, port = paddr.rsplit(':', 1)
                port = int(port)
            else:
                addr, port = paddr, 9100
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((addr, port))
                s.sendall(data)
        else:
            return {'error': f'Bilinmeyen yazici tipi: {ptype}'}
        return {'success': True}
    except ImportError:
        return {'error': 'pyserial kutuphanesi eksik. pip install pyserial'}
    except Exception as e:
        return {'error': f'Yazdirma hatasi: {str(e)}'}
