"""Datos locales de BLOSSOM. Todos los importes se guardan en centavos de Bs."""
import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import os
import sqlite3

METHODS = ('Efectivo', 'QR', 'Transferencia', 'Otro')
STATES = ('Pendiente', 'En preparación', 'Listo', 'Entregado', 'Cancelado')
MODES = ('Encargo', 'Disponible')
EXPENSE_CATEGORIES = (
    'Compra de materiales', 'Delivery', 'Publicidad', 'Servicios',
    'Empaque adicional', 'Mantenimiento', 'Equipamiento', 'Retiro personal', 'Otros',
)
# Las compras de materiales y los activos no se descuentan dos veces del resultado
# cuando el costo de producción ya está registrado por producto.
NON_OPERATING = ('Compra de materiales', 'Equipamiento', 'Retiro personal')


def to_cents(value):
    """Acepta 1234,50 o 1234.50; devuelve un entero, nunca float."""
    if isinstance(value, int):
        return value * 100
    raw = str(value).replace('Bs.', '').replace('Bs', '').replace(' ', '').strip()
    if not raw:
        raw = '0'
    if ',' in raw and '.' in raw:
        # El último separador se toma como separador decimal.
        if raw.rfind(',') > raw.rfind('.'):
            raw = raw.replace('.', '').replace(',', '.')
        else:
            raw = raw.replace(',', '')
    else:
        raw = raw.replace(',', '.')
    try:
        d = Decimal(raw)
        if not d.is_finite():
            raise ValueError('Importe no válido')
        return int((d * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('Introduce un importe numérico válido.') from exc


def bs(cents):
    n = (Decimal(cents or 0) / 100).quantize(Decimal('0.01'))
    formatted = f'{n:,.2f}'
    return 'Bs ' + formatted.replace(',', '_').replace('.', ',').replace('_', '.')


def database_path():
    root = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / '.local' / 'share'))
    base = root / 'BLOSSOM'
    base.mkdir(parents=True, exist_ok=True)
    return base / 'blossom.db'


