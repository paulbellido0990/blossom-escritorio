from pathlib import Path
import pytest
from db import Database
from receipt import generate_receipt


def test_receipt_pdf_with_refund_and_long_content(tmp_path):
    db = Database(tmp_path / 'data.db')
    try:
        sid = db.add_sale('María & Ana <cliente>', 'Ramo rosado ' * 25,
            'Encargo', 2, '50', '17', shipping='10', discount='5', advance='30',
            notes='Nota privada', phone='70000000')
        db.refund(sid, '5', 'QR')
        for _ in range(45):
            db.add_payment(sid, '1', 'Efectivo')
        output = generate_receipt(db, sid, tmp_path / 'receipt.pdf',
                                  Path(__file__).resolve().parents[1] / 'assets/logo.png')
        data = output.read_bytes()
        assert data.startswith(b'%PDF-')
        assert b'%%EOF' in data[-50:]
        assert db.sale(sid)['paid_cents'] == 7000
        assert db.sale(sid)['total_cents'] == 10500
    finally:
        db.close()


def test_receipt_rejects_missing_sale_and_database_target(tmp_path):
    db = Database(tmp_path / 'data.db')
    try:
        sid = db.add_sale('Ana','Flor','Disponible',1,'20','5')
        with pytest.raises(ValueError):
            generate_receipt(db, sid, db.path)
        with pytest.raises(ValueError):
            generate_receipt(db, 999, tmp_path / 'missing.pdf')
        assert not (tmp_path / 'missing.pdf').exists()
        assert db.sale(sid)['total_cents'] == 2000
        generate_receipt(db, sid, tmp_path / 'no_logo.pdf')
    finally:
        db.close()
