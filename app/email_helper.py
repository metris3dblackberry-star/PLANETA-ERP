import smtplib
from email.message import EmailMessage

import requests
from flask import current_app


def _smtp_configured():
    return bool(current_app.config.get('MAIL_SERVER'))


def _send_smtp(to, subject, html_body):
    msg = EmailMessage()
    sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
    msg['From'] = f"SOLVIOR PROJECT <{sender}>" if sender else 'SOLVIOR PROJECT'
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content('Az üzenet HTML formátumban érhető el.')
    msg.add_alternative(html_body, subtype='html')

    server = current_app.config['MAIL_SERVER']
    port = current_app.config.get('MAIL_PORT', 587)
    use_ssl = current_app.config.get('MAIL_USE_SSL', False)
    use_tls = current_app.config.get('MAIL_USE_TLS', True)
    username = current_app.config.get('MAIL_USERNAME')
    password = current_app.config.get('MAIL_PASSWORD')

    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_class(server, port, timeout=15) as smtp:
        if use_tls and not use_ssl:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg)


def _send_mailgun(to, subject, html_body):
    api_key = current_app.config.get('MAILGUN_API_KEY')
    domain = current_app.config.get('MAILGUN_DOMAIN')
    from_addr = current_app.config.get('MAILGUN_FROM')

    if not api_key or not domain:
        return False

    resp = requests.post(
        f"https://api.mailgun.net/v3/{domain}/messages",
        auth=("api", api_key),
        data={
            "from": f"SOLVIOR PROJECT <{from_addr}>",
            "to": [to],
            "subject": subject,
            "html": html_body,
        },
        timeout=15,
    )
    return resp.status_code == 200


def send_email(to, subject, html_body):
    """Send email via SMTP/SendGrid, with optional Mailgun fallback."""
    if not to:
        return False

    try:
        if _smtp_configured():
            _send_smtp(to, subject, html_body)
            return True
        if _send_mailgun(to, subject, html_body):
            return True
        print(f"[EMAIL SKIP] Missing email provider config. To: {to}, Subject: {subject}")
        return False
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def notify_invoice_created(invoice):
    """Email to client when invoice is created."""
    if not invoice.client or not invoice.client.email:
        return False
    html = f"""
    <h2>Új számla értesítő</h2>
    <p>Tisztelt {invoice.client.name}!</p>
    <p>Új számla került kiállításra az Ön részére:</p>
    <ul>
        <li><strong>Számlaszám:</strong> {invoice.invoice_number}</li>
        <li><strong>Projekt:</strong> {invoice.project.name if invoice.project else '-'}</li>
        <li><strong>Összeg:</strong> {float(invoice.amount):,.0f} Ft</li>
        <li><strong>Fizetési határidő:</strong> {invoice.due_date or '-'}</li>
    </ul>
    <p>Köszönettel,<br>SOLVIOR PROJECT</p>
    """
    return send_email(invoice.client.email, f"Új számla: {invoice.invoice_number}", html)


def notify_invoice_paid(invoice):
    """Email to client when invoice is marked paid."""
    if not invoice.client or not invoice.client.email:
        return False
    html = f"""
    <h2>Fizetés visszaigazolás</h2>
    <p>Tisztelt {invoice.client.name}!</p>
    <p>A következő számla <strong>kifizetettnek</strong> lett jelölve:</p>
    <ul>
        <li><strong>Számlaszám:</strong> {invoice.invoice_number}</li>
        <li><strong>Összeg:</strong> {float(invoice.amount):,.0f} Ft</li>
        <li><strong>Fizetés dátuma:</strong> {invoice.paid_date or '-'}</li>
    </ul>
    <p>Köszönettel,<br>SOLVIOR PROJECT</p>
    """
    return send_email(invoice.client.email, f"Fizetés visszaigazolva: {invoice.invoice_number}", html)


def notify_subcontractor_payment(payment):
    """Email to subcontractor about payment."""
    if not payment.subcontractor or not payment.subcontractor.email:
        return False
    html = f"""
    <h2>Alvállalkozói kifizetés értesítő</h2>
    <p>Tisztelt {payment.subcontractor.name}!</p>
    <p>Kifizetés lett rögzítve az Ön részére:</p>
    <ul>
        <li><strong>Projekt:</strong> {payment.project.name if payment.project else '-'}</li>
        <li><strong>Összeg:</strong> {float(payment.amount):,.0f} Ft</li>
        <li><strong>Státusz:</strong> {payment.status}</li>
    </ul>
    <p>Köszönettel,<br>SOLVIOR PROJECT</p>
    """
    return send_email(payment.subcontractor.email, f"Alvállalkozói kifizetés: {payment.project.name}", html)
