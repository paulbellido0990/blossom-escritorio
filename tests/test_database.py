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
