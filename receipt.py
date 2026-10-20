"""Comprobantes PDF para clientes; no incluyen costos internos del negocio."""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from db import bs

ROSE = colors.HexColor('#AC4F79')
DARK = colors.HexColor('#6D3C55')
SOFT = colors.HexColor('#FBE7EF')
MINT = colors.HexColor('#E2F5ED')
MUTED = colors.HexColor('#927F8B')


def generate_receipt(database, sale_id, target, logo_path=None):
    sale = database.sale(sale_id)
    payments = database.sale_payments(sale_id)
    target = Path(target)
    if target.resolve() == database.path.resolve():
        raise ValueError('El PDF debe guardarse en un archivo distinto de la base de datos.')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('BodyReceipt', fontName='Helvetica', fontSize=10,
        leading=15, textColor=DARK, spaceAfter=5, splitLongWords=True))
    styles.add(ParagraphStyle('TitleReceipt', fontName='Helvetica-Bold', fontSize=25,
        leading=30, textColor=ROSE))
    styles.add(ParagraphStyle('SmallReceipt', parent=styles['BodyReceipt'], fontSize=8,
        leading=12, textColor=MUTED))
    styles.add(ParagraphStyle('RightReceipt', parent=styles['BodyReceipt'], alignment=TA_RIGHT))
    def text(value, style='BodyReceipt'):
        return Paragraph(escape(str(value or '')).replace('\n', '<br/>'), styles[style])
    width = A4[0] - 40*mm
    doc = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=20*mm,
        rightMargin=20*mm, topMargin=18*mm, bottomMargin=22*mm,
        title=f'BLOSSOM - Comprobante V-{sale_id:04d}', author='BLOSSOM')
    story = []
    brand = [text('BLOSSOM', 'TitleReceipt'), text('Detalles que florecen', 'SmallReceipt')]
    if logo_path and Path(logo_path).is_file():
        logo = Image(str(logo_path))
        logo._restrictSize(45*mm, 24*mm)
        brand = [logo]
    heading = Table([[brand, [text('COMPROBANTE DE PEDIDO', 'RightReceipt'),
        text(f'V-{sale_id:04d}', 'RightReceipt'), text(sale['sale_date'], 'RightReceipt')]]],
        colWidths=[width*.5, width*.5])
    heading.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LINEBELOW',(0,0),(-1,-1),1.5,ROSE),('BOTTOMPADDING',(0,0),(-1,-1),16)]))
    story += [heading, Spacer(1, 7*mm)]
    customer = Table([[text('CLIENTE', 'SmallReceipt'), text('PEDIDO', 'SmallReceipt')],
        [text(sale['client']), text(f'{sale["mode"]} · {sale["status"]}')],
        [text(sale['phone'] or 'Sin teléfono registrado', 'SmallReceipt'),
         text('Entrega: '+(sale['delivery_date'] or 'Pendiente de entrega'), 'SmallReceipt')]],
        colWidths=[width*.56, width*.44])
    customer.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),SOFT),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),12),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story += [customer, Spacer(1, 8*mm)]
    items = Table([[text('PRODUCTO'),text('CANT.'),text('PRECIO'),text('IMPORTE')],
        [text(sale['product']),text(sale['qty']),text(bs(sale['price_cents'])),
         text(bs(sale['qty']*sale['price_cents']))]],
        colWidths=[width*.46,width*.12,width*.21,width*.21], repeatRows=1)
    items.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),MINT),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),10),
        ('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,-1),(-1,-1),.5,SOFT)]))
    story += [items, Spacer(1, 5*mm)]
    totals = Table([[text(label), text(bs(value), 'RightReceipt')] for label,value in [
        ('Envío',sale['shipping_cents']),('Descuento',-sale['discount_cents']),
        ('TOTAL DEL PEDIDO',sale['total_cents']),('Cobrado neto',sale['paid_cents']),
        ('Saldo pendiente',0 if sale['status']=='Cancelado' else sale['total_cents']-sale['paid_cents'])]],
        colWidths=[width*.65,width*.35])
    totals.setStyle(TableStyle([('BACKGROUND',(0,2),(-1,2),SOFT),
        ('BACKGROUND',(0,4),(-1,4),MINT),('TOPPADDING',(0,0),(-1,-1),7),
        ('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story += [KeepTogether([totals]), Spacer(1, 7*mm)]
    story.append(text('MOVIMIENTOS DE PAGO'))
    if payments:
        rows = [[text('FECHA'), text('MEDIO'), text('IMPORTE')]]
        rows += [[text(p['payment_date']),text(p['method']+(' · Devolución' if p['amount_cents']<0 else '')),
                  text(bs(p['amount_cents']),'RightReceipt')] for p in payments]
        table = Table(rows, colWidths=[width*.28,width*.42,width*.30],repeatRows=1)
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),MINT),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),
            ('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,-1),.3,SOFT)]))
        story.append(table)
    else:
        story.append(text('Sin pagos registrados.', 'SmallReceipt'))
    # Las notas de la venta son internas y no se imprimen para el cliente.
    story += [Spacer(1, 8*mm), text('Gracias por elegir BLOSSOM.', 'RightReceipt')]
    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(ROSE)
        canvas.line(20*mm,18*mm,A4[0]-20*mm,18*mm)
        canvas.setFillColor(MUTED)
        canvas.setFont('Helvetica',8)
        canvas.drawString(20*mm,13*mm,'Comprobante de pedido y pagos · No es una factura fiscal')
        canvas.drawRightString(A4[0]-20*mm,13*mm,f'Página {document.page}')
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return target
