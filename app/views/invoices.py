import io
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import db
from app.email_helper import notify_invoice_created, notify_invoice_paid
from app.models import Client, Invoice, Project
from app.views.maintenance import update_overdue_invoices

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

CURRENCY_SUFFIX = {
    'HUF': 'Ft',
    'EUR': 'EUR',
    'USD': 'USD',
}

TAX_CATEGORY_OPTIONS = [
    ('VAT', 'Normál ÁFA'),
    ('EUE', 'EUE'),
    ('FAD', 'FAD'),
    ('AAM', 'AAM'),
]

SPECIAL_TAX_CATEGORIES = {'EUE', 'FAD', 'AAM'}


def _format_money(amount, currency='HUF'):
    value = float(amount or 0)
    code = (currency or 'HUF').upper()
    if code == 'HUF':
        return f"{value:,.0f} Ft".replace(',', ' ')
    return f"{value:,.2f} {CURRENCY_SUFFIX.get(code, code)}".replace(',', ' ').replace('.', ',')


def _normalize_tax_category(raw_value):
    value = (raw_value or 'VAT').upper()
    allowed = {item[0] for item in TAX_CATEGORY_OPTIONS}
    return value if value in allowed else 'VAT'


def _tax_category_label(category):
    normalized = _normalize_tax_category(category)
    for value, label in TAX_CATEGORY_OPTIONS:
        if value == normalized:
            return label
    return 'Normál ÁFA'


def next_invoice_number():
    last = Invoice.query.order_by(Invoice.id.desc()).first()
    year = datetime.now().year
    if last:
        return f"SLV-{year}-{last.id + 1:04d}"
    return f"SLV-{year}-0001"


@invoices_bp.route('/')
@login_required
def list():
    update_overdue_invoices()
    direction = request.args.get('direction', 'all')
    status = request.args.get('status', 'all')
    query = Invoice.query
    if direction != 'all':
        query = query.filter_by(direction=direction)
    if status != 'all':
        query = query.filter_by(status=status)
    invoices = query.order_by(Invoice.created_at.desc()).all()
    return render_template('invoices/list.html', invoices=invoices, direction=direction, status=status)


@invoices_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    clients = Client.query.filter_by(is_active=True).order_by(Client.name).all()
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        tax_category = _normalize_tax_category(request.form.get('tax_category'))
        vat_rate = float(request.form.get('vat_rate', 27))
        if tax_category in SPECIAL_TAX_CATEGORIES:
            vat_rate = 0
        amount_with_vat = amount * (1 + vat_rate / 100)

        invoice = Invoice(
            invoice_number=request.form.get('invoice_number') or next_invoice_number(),
            project_id=int(request.form.get('project_id')),
            client_id=int(request.form.get('client_id')),
            direction=request.form.get('direction'),
            amount=amount,
            vat_rate=vat_rate,
            tax_category=tax_category,
            amount_with_vat=amount_with_vat,
            description=request.form.get('description'),
            issue_date=datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d').date() if request.form.get('issue_date') else date.today(),
            due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else None,
            status=request.form.get('status', 'pending'),
            notes=request.form.get('notes'),
            currency=(request.form.get('currency') or 'HUF').upper(),
            created_by=current_user.id,
        )
        db.session.add(invoice)
        db.session.flush()

        pdf_file = request.files.get('pdf_file')
        if pdf_file and pdf_file.filename and pdf_file.filename.lower().endswith('.pdf'):
            invoice.pdf_data = pdf_file.read()
            invoice.pdf_filename = pdf_file.filename

        db.session.commit()

        if invoice.direction == 'outgoing' and not invoice.notification_sent:
            invoice.notification_sent = notify_invoice_created(invoice)
            db.session.commit()

        flash(f'Számla {invoice.invoice_number} létrehozva!', 'success')
        return redirect(url_for('invoices.detail', id=invoice.id))

    return render_template(
        'invoices/form.html',
        projects=projects,
        clients=clients,
        next_number=next_invoice_number(),
        invoice=None,
        tax_category_options=TAX_CATEGORY_OPTIONS,
    )


@invoices_bp.route('/<int:id>')
@login_required
def detail(id):
    update_overdue_invoices()
    invoice = Invoice.query.get_or_404(id)
    return render_template(
        'invoices/detail.html',
        invoice=invoice,
        tax_category_label=_tax_category_label(invoice.tax_category),
    )


def _register_pdf_font():
    font_paths = [
        r'C:\Windows\Fonts\arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
    ]
    for path in font_paths:
        try:
            pdfmetrics.registerFont(TTFont('SolviorSans', path))
            return 'SolviorSans'
        except Exception:
            continue
    return 'Helvetica'


