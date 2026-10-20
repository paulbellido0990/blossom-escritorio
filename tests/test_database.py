import csv
from datetime import date
from db import Database, to_cents, bs
import pytest

@pytest.fixture
def db(tmp_path):
    obj=Database(tmp_path / 'blossom.db')
    yield obj
    obj.close()


def test_money_precision():
    assert to_cents('25,50') == 2550
    assert to_cents('1.234,50') == 123450
    assert to_cents('1,234.50') == 123450
    assert to_cents('0,005') == 1
    assert bs(123450) == 'Bs 1.234,50'
    with pytest.raises(ValueError):to_cents('cinco')
    with pytest.raises(ValueError):to_cents('NaN')


def test_sale_with_advance_payments_and_revenue(db):
    today=date.today().isoformat()
    month=today[:7]
    sid=db.add_sale('Carla', 'Ramo rosado', 'Encargo', 2, '50', '20',
                    shipping='5', discount='5', advance='30', method='QR')
    s=db.sale(sid)
    assert s['total_cents']==10000
    assert s['production_cents']==4000
    assert s['paid_cents']==3000
    assert db.totals(month)['sales']==0 # pedido no entregado
    assert db.totals(month)['collected']==3000
    assert db.totals()['pending']==7000
    with pytest.raises(ValueError):db.add_payment(sid,'71','Efectivo')
    db.add_payment(sid,'70','Efectivo')
    assert db.totals()['pending']==0
    db.set_status(sid,'Entregado')
    assert db.totals(month)['sales']==10000
    assert db.totals(month)['result']==6000
    assert db.cash_balance()==10000
    with pytest.raises(ValueError):db.set_status(sid,'Pendiente')


def test_refund_before_cancel(db):
    sid=db.add_sale('Ana','Flor', 'Disponible',1,'40','13', advance='10')
    with pytest.raises(ValueError):db.set_status(sid,'Cancelado')
    db.refund(sid,'10','Efectivo')
    db.set_status(sid,'Cancelado')
    assert db.totals()['collected']==0
    assert db.totals()['pending']==0
    with pytest.raises(ValueError):db.add_payment(sid,'3','QR')


def test_expenses_vs_production_double_count(db):
    sid=db.add_sale('Rosa','Caja floral','Disponible',1,'100','35',status='Entregado')
    db.add_expense('Compra de materiales','Limpiapipas','20','Efectivo')
    db.add_expense('Publicidad','Instagram','8','QR')
    db.add_expense('Equipamiento','Tijeras','15','Efectivo')
    db.add_expense('Retiro personal','Personal','4','Efectivo')
    t=db.totals()
    assert t['sales']==10000
    assert t['cost']==3500
    assert t['spent']==4700
    assert t['operating']==800
    assert t['result']==5700
    assert db.cash_balance()==-4700


def test_backup_and_exports(db,tmp_path):
    sid=db.add_sale('Sara','Flor','Encargo',1,'25','9',advance='10')
    db.add_expense('Servicios','Internet','7','Transferencia')
    out=tmp_path/'backup.db'
    db.backup(out)
    copied=Database(out)
    assert copied.sale(sid)['client']=='Sara'
    assert copied.expenses()[0]['amount_cents']==700
    copied.close()
    db.export_sales_csv(tmp_path/'ventas.csv')
    db.export_expenses_csv(tmp_path/'gastos.csv')
    with (tmp_path/'ventas.csv').open(encoding='utf-8-sig') as f:
        assert list(csv.reader(f,delimiter=';'))[1][2]=='Sara'


def test_validation(db):
    with pytest.raises(ValueError):db.add_sale('','Flor','Encargo',1,'10','5')
    with pytest.raises(ValueError):db.add_sale('Eva','Flor','Encargo',1,'10','5',discount='11')
    with pytest.raises(ValueError):db.add_sale('Eva','Flor','Encargo',1,'10','5',advance='11')
    with pytest.raises(ValueError):db.add_expense('Publicidad','', '10','QR')
    with pytest.raises(ValueError):db.add_expense('Publicidad','Ads','-1','QR')


def test_delete_sale_audits_and_updates_totals(db):
    import json
    sid = db.add_sale('Ana', 'Flor', 'Disponible', 1, '100', '30',
                      advance='60', status='Entregado')
    other = db.add_sale('Eva', 'Ramo', 'Encargo', 1, '20', '5', advance='10')
    db.refund(sid, '10', 'Efectivo')
    backup = db.delete_sale(sid, 'Registro duplicado')
    with pytest.raises(ValueError):
        db.sale(sid)
    assert db.sale_payments(sid) == []
    assert db.totals()['sales'] == 0
    assert db.totals()['pending'] == 1000
    assert db.cash_balance() == 1000
    assert db.sale(other)['paid_cents'] == 1000
    log = db.conn.execute('SELECT * FROM audit_log').fetchone()
    assert log['reason'] == 'Registro duplicado'
    assert len(json.loads(log['snapshot'])['payments']) == 2
    saved = Database(backup)
    assert saved.sale(sid)['paid_cents'] == 5000
    saved.close()