class Database:
    def __init__(self, path=None):
        self.path = Path(path or database_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.execute('PRAGMA busy_timeout=3000')
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sales(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_date TEXT NOT NULL,
                client TEXT NOT NULL,
                phone TEXT NOT NULL DEFAULT '',
                product TEXT NOT NULL,
                mode TEXT NOT NULL CHECK(mode IN ('Encargo','Disponible')),
                qty INTEGER NOT NULL CHECK(qty>0),
                price_cents INTEGER NOT NULL CHECK(price_cents>=0),
                cost_cents INTEGER NOT NULL CHECK(cost_cents>=0),
                shipping_cents INTEGER NOT NULL DEFAULT 0 CHECK(shipping_cents>=0),
                discount_cents INTEGER NOT NULL DEFAULT 0 CHECK(discount_cents>=0),
                status TEXT NOT NULL DEFAULT 'Pendiente',
                delivery_date TEXT,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS payments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE RESTRICT,
                payment_date TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK(amount_cents <> 0),
                method TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
                method TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS ix_sales_date ON sales(sale_date);
            CREATE INDEX IF NOT EXISTS ix_sales_delivery ON sales(delivery_date);
            CREATE INDEX IF NOT EXISTS ix_payments_sale ON payments(sale_id);
            CREATE INDEX IF NOT EXISTS ix_payments_date ON payments(payment_date);
            CREATE INDEX IF NOT EXISTS ix_expenses_date ON expenses(expense_date);
            INSERT OR IGNORE INTO settings(key,value) VALUES('initial_balance_cents','0');
        ''')
        self.conn.commit()

    def close(self):
        self.conn.close()

    def setting(self, key, default=''):
        row = self.conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return row['value'] if row else default

    def set_initial_balance(self, value):
        cents = to_cents(value)
        if cents < 0:
            raise ValueError('El saldo inicial debe ser igual o mayor que cero.')
        with self.conn:
            self.conn.execute("UPDATE settings SET value=? WHERE key='initial_balance_cents'", (str(cents),))

    def initial_balance(self):
        return int(self.setting('initial_balance_cents', '0'))

    @staticmethod
    def _date(text, field='Fecha'):
        try:
            return date.fromisoformat(text).isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{field}: utiliza AAAA-MM-DD.') from exc

    def add_sale(self, client, product, mode, qty, price, cost, shipping='0', discount='0',
                 phone='', notes='', sale_date=None, status='Pendiente', advance='0', method='Efectivo'):
        client = client.strip()
        product = product.strip()
        if not client or not product:
            raise ValueError('Escribe el cliente y el producto.')
        if mode not in MODES or status not in STATES or status == 'Cancelado':
            raise ValueError('Selecciona una modalidad y un estado válidos.')
        if method not in METHODS:
            raise ValueError('Selecciona un medio de cobro válido.')
        try:
            quantity = int(qty)
        except (TypeError, ValueError) as exc:
            raise ValueError('La cantidad debe ser un número entero.') from exc
        if quantity < 1:
            raise ValueError('La cantidad debe ser mayor que cero.')
        unit_price, unit_cost = to_cents(price), to_cents(cost)
        envio, descuento, adelanto = to_cents(shipping), to_cents(discount), to_cents(advance)
        if min(unit_price, unit_cost, envio, descuento, adelanto) < 0:
            raise ValueError('Los precios, costos y cobros no pueden ser negativos.')
        amount = quantity * unit_price + envio - descuento
        if amount <= 0:
            raise ValueError('El total debe ser mayor que cero.')
        if adelanto > amount:
            raise ValueError('El adelanto no puede superar el total de la venta.')
        when = self._date(sale_date or date.today().isoformat())
        delivered = when if status == 'Entregado' else None
        with self.conn:
            cur = self.conn.execute('''
                INSERT INTO sales(sale_date,client,phone,product,mode,qty,price_cents,cost_cents,
                    shipping_cents,discount_cents,status,delivery_date,notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (when, client, phone.strip(), product, mode, quantity, unit_price, unit_cost,
                 envio, descuento, status, delivered, notes.strip()))
            sale_id = cur.lastrowid
            if adelanto:
                self.conn.execute('''INSERT INTO payments(sale_id,payment_date,amount_cents,method,notes)
                    VALUES(?,?,?,?,?)''', (sale_id, when, adelanto, method, 'Adelanto inicial'))
        return sale_id

    def sale(self, sale_id):
        row = self.conn.execute('''
            SELECT s.*,
              (s.qty*s.price_cents+s.shipping_cents-s.discount_cents) AS total_cents,
              s.qty*s.cost_cents AS production_cents,
              COALESCE((SELECT SUM(p.amount_cents) FROM payments p WHERE p.sale_id=s.id),0) AS paid_cents
            FROM sales s WHERE s.id=?''', (sale_id,)).fetchone()
        if row is None:
            raise ValueError('No se encontró la venta.')
        return row

    def add_payment(self, sale_id, amount, method, when=None):
        s = self.sale(sale_id)
        if s['status'] == 'Cancelado':
            raise ValueError('No se puede cobrar una venta cancelada.')
        if method not in METHODS:
            raise ValueError('Método de cobro no válido.')
        cents = to_cents(amount)
        balance = s['total_cents'] - s['paid_cents']
        if cents <= 0 or cents > balance:
            raise ValueError(f'El cobro debe ser mayor que cero y no superar {bs(balance)}.')
        with self.conn:
            self.conn.execute('INSERT INTO payments(sale_id,payment_date,amount_cents,method) VALUES(?,?,?,?)',
                              (sale_id, self._date(when or date.today().isoformat()), cents, method))

    def refund(self, sale_id, amount, method, when=None):
        s = self.sale(sale_id)
        if method not in METHODS:
            raise ValueError('Método de devolución no válido.')
        cents = to_cents(amount)
        if cents <= 0 or cents > s['paid_cents']:
            raise ValueError(f'La devolución debe ser mayor que cero y no superar {bs(s["paid_cents"])}.')
        with self.conn:
            self.conn.execute('''INSERT INTO payments(sale_id,payment_date,amount_cents,method,notes)
                VALUES(?,?,?,?,?)''',
                (sale_id, self._date(when or date.today().isoformat()), -cents, method, 'Devolución'))

    def set_status(self, sale_id, status, when=None):
        s = self.sale(sale_id)
        if status not in STATES:
            raise ValueError('Estado no válido.')
        if s['status'] == 'Cancelado':
            raise ValueError('Una venta cancelada no puede reabrirse en esta versión.')
        if s['status'] == 'Entregado' and status != 'Entregado':
            raise ValueError('No se puede retroceder un pedido entregado en esta versión.')
        if status == 'Cancelado' and s['paid_cents'] != 0:
            raise ValueError('Debes devolver todos los cobros antes de cancelar el pedido.')
        if status == 'Entregado':
            delivery = self._date(when or date.today().isoformat())
        else:
            delivery = None
        with self.conn:
            self.conn.execute('UPDATE sales SET status=?,delivery_date=? WHERE id=?',
                              (status, delivery, sale_id))

    def sales(self, limit=250, query=''):
        query = query.strip()
        sql = '''SELECT s.id,s.sale_date,s.client,s.product,s.mode,s.qty,s.status,
              s.delivery_date,
              (s.qty*s.price_cents+s.shipping_cents-s.discount_cents) AS total_cents,
              COALESCE((SELECT SUM(p.amount_cents) FROM payments p WHERE p.sale_id=s.id),0) AS paid_cents
              FROM sales s'''
        params = []
        if query:
            sql += ' WHERE s.client LIKE ? OR s.product LIKE ? OR CAST(s.id AS TEXT) LIKE ?'
            params = [f'%{query}%'] * 3
        sql += ' ORDER BY s.id DESC LIMIT ?'
        params.append(limit)
        return self.conn.execute(sql, params).fetchall()

    def sale_payments(self, sale_id):
        return self.conn.execute('SELECT * FROM payments WHERE sale_id=? ORDER BY id', (sale_id,)).fetchall()

    def add_expense(self, category, description, amount, method, when=None, notes=''):
        if category not in EXPENSE_CATEGORIES or method not in METHODS:
            raise ValueError('Categoría o medio de pago no válido.')
        if not description.strip():
            raise ValueError('Escribe una descripción del gasto.')
        cents = to_cents(amount)
        if cents <= 0:
            raise ValueError('El gasto debe ser mayor que cero.')
        when = self._date(when or date.today().isoformat())
        with self.conn:
            return self.conn.execute('''INSERT INTO expenses(expense_date,category,description,amount_cents,method,notes)
                VALUES(?,?,?,?,?,?)''', (when, category, description.strip(), cents, method, notes.strip())).lastrowid

    def expenses(self, limit=250):
        return self.conn.execute('SELECT * FROM expenses ORDER BY id DESC LIMIT ?', (limit,)).fetchall()

    def totals(self, month=None):
        # Ventas devengadas solo cuando están entregadas. Dinero por separado.
        part_sale = " AND substr(delivery_date,1,7)=?" if month else ''
        part_pay = " WHERE substr(payment_date,1,7)=?" if month else ''
        part_exp = " WHERE substr(expense_date,1,7)=?" if month else ''
        saleparams = (month,) if month else ()
        sal = self.conn.execute('''SELECT COUNT(*) AS n,
          COALESCE(SUM(qty*price_cents+shipping_cents-discount_cents),0) AS sold,
          COALESCE(SUM(qty*cost_cents),0) AS cost FROM sales
          WHERE status='Entregado' ''' + part_sale, saleparams).fetchone()
        pay = self.conn.execute('SELECT COALESCE(SUM(amount_cents),0) AS paid FROM payments' + part_pay,
                                saleparams).fetchone()['paid']
        exp = self.conn.execute('''SELECT COALESCE(SUM(amount_cents),0) AS spend,
          COALESCE(SUM(CASE WHEN category IN ('Compra de materiales','Equipamiento','Retiro personal')
               THEN 0 ELSE amount_cents END),0) AS op
          FROM expenses''' + part_exp, saleparams).fetchone()
        unpaid = self.conn.execute('''SELECT COALESCE(SUM(
            MAX(0, qty*price_cents+shipping_cents-discount_cents -
            COALESCE((SELECT SUM(amount_cents) FROM payments p WHERE p.sale_id=s.id),0))),0)
            FROM sales s WHERE status!='Cancelado' ''').fetchone()[0]
        return {'sales':sal['sold'],'cost':sal['cost'],'delivered':sal['n'],
                'collected':pay,'spent':exp['spend'],'operating':exp['op'],
                'result':sal['sold']-sal['cost']-exp['op'],'pending':unpaid}

    def cash_balance(self):
        t = self.totals()
        return self.initial_balance()+t['collected']-t['spent']

    def order_counts(self):
        rows = self.conn.execute('SELECT status,COUNT(*) AS n FROM sales GROUP BY status').fetchall()
        return dict((x['status'],x['n']) for x in rows)

    def monthly_series(self, year):
        return [(f'{year}-{m:02d}', self.totals(f'{year}-{m:02d}')) for m in range(1,13)]

    def backup(self, target):
        target = Path(target)
        if target.resolve() == self.path.resolve():
            raise ValueError('Selecciona una ubicación distinta para la copia.')
        target.parent.mkdir(parents=True, exist_ok=True)
        dest = sqlite3.connect(str(target))
        try:
            self.conn.backup(dest)
        finally:
            dest.close()
        return target

    def export_sales_csv(self, path):
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(['ID','Fecha','Cliente','Producto','Modalidad','Cantidad','Estado','Entrega',
                        'Total (centavos)','Cobrado (centavos)','Por cobrar (centavos)'])
            for s in self.sales(limit=100000):
                w.writerow([s['id'],s['sale_date'],s['client'],s['product'],s['mode'],s['qty'],s['status'],
                            s['delivery_date'],s['total_cents'],s['paid_cents'],
                            s['total_cents']-s['paid_cents']])

    def export_expenses_csv(self, path):
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(['ID','Fecha','Categoría','Descripción','Importe (centavos)','Medio','Notas'])
            for e in self.expenses(limit=100000):
                w.writerow([e['id'],e['expense_date'],e['category'],e['description'],e['amount_cents'],
                            e['method'],e['notes']])