@invoices_bp.route('/<int:id>/pdf')
@login_required
def pdf(id):
    invoice = Invoice.query.get_or_404(id)
    buffer = io.BytesIO()
    font_name = _register_pdf_font()
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=invoice.invoice_number,
    )

    net = float(invoice.amount or 0)
    gross = float(invoice.amount_with_vat or invoice.amount or 0)
    vat = gross - net
    tax_category = _normalize_tax_category(invoice.tax_category)
    tax_label = _tax_category_label(invoice.tax_category)
    tax_amount_label = tax_label if tax_category in SPECIAL_TAX_CATEGORIES else f'ÁFA ({float(invoice.vat_rate or 0):.0f}%)'
    status_labels = {
        'paid': 'Fizetve',
        'pending': 'Függőben',
        'overdue': 'Lejárt',
        'cancelled': 'Törölve',
    }

    story = [
        Paragraph('<b>SOLVIOR PROJECT</b>', styles['Title']),
        Paragraph('Planéta Centrum Kft.', styles['Heading2']),
        Paragraph('Belső ERP számlaösszesítő', styles['Normal']),
        Spacer(1, 10 * mm),
    ]

    header = Table([
        ['Számlaszám', invoice.invoice_number],
        ['Irány', 'Kimenő számla' if invoice.direction == 'outgoing' else 'Bejövő számla'],
        ['Projekt', invoice.project.name if invoice.project else '-'],
        ['Ügyfél', invoice.client.name if invoice.client else '-'],
        ['Kiállítás dátuma', invoice.issue_date or '-'],
        ['Fizetési határidő', invoice.due_date or '-'],
        ['Státusz', status_labels.get(invoice.status, invoice.status)],
        ['Pénznem', invoice.currency or 'HUF'],
        ['Adónem', tax_label],
    ], colWidths=[45 * mm, 110 * mm])
    header.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3a5c')),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d6dce5')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 7),
    ]))
    story.extend([header, Spacer(1, 10 * mm)])

    story.append(Paragraph('<b>Tárgy / leírás</b>', styles['Heading3']))
    story.append(Paragraph(invoice.description or '-', styles['Normal']))
    story.append(Spacer(1, 7 * mm))

    amounts = Table([
        ['Nettó összeg', _format_money(net, invoice.currency)],
        [tax_amount_label, _format_money(vat, invoice.currency)],
        ['Bruttó összeg', _format_money(gross, invoice.currency)],
    ], colWidths=[85 * mm, 70 * mm])
    amounts.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#e8f1fb')),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor('#1a3a5c')),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d6dce5')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(amounts)

    if invoice.notes:
        story.extend([
            Spacer(1, 8 * mm),
            Paragraph('<b>Megjegyzés</b>', styles['Heading3']),
            Paragraph(invoice.notes, styles['Normal']),
        ])

    doc.build(story)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'{invoice.invoice_number}.pdf',
        mimetype='application/pdf',
    )


@invoices_bp.route('/<int:id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(id):
    invoice = Invoice.query.get_or_404(id)
    invoice.status = 'paid'
    invoice.paid_date = date.today()
    db.session.commit()
    notify_invoice_paid(invoice)
    flash(f'{invoice.invoice_number} kifizetettnek jelölve!', 'success')
    return redirect(request.referrer or url_for('invoices.list'))


@invoices_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    invoice = Invoice.query.get_or_404(id)
    projects = Project.query.order_by(Project.name).all()
    clients = Client.query.filter_by(is_active=True).order_by(Client.name).all()
    if request.method == 'POST':
        invoice.project_id = int(request.form.get('project_id'))
        invoice.client_id = int(request.form.get('client_id'))
        invoice.direction = request.form.get('direction')
        invoice.amount = float(request.form.get('amount', 0))
        invoice.tax_category = _normalize_tax_category(request.form.get('tax_category'))
        invoice.vat_rate = float(request.form.get('vat_rate', 27))
        if invoice.tax_category in SPECIAL_TAX_CATEGORIES:
            invoice.vat_rate = 0
        invoice.amount_with_vat = invoice.amount * (1 + invoice.vat_rate / 100)
        invoice.description = request.form.get('description')
        invoice.status = request.form.get('status')
        invoice.notes = request.form.get('notes')
        invoice.currency = (request.form.get('currency') or 'HUF').upper()
        invoice.issue_date = datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d').date() if request.form.get('issue_date') else None
        invoice.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else None

        pdf_file = request.files.get('pdf_file')
        if pdf_file and pdf_file.filename and pdf_file.filename.lower().endswith('.pdf'):
            invoice.pdf_data = pdf_file.read()
            invoice.pdf_filename = pdf_file.filename

        db.session.commit()
        flash('Számla frissítve!', 'success')
        return redirect(url_for('invoices.detail', id=invoice.id))

    return render_template(
        'invoices/form.html',
        projects=projects,
        clients=clients,
        invoice=invoice,
        next_number=invoice.invoice_number,
        tax_category_options=TAX_CATEGORY_OPTIONS,
    )


@invoices_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    invoice = Invoice.query.get_or_404(id)
    db.session.delete(invoice)
    db.session.commit()
    flash('Számla törölve!', 'success')
    return redirect(url_for('invoices.list'))


@invoices_bp.route('/<int:id>/pdf-upload')
@login_required
def download_uploaded_pdf(id):
    invoice = Invoice.query.get_or_404(id)
    if not invoice.pdf_data:
        flash('Nincs feltöltött PDF ehhez a számlához.', 'danger')
        return redirect(url_for('invoices.detail', id=id))
    return send_file(
        io.BytesIO(invoice.pdf_data),
        as_attachment=True,
        download_name=invoice.pdf_filename or f'{invoice.invoice_number}_szamla.pdf',
        mimetype='application/pdf',
    )


@invoices_bp.route('/<int:id>/pdf-upload/delete', methods=['POST'])
@login_required
def delete_uploaded_pdf(id):
    invoice = Invoice.query.get_or_404(id)
    invoice.pdf_data = None
    invoice.pdf_filename = None
    db.session.commit()
    flash('Feltöltött PDF törölve.', 'success')
    return redirect(url_for('invoices.detail', id=id))
