import requests
from flask import current_app


def send_email(to, subject, html_body):
    """Send email via Mailgun"""
    api_key = current_app.config.get('MAILGUN_API_KEY')
    domain = current_app.config.get('MAILGUN_DOMAIN')
    from_addr = current_app.config.get('MAILGUN_FROM')

    if not api_key or not domain:
        print(f"[EMAIL SKIP] To: {to}, Subject: {subject}")
        return False

    try:
        resp = requests.post(
            f"https://api.mailgun.net/v3/{domain}/messages",
            auth=("api", api_key),
            data={
                "from": f"SOLVIOR CRM <{from_addr}>",
                "to": [to],
                "subject": subject,
                "html": html_body
            }
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def notify_invoice_created(invoice):
    """Email to client when invoice is created"""
    if not invoice.client.email:
        return
    html = f"""
    <h2>Új számla értesítő</h2>
    <p>Tisztelt {invoice.client.name}!</p>
    <p>Új számla került kiállításra az Ön részére:</p>
    <ul>
        <li><strong>Számlaszám:</strong> {invoice.invoice_number}</li>
        <li><strong>Projekt:</strong> {invoice.project.name}</li>
        <li><strong>Összeg:</strong> {float(invoice.amount):,.0f} Ft</li>
        <li><strong>Fizetési határidő:</strong> {invoice.due_date}</li>
    </ul>
    <p>Köszönettel,<br>SOLVIOR CRM</p>
    """
    send_email(invoice.client.email, f"Új számla: {invoice.invoice_number}", html)


def notify_invoice_paid(invoice):
    """Email to client when invoice is marked paid"""
    if not invoice.client.email:
        return
    html = f"""
    <h2>Fizetés visszaigazolás</h2>
    <p>Tisztelt {invoice.client.name}!</p>
    <p>A következő számla <strong>kifizetettnek</strong> lett jelölve:</p>
    <ul>
        <li><strong>Számlaszám:</strong> {invoice.invoice_number}</li>
        <li><strong>Összeg:</strong> {float(invoice.amount):,.0f} Ft</li>
        <li><strong>Fizetés dátuma:</strong> {invoice.paid_date}</li>
    </ul>
    <p>Köszönettel,<br>SOLVIOR CRM</p>
    """
    send_email(invoice.client.email, f"Fizetés visszaigazolva: {invoice.invoice_number}", html)


def notify_subcontractor_payment(payment):
    """Email to subcontractor about payment"""
    if not payment.subcontractor.email:
        return
    html = f"""
    <h2>Alvállalkozói kifizetés értesítő</h2>
    <p>Tisztelt {payment.subcontractor.name}!</p>
    <p>Kifizetés lett rögzítve az Ön részére:</p>
    <ul>
        <li><strong>Projekt:</strong> {payment.project.name}</li>
        <li><strong>Összeg:</strong> {float(payment.amount):,.0f} Ft</li>
        <li><strong>Státusz:</strong> {payment.status}</li>
    </ul>
    <p>Köszönettel,<br>SOLVIOR CRM</p>
    """
    send_email(payment.subcontractor.email, f"Alvállalkozói kifizetés: {payment.project.name}", html)
