import socket, time, threading

def _prepare_sale_packet(amount_tl):
    amount_kurus = str(int(round(amount_tl * 100))).zfill(12)
    now = time.localtime()
    time_str = f'{now.tm_hour:02d}{now.tm_min:02d}{now.tm_sec:02d}'
    date_str = f'{now.tm_mday:02d}{now.tm_mon:02d}{now.tm_year % 100:02d}'
    data = (time_str + date_str + amount_kurus + '949' + '00').encode('ascii')
    packet = bytearray()
    packet.append(0x02)
    cmd = 0x30
    chk = cmd
    for b in data:
        chk ^= b
    packet.append(len(data) + 1)
    packet.append(cmd)
    packet.extend(data)
    packet.append(chk)
    packet.append(0x03)
    return bytes(packet)

def _parse_response(data):
    try:
        if len(data) < 6 or data[0] != 0x02 or data[-1] != 0x03:
            return {'success': False, 'error': 'Geçersiz yanıt formatı'}
        resp_code = data[3:5].decode('ascii', errors='replace')
        if resp_code == '00':
            approval = data[5:11].decode('ascii', errors='replace') if len(data) >= 11 else ''
            card_no = data[11:30].decode('ascii', errors='replace') if len(data) >= 30 else ''
            return {
                'success': True,
                'approval_code': approval,
                'card_number': card_no.strip(),
                'message': f'Onay kodu: {approval}'
            }
        error_msgs = {
            '01': 'Kart reddedildi',
            '02': 'Geçersiz kart',
            '03': 'Geçersiz işlem',
            '04': 'Yetersiz bakiye',
            '05': 'Genel hata',
            '51': 'Yetersiz bakiye',
            '54': 'Kart süresi dolmuş',
            '55': 'Hatalı şifre',
            '57': 'İşleme izin verilmiyor',
            '62': 'Kısıtlı kart',
            '65': 'İşlem limiti aşıldı',
        }
        msg = error_msgs.get(resp_code, f'Hata kodu: {resp_code}')
        return {'success': False, 'error': msg}
    except Exception as e:
        return {'success': False, 'error': f'Yanıt çözümleme hatası: {str(e)}'}

def send_sale(amount_tl, conn_type='serial', address='COM1', timeout=30):
    if conn_type == 'none' or not address:
        return {'success': False, 'error': 'POS yapılandırılmamış'}
    packet = _prepare_sale_packet(amount_tl)
    try:
        if conn_type == 'serial':
            import serial
            with serial.Serial(address, 9600, timeout=timeout) as ser:
                ser.write(packet)
                time.sleep(0.5)
                resp = ser.read(1024)
        elif conn_type == 'tcp':
            if ':' in address:
                addr, port = address.rsplit(':', 1)
                port = int(port)
            else:
                addr, port = address, 9100
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((addr, port))
                s.sendall(packet)
                resp = s.recv(1024)
        else:
            return {'success': False, 'error': f'Bilinmeyen POS türü: {conn_type}'}
        if not resp or len(resp) == 0:
            return {'success': False, 'error': 'POS yanıt vermedi (zaman aşımı)'}
        return _parse_response(resp)
    except ImportError:
        return {'success': False, 'error': 'pyserial kütüphanesi eksik (pip install pyserial)'}
    except Exception as e:
        return {'success': False, 'error': f'POS iletişim hatası: {str(e)}'}

def test_connection(conn_type='serial', address='COM1', timeout=10):
    if conn_type == 'none' or not address:
        return {'success': False, 'error': 'POS yapılandırılmamış'}
    try:
        if conn_type == 'serial':
            import serial
            try:
                with serial.Serial(address, 9600, timeout=timeout) as ser:
                    ser.write(b'\x05')
                    time.sleep(0.3)
                    resp = ser.read(1024)
                    if resp:
                        return {'success': True, 'message': f'{address} üzerinde POS cihazı algılandı ({len(resp)} bayt yanıt)'}
                    return {'success': True, 'message': f'{address} açık, yanıt bekleniyor (POS cihazı algılanamadı)'}
            except serial.SerialException as e:
                return {'success': False, 'error': f'{address} açılamadı: {str(e)}'}
        elif conn_type == 'tcp':
            if ':' in address:
                addr, port = address.rsplit(':', 1)
                port = int(port)
            else:
                addr, port = address, 9100
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((addr, port))
                return {'success': True, 'message': f'{addr}:{port} bağlantı başarılı'}
        else:
            return {'success': False, 'error': f'Bilinmeyen tür: {conn_type}'}
    except socket.timeout:
        return {'success': False, 'error': f'{address} bağlantı zaman aşımı'}
    except ConnectionRefusedError:
        return {'success': False, 'error': f'{address} bağlantı reddedildi'}
    except Exception as e:
        return {'success': False, 'error': f'Test hatası: {str(e)}'}

def list_ports():
    try:
        import serial.tools.list_ports
        return [p.device for p in serial.tools.list_ports.comports()]
    except ImportError:
        return []