def test_delete_requires_reason_and_rolls_back(db):
    sid = db.add_sale('Ana', 'Flor', 'Encargo', 1, '40', '10', advance='20')
    with pytest.raises(ValueError):
        db.delete_sale(sid, ' ')
    db.conn.execute("""CREATE TRIGGER fail_delete BEFORE DELETE ON sales
                       BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        db.delete_sale(sid, 'Error de registro')
    assert db.sale(sid)['paid_cents'] == 2000
    assert db.conn.execute('SELECT COUNT(*) FROM audit_log').fetchone()[0] == 0


def test_delivery_date_does_not_change_when_repeated(db):
    sid = db.add_sale('Ana', 'Flor', 'Encargo', 1, '100', '30')
    db.set_status(sid, 'Entregado', '2026-01-31')
    db.set_status(sid, 'Entregado', '2026-02-01')
    assert db.sale(sid)['delivery_date'] == '2026-01-31'
    assert db.totals('2026-01')['sales'] == 10000
    assert db.totals('2026-02')['sales'] == 0


def test_restore_preserves_previous_data(db, tmp_path):
    sid = db.add_sale('Ana', 'Flor', 'Encargo', 1, '100', '30')
    source = db.backup(tmp_path / 'source.db')
    db.add_payment(sid, '50', 'QR')
    previous = db.restore(source)
    assert db.sale(sid)['paid_cents'] == 0
    saved = Database(previous)
    assert saved.sale(sid)['paid_cents'] == 5000
    saved.close()
    db.add_payment(sid, '10', 'Efectivo')
    assert db.sale(sid)['paid_cents'] == 1000


def test_restore_invalid_does_not_modify_data(db, tmp_path):
    import sqlite3
    sid = db.add_sale('Ana', 'Flor', 'Encargo', 1, '100', '30')
    invalid = tmp_path / 'invalid.db'
    invalid.write_text('invalid', encoding='utf-8')
    empty = tmp_path / 'empty.db'
    sqlite3.connect(empty).close()
    for source in (invalid, empty, tmp_path / 'missing.db', db.path):
        with pytest.raises(ValueError):
            db.restore(source)
        assert db.sale(sid)['client'] == 'Ana'
    assert not (tmp_path / 'missing.db').exists()


def test_restore_legacy_backup(db, tmp_path):
    import sqlite3
    source = db.backup(tmp_path / 'legacy.db')
    with sqlite3.connect(source) as conn:
        conn.execute('DROP TABLE audit_log')
        conn.execute('PRAGMA user_version=0')
    db.restore(source)
    assert db.conn.execute('PRAGMA user_version').fetchone()[0] == 1
    sid = db.add_sale('Ana', 'Flor', 'Encargo', 1, '10', '3')
    db.delete_sale(sid, 'Prueba')


def test_daily_backup_is_once_and_retains_30(db):
    target = db.automatic_backup()
    original = target.read_bytes()
    db.add_sale('Ana', 'Flor', 'Encargo', 1, '10', '3')
    assert db.automatic_backup().read_bytes() == original
    for day in range(1, 32):
        (db.backup_dir / f'diario_2000-01-{day:02d}.db').write_bytes(original)
    protected = db.safety_backup('antes_eliminar')
    db.automatic_backup()
    assert len(list(db.backup_dir.glob('diario_*.db'))) == 30
    assert protected.exists()


def test_deleted_sales_remains_queryable_after_reopening(db):
    sid = db.add_sale('Ana', 'Flor', 'Encargo', 1, '50', '10', advance='30')
    db.refund(sid, '5', 'Efectivo')
    db.delete_sale(sid, 'Duplicada')
    reopened = Database(db.path)
    try:
        item = reopened.deleted_sales()[0]
        assert item['sale_id'] == sid
        assert item['reason'] == 'Duplicada'
        assert item['sale']['total_cents'] == 5000
        assert item['sale']['paid_cents'] == 2500
        assert len(item['payments']) == 2
        assert reopened.totals()['registered'] == 0
        assert reopened.totals()['collected'] == 0
    finally:
        reopened.close()


def test_registered_delivered_and_collected_have_distinct_dates(db):
    sid = db.add_sale('Ana','Flor','Encargo',1,'100','30',advance='20',sale_date='2026-01-31')
    db.add_payment(sid,'80','QR',when='2026-02-01')
    db.set_status(sid,'Entregado',when='2026-03-01')
    db.add_expense('Compra de materiales','Material','15','Efectivo',when='2026-01-31')
    assert db.totals('2026-01')['registered'] == 10000
    assert db.totals('2026-01')['collected'] == 2000
    assert db.totals('2026-01')['spent'] == 1500
    assert db.totals('2026-01')['operating'] == 0
    assert db.totals('2026-02')['collected'] == 8000
    assert db.totals('2026-03')['sales'] == 10000
    assert db.totals('2026-03')['result'] == 7000
