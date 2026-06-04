from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.auth_helper import login_required, get_user_id, get_branch_id, is_admin, get_user_name
from app.models import Sale, SaleItem, Setting
from app import db

receipt_bp = Blueprint('receipt', __name__, url_prefix='/receipt')

@receipt_bp.route('/<int:sale_id>')
@login_required
def view_receipt(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    host = request.host_url.rstrip('/')
    return render_template('receipt.html', sale=sale, items=items, host=host)

@receipt_bp.route('/send-email/<int:sale_id>', methods=['POST'])
@login_required
def send_email(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    to_email = request.form.get('email', '').strip()
    if not to_email:
        flash('E-posta adresi gerekli', 'error')
        return redirect(url_for('receipt.view_receipt', sale_id=sale_id))
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        def get_setting(key, default=''):
            s = Setting.query.filter_by(key=key).first()
            return s.value if s else default

        smtp_host = get_setting('smtp_host')
        smtp_port = get_setting('smtp_port', '587')
        smtp_user = get_setting('smtp_user')
        smtp_pass = get_setting('smtp_pass')
        from_email = get_setting('from_email') or smtp_user

        if not smtp_host or not smtp_user:
            flash('SMTP ayarları yapılmamış. Ayarlar > E-posta bölümünden yapılandırın.', 'error')
            return redirect(url_for('receipt.view_receipt', sale_id=sale_id))

        items_html = ''
        for item in SaleItem.query.filter_by(sale_id=sale.id).all():
            items_html += f'<tr><td>{item.product_name}</td><td>{item.quantity}</td><td>{item.total_price} ₺</td></tr>'

        body = f'''
        <h3>BarkodPOS Fişi</h3>
        <p><b>Fiş No:</b> {sale.receipt_no}</p>
        <p><b>Tarih:</b> {sale.created_at.strftime("%d.%m.%Y %H:%M")}</p>
        <table border="1" cellpadding="5" style="border-collapse:collapse">
        <tr><th>Ürün</th><th>Adet</th><th>Tutar</th></tr>
        {items_html}
        </table>
        <hr>
        <p><b>Ara Toplam:</b> {sale.total_amount} ₺</p>
        {f"<p><b>KDV:</b> {sale.tax_amount} ₺</p>" if sale.tax_amount else ""}
        {f"<p><b>İndirim:</b> -{sale.discount} ₺</p>" if sale.discount > 0 else ""}
        <p><b>Genel Toplam:</b> {sale.grand_total} ₺</p>
        <p><b>Ödeme:</b> {sale.payment_method}</p>
        <hr><p>İyi günler dileriz!</p>
        '''

        msg = MIMEMultipart()
        msg['Subject'] = f'BarkodPOS Fişi - {sale.receipt_no}'
        msg['From'] = from_email
        msg['To'] = to_email
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(smtp_host, int(smtp_port), timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        flash('Fiş e-posta ile gönderildi', 'success')
    except Exception as e:
        flash(f'E-posta gönderilemedi: {str(e)}', 'error')
    return redirect(url_for('receipt.view_receipt', sale_id=sale_id))
