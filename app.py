"""BLOSSOM | Sistema de ventas local para Windows (Tkinter + SQLite)."""
from datetime import date
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from db import (Database, bs, METHODS, STATES, MODES, EXPENSE_CATEGORIES)

PINK = '#EFAFC8'
ROSE = '#AC4F79'
ROSE_DARK = '#6D3C55'
LIGHT = '#FFF8FB'
PANEL = '#FFFFFF'
SOFT = '#FBE7EF'
MINT = '#E2F5ED'
MINT_TEXT = '#3F8A70'
MUTED = '#927F8B'
BORDER = '#EAD5E0'
NAV_FONT = ('Segoe UI', 11)


def resource_path(name):
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return root / name


class BlossomApp(tk.Tk):
    def __init__(self, db=None):
        super().__init__()
        self.db = db or Database()
        self.title('BLOSSOM · Sistema de ventas')
        self.geometry('1250x810')
        self.minsize(1060, 710)
        self.configure(bg=LIGHT)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.selected_month = date.today().strftime('%Y-%m')
        self._style()
        self._layout()
        self.show_page('Inicio')

    def _style(self):
        sty = ttk.Style(self)
        if 'clam' in sty.theme_names():
            sty.theme_use('clam')
        sty.configure('Treeview', background=PANEL, foreground=ROSE_DARK,
                      fieldbackground=PANEL, borderwidth=0, rowheight=29, font=('Segoe UI', 9))
        sty.configure('Treeview.Heading', background=SOFT, foreground=ROSE_DARK,
                      padding=(5, 10), font=('Segoe UI Semibold', 9), borderwidth=0)
        sty.map('Treeview', background=[('selected', '#F4C4D6')], foreground=[('selected', ROSE_DARK)])
        sty.configure('TEntry', padding=6, font=('Segoe UI', 10))
        sty.configure('TCombobox', padding=6, font=('Segoe UI', 10))
        sty.configure('TScrollbar', background=SOFT)

    def _layout(self):
        self.sidebar = tk.Frame(self, bg='#FCE7EF', width=245)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)
        logo_path = resource_path('assets/logo.png')
        try:
            self.logo = tk.PhotoImage(file=str(logo_path)).subsample(2, 2)
            tk.Label(self.sidebar, image=self.logo, bg='#FCE7EF').pack(pady=(21, 8))
        except tk.TclError:
            tk.Label(self.sidebar, text='BLOSSOM 🌸', font=('Georgia', 23, 'bold'),
                     fg=ROSE, bg='#FCE7EF').pack(pady=(40, 20))
        tk.Label(self.sidebar, text='GESTIÓN LOCAL  ·  Bs', bg='#FCE7EF', fg=ROSE_DARK,
                 font=('Segoe UI Semibold', 9)).pack(pady=(0, 24))
        self.buttons = {}
        for label, glyph in [('Inicio', '⌂'), ('Ventas', '▤'), ('Gastos', '▦'),
                             ('Estadísticas', '▥'), ('Configuración', '⚙')]:
            b = tk.Button(self.sidebar, text=f'   {glyph}    {label}',
                          bg='#FCE7EF', fg=ROSE_DARK, relief='flat', bd=0,
                          activebackground='#F5D0DF', activeforeground=ROSE_DARK,
                          anchor='w', font=NAV_FONT, cursor='hand2',
                          padx=10, pady=15, command=lambda n=label: self.show_page(n))
            b.pack(fill='x', padx=15, pady=3)
            self.buttons[label] = b
        tk.Frame(self.sidebar, bg='#FCE7EF').pack(fill='both', expand=True)
        tk.Label(self.sidebar, text='Sin internet · Datos en tu equipo', bg='#FCE7EF',
                 fg=MUTED, font=('Segoe UI', 9)).pack(pady=(0, 18))

        self.body = tk.Frame(self, bg=LIGHT)
        self.body.pack(side='left', fill='both', expand=True)
        self.header = tk.Frame(self.body, bg=LIGHT)
        self.header.pack(fill='x', padx=31, pady=(24, 13))
        self.title_lbl = tk.Label(self.header, text='', font=('Segoe UI Semibold', 22),
                                  fg=ROSE_DARK, bg=LIGHT)
        self.title_lbl.pack(side='left')
        self.date_lbl = tk.Label(self.header, text=date.today().strftime('%d/%m/%Y') + '  ·  BOB (Bs)',
                                 font=('Segoe UI', 10), fg=MUTED, bg=LIGHT)
        self.date_lbl.pack(side='right')
        self.content = tk.Frame(self.body, bg=LIGHT)
        self.content.pack(fill='both', expand=True, padx=31, pady=(0, 20))

    def show_page(self, page):
        self.title_lbl.config(text=page if page != 'Inicio' else 'Resumen de BLOSSOM')
        for name, b in self.buttons.items():
            b.configure(bg=('#F3C5D8' if name == page else '#FCE7EF'))
        for widget in self.content.winfo_children():
            widget.destroy()
        actions = {'Inicio': self.home, 'Ventas': self.sales_page, 'Gastos': self.expenses_page,
                   'Estadísticas': self.stats_page, 'Configuración': self.settings_page}
        actions[page]()

    def _heading(self, parent, title, subtitle):
        tk.Label(parent, text=title, bg=LIGHT, fg=ROSE_DARK,
                 font=('Segoe UI Semibold', 14)).pack(anchor='w')
        tk.Label(parent, text=subtitle, bg=LIGHT, fg=MUTED,
                 font=('Segoe UI', 9)).pack(anchor='w', pady=(2, 13))

    def _card(self, parent, label, amount, tone=SOFT, large=True):
        frm = tk.Frame(parent, bg=tone, highlightbackground=BORDER, highlightthickness=1,
                       padx=18, pady=17)
        tk.Label(frm, text=label.upper(), fg=MUTED, bg=tone,
                 font=('Segoe UI Semibold', 9)).pack(anchor='w')
        tk.Label(frm, text=amount, fg=ROSE_DARK if tone != MINT else MINT_TEXT,
                 bg=tone, font=('Segoe UI Semibold', 20 if large else 14)).pack(anchor='w', pady=(8, 0))
        return frm

    def _btn(self, parent, text, action, primary=False, mint=False):
        bg = MINT if mint else (ROSE if primary else SOFT)
        fg = MINT_TEXT if mint else ('white' if primary else ROSE_DARK)
        return tk.Button(parent, text=text, command=action, bg=bg, fg=fg,
                         activebackground=PINK, activeforeground=ROSE_DARK,
                         font=('Segoe UI Semibold', 9), padx=14, pady=10,
                         relief='flat', bd=0, cursor='hand2')

    def _field(self, parent, text, key, row, col, default='', options=None, span=1):
        frm = tk.Frame(parent, bg=PANEL)
        frm.grid(row=row, column=col, columnspan=span, sticky='ew', padx=7, pady=7)
        tk.Label(frm, text=text, bg=PANEL, fg=ROSE_DARK, font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 4))
        val = tk.StringVar(value=default)
        if options:
            wid = ttk.Combobox(frm, textvariable=val, values=list(options), state='readonly')
        else:
            wid = ttk.Entry(frm, textvariable=val)
        wid.pack(fill='x')
        return val

    def _make_tree(self, parent, columns, widths=None, height=10):
        outer = tk.Frame(parent, bg=PANEL)
        outer.pack(fill='both', expand=True)
        tree = ttk.Treeview(outer, columns=columns, show='headings', height=height, selectmode='browse')
        for i, c in enumerate(columns):
            tree.heading(c, text=c)
            tree.column(c, anchor='w' if i in (1,2,3) else 'center',
                        width=(widths[i] if widths else 120), minwidth=62, stretch=True)
        sy = ttk.Scrollbar(outer, orient='vertical', command=tree.yview)
        sx = ttk.Scrollbar(outer, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        tree.grid(row=0, column=0, sticky='nsew')
        sy.grid(row=0, column=1, sticky='ns')
        sx.grid(row=1, column=0, sticky='ew')
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        return tree

    def _safe(self, func):
        try:
            return func()
        except (ValueError, OSError) as exc:
            messagebox.showerror('BLOSSOM · Revisa los datos', str(exc), parent=self)
        except Exception as exc:
            messagebox.showerror('BLOSSOM · Error', f'No se pudo completar la acción: {exc}', parent=self)

    def home(self):
        t = self.db.totals(self.selected_month)
        all_t = self.db.totals()
        self._heading(self.content, 'Tu negocio, de un vistazo',
                      'Resumen mensual de ventas entregadas y movimiento de efectivo. Valores en bolivianos.')
        row = tk.Frame(self.content, bg=LIGHT)
        row.pack(fill='x', pady=(3, 21))
        cards = [('Ventas del mes', bs(t['sales']), SOFT),
                 ('Cobros del mes', bs(t['collected']), '#F6EBF6'),
                 ('Gastos pagados', bs(t['spent']), '#FFF2E3'),
                 ('Resultado estimado', bs(t['result']), MINT)]
        for i, (name,value,tone) in enumerate(cards):
            row.columnconfigure(i, weight=1)
            self._card(row, name, value, tone).grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 5, 5))
        strip = tk.Frame(self.content, bg=PANEL, padx=18, pady=12,
                         highlightbackground=BORDER, highlightthickness=1)
        strip.pack(fill='x', pady=(0, 22))
        tk.Label(strip, text=f'Por cobrar: {bs(all_t["pending"])}', fg=ROSE_DARK,
                 bg=PANEL, font=('Segoe UI Semibold', 11)).pack(side='left', padx=(0, 30))
        tk.Label(strip, text=f'Caja estimada: {bs(self.db.cash_balance())}', fg=MINT_TEXT,
                 bg=PANEL, font=('Segoe UI Semibold', 11)).pack(side='left')
        btns = tk.Frame(self.content, bg=LIGHT)
        btns.pack(fill='x', pady=(0, 16))
        self._btn(btns,'+ Nueva venta',lambda:self.show_page('Ventas'),True).pack(side='left',padx=(0, 8))
        self._btn(btns,'+ Registrar gasto',lambda:self.show_page('Gastos')).pack(side='left',padx=(0, 8))
        self._btn(btns,'Ver estadísticas',lambda:self.show_page('Estadísticas'),mint=True).pack(side='left')
        self._heading(self.content,'Últimos pedidos','Selecciona Ventas para añadir cobros o cambiar el estado.')
        tree = self._make_tree(self.content, ('ID','Fecha','Cliente','Producto','Estado','Total','Cobrado','Saldo'),
                               [55,95,145,190,112,110,110,110],height=8)
        for s in self.db.sales(limit=12):
            tree.insert('', 'end', values=(f'V-{s["id"]:04d}',s['sale_date'],s['client'],
                s['product'],s['status'],bs(s['total_cents']),bs(s['paid_cents']),
                bs(s['total_cents']-s['paid_cents'])))

    def sales_page(self):
        self._heading(self.content,'Registro de ventas','Encargos y productos listos · Adelantos y cobros por partes · Historial.')
        notebook = ttk.Notebook(self.content)
        notebook.pack(fill='both', expand=True)
        new = tk.Frame(notebook,bg=LIGHT)
        hist = tk.Frame(notebook,bg=LIGHT)
        notebook.add(new,text='  Nueva venta  ')
        notebook.add(hist,text='  Historial y cobros  ')
        form = tk.Frame(new,bg=PANEL,padx=13,pady=14,
                        highlightbackground=BORDER,highlightthickness=1)
        form.pack(fill='x',pady=(14, 13))
        for j in range(4): form.columnconfigure(j,weight=1)
        defs = [
          ('Cliente *','client',0,0,''),('WhatsApp (opcional)','phone',0,1,''),
          ('Flor o arreglo *','product',0,2,''),('Modalidad','mode',0,3,'Encargo',MODES),
          ('Cantidad','qty',1,0,'1'),('Precio por unidad (Bs)','price',1,1,''),
          ('Costo completo por unidad (Bs)','cost',1,2,''),('Estado del pedido','status',1,3,'Pendiente',STATES[:-1]),
          ('Envío cobrado (Bs)','shipping',2,0,'0'),('Descuento (Bs)','discount',2,1,'0'),
          ('Adelanto recibido (Bs)','advance',2,2,'0'),('Medio de adelanto','method',2,3,'Efectivo',METHODS),
          ('Fecha (AAAA-MM-DD)','sale_date',3,0,date.today().isoformat()),
          ('Observaciones','notes',3,1,'',None,3),
        ]
        self.sales_vars = {}
        for item in defs:
            label,key,row,col,default,*rest=item
            options=rest[0] if rest else None
            span=rest[1] if len(rest)>1 else 1
            self.sales_vars[key] = self._field(form,label,key,row,col,default,options,span)
        ctrl = tk.Frame(new,bg=LIGHT)
        ctrl.pack(fill='x',pady=(0, 10))
        self._btn(ctrl,'Guardar venta',self.save_sale,primary=True).pack(side='left')
        tk.Label(ctrl,text='El costo por unidad incluye materiales, empaque y tu tiempo de elaboración.',
                 bg=LIGHT,fg=MUTED,font=('Segoe UI',9)).pack(side='left',padx=16)
        lower = tk.Frame(new,bg=MINT,padx=15,pady=14)
        lower.pack(fill='x')
        tk.Label(lower,text='¿Qué pasa al guardar?',fg=MINT_TEXT,bg=MINT,
                 font=('Segoe UI Semibold',10)).pack(anchor='w')
        tk.Label(lower,text='La venta queda registrada. Si hay adelanto, se registra un cobro. '
                 'El ingreso se reconoce como venta cuando cambies su estado a Entregado.',
                 fg=MINT_TEXT,bg=MINT,font=('Segoe UI',9),wraplength=780,justify='left').pack(anchor='w',pady=(5,0))

        search_frame=tk.Frame(hist,bg=LIGHT)
        search_frame.pack(fill='x',pady=(14,8))
        tk.Label(search_frame,text='Buscar:',bg=LIGHT,fg=ROSE_DARK).pack(side='left')
        self.search_var=tk.StringVar()
        ent=ttk.Entry(search_frame,textvariable=self.search_var,width=30)
        ent.pack(side='left',padx=10)
        self._btn(search_frame,'Buscar',self.refresh_sales).pack(side='left')
        self._btn(search_frame,'Exportar CSV',self.export_sales,mint=True).pack(side='right')
        self.sales_tree=self._make_tree(hist,('ID','Fecha','Cliente','Arreglo','Estado','Total','Cobrado','Saldo'),
                                        [68,102,140,165,124,102,102,102],height=12)
        actions=tk.Frame(hist,bg=LIGHT)
        actions.pack(fill='x',pady=(12,0))
        for text,call,highlight in [
           ('Registrar cobro',self.ui_add_payment,True),('Devolver cobro',self.ui_refund,False),
           ('Cambiar estado',self.ui_change_status,False),('Ver pagos',self.ui_payment_history,False)]:
            self._btn(actions,text,call,primary=highlight).pack(side='left',padx=(0,7))
        self.refresh_sales()

    def save_sale(self):
        def task():
            d={k:v.get() for k,v in self.sales_vars.items()}
            sid=self.db.add_sale(d['client'],d['product'],d['mode'],d['qty'],d['price'],d['cost'],
                 d['shipping'],d['discount'],d['phone'],d['notes'],d['sale_date'],d['status'],
                 d['advance'],d['method'])
            messagebox.showinfo('Venta guardada',f'¡Listo! Se registró la venta V-{sid:04d}.',parent=self)
            self.show_page('Ventas')
        self._safe(task)

    def refresh_sales(self):
        for child in self.sales_tree.get_children(): self.sales_tree.delete(child)
        for s in self.db.sales(query=self.search_var.get()):
            bal=s['total_cents']-s['paid_cents']
            self.sales_tree.insert('', 'end', iid=str(s['id']), values=(
                f'V-{s["id"]:04d}', s['sale_date'],s['client'],s['product'],s['status'],
                bs(s['total_cents']),bs(s['paid_cents']),bs(bal)))

    def selected_sale_id(self):
        selection=self.sales_tree.selection()
        if not selection:
            messagebox.showwarning('Selecciona una venta','Primero selecciona una fila del historial.',parent=self)
            return None
        return int(selection[0])

    def ui_add_payment(self):
        sale_id=self.selected_sale_id()
        if sale_id is None:return
        s=self.db.sale(sale_id)
        bal=s['total_cents']-s['paid_cents']
        raw=simpledialog.askstring('Nuevo cobro',f'Venta V-{sale_id:04d}\nSaldo: {bs(bal)}\n\nImporte recibido (Bs):',parent=self)
        if raw is None:return
        method=self.choose_method('Medio de cobro')
        if method is None:return
        self._safe(lambda:self.db.add_payment(sale_id,raw,method))
        self.refresh_sales()

    def ui_refund(self):
        sid=self.selected_sale_id()
        if sid is None:return
        s=self.db.sale(sid)
        raw=simpledialog.askstring('Devolver cobro',f'Venta V-{sid:04d}\nCobrado neto: {bs(s["paid_cents"])}\n\nImporte a devolver (Bs):',parent=self)
        if raw is None:return
        method=self.choose_method('Medio de devolución')
        if method is None:return
        self._safe(lambda:self.db.refund(sid,raw,method))
        self.refresh_sales()

    def choose_method(self,title):
        win=tk.Toplevel(self)
        win.title(title)
        win.geometry('360x160')
        win.resizable(False,False)
        win.configure(bg=LIGHT)
        win.transient(self)
        win.grab_set()
        selected=tk.StringVar(value='Efectivo')
        tk.Label(win,text=title,bg=LIGHT,fg=ROSE_DARK,font=('Segoe UI Semibold',12)).pack(pady=(17,8))
        ttk.Combobox(win,values=METHODS,textvariable=selected,state='readonly',width=25).pack(pady=4)
        result=[]
        def done(): result.append(selected.get());win.destroy()
        self._btn(win,'Aceptar',done,True).pack(pady=10)
        self.wait_window(win)
        return result[0] if result else None

    def ui_change_status(self):
        sid=self.selected_sale_id()
        if sid is None:return
        s=self.db.sale(sid)
        win=tk.Toplevel(self)
        win.title('Estado del pedido')
        win.geometry('365x192')
        win.resizable(False,False)
        win.configure(bg=LIGHT)
        win.transient(self);win.grab_set()
        tk.Label(win,text=f'Venta V-{sid:04d} · Estado actual: {s["status"]}',bg=LIGHT,
                 fg=ROSE_DARK,font=('Segoe UI Semibold',10)).pack(pady=(22,12))
        state=tk.StringVar(value=s['status'])
        ttk.Combobox(win,textvariable=state,values=STATES,state='readonly',width=28).pack()
        def save():
            if self._safe(lambda:self.db.set_status(sid,state.get())) is None:
                # El método sin retorno también retorna None: comprobamos la BD.
                pass
            if self.db.sale(sid)['status']==state.get():
                win.destroy();self.refresh_sales()
        self._btn(win,'Actualizar estado',save,True).pack(pady=16)

    def ui_payment_history(self):
        sid=self.selected_sale_id()
        if sid is None:return
        records=self.db.sale_payments(sid)
        text='\n'.join(f'{p["payment_date"]}  ·  {p["method"]}  ·  {bs(p["amount_cents"])}'
                       for p in records) or 'Este pedido aún no tiene cobros.'
        messagebox.showinfo(f'Cobros de V-{sid:04d}',text,parent=self)

    def expenses_page(self):
        self._heading(self.content,'Control de gastos',
                      'Cada gasto supone dinero pagado. Separa compras de materiales de otros gastos para no duplicar costos.')
        form=tk.Frame(self.content,bg=PANEL,padx=12,pady=11,highlightbackground=BORDER,highlightthickness=1)
        form.pack(fill='x',pady=(0,12))
        for j in range(3):form.columnconfigure(j,weight=1)
        self.exp_vars={}
        for label,key,r,c,default,opts in [
            ('Fecha (AAAA-MM-DD)','date',0,0,date.today().isoformat(),None),
            ('Categoría','category',0,1,'Compra de materiales',EXPENSE_CATEGORIES),
            ('Medio de pago','method',0,2,'Efectivo',METHODS),
            ('Descripción','description',1,0,'',None),
            ('Importe pagado (Bs)','amount',1,1,'',None),
            ('Nota (opcional)','notes',1,2,'',None),
        ]:
            self.exp_vars[key]=self._field(form,label,key,r,c,default,opts)
        self._btn(self.content,'Guardar gasto',self.save_expense,True).pack(anchor='w',pady=(0,17))
        actions=tk.Frame(self.content,bg=LIGHT)
        actions.pack(fill='x',pady=(0,9))
        tk.Label(actions,text='Gastos recientes',bg=LIGHT,fg=ROSE_DARK,
                 font=('Segoe UI Semibold',13)).pack(side='left')
        self._btn(actions,'Exportar CSV',self.export_expenses,mint=True).pack(side='right')
        tree=self._make_tree(self.content,('ID','Fecha','Categoría','Descripción','Importe','Medio'),
                             [60,105,165,270,120,110],height=14)
        for e in self.db.expenses():
            tree.insert('','end',values=(f'G-{e["id"]:04d}',e['expense_date'],e['category'],
                e['description'],bs(e['amount_cents']),e['method']))

    def save_expense(self):
        def task():
            v={k:x.get() for k,x in self.exp_vars.items()}
            eid=self.db.add_expense(v['category'],v['description'],v['amount'],v['method'],v['date'],v['notes'])
            messagebox.showinfo('Gasto registrado',f'Se guardó el gasto G-{eid:04d}.',parent=self)
            self.show_page('Gastos')
        self._safe(task)

    def stats_page(self):
        self._heading(self.content,'Estadísticas y resultados',
                      'Ventas entregadas, costo registrado por unidad y gastos operativos del periodo.')
        toolbar=tk.Frame(self.content,bg=LIGHT)
        toolbar.pack(fill='x',pady=(0,15))
        tk.Label(toolbar,text='Año:',bg=LIGHT,fg=ROSE_DARK).pack(side='left')
        self.year_var=tk.StringVar(value=str(date.today().year))
        ttk.Combobox(toolbar,textvariable=self.year_var,values=[str(n) for n in range(2024,2036)],
                     width=8,state='readonly').pack(side='left',padx=12)
        self._btn(toolbar,'Actualizar',self.redraw_stats).pack(side='left')
        self.stats_metrics=tk.Frame(self.content,bg=LIGHT)
        self.stats_metrics.pack(fill='x',pady=(0,15))
        self.chart_frame=tk.Frame(self.content,bg=PANEL,padx=12,pady=12,
                                  highlightbackground=BORDER,highlightthickness=1)
        self.chart_frame.pack(fill='both',expand=True)
        self.chart_title=tk.Label(self.chart_frame,text='Ventas y gastos operativos por mes',
                                  fg=ROSE_DARK,bg=PANEL,font=('Segoe UI Semibold',13))
        self.chart_title.pack(anchor='w',pady=(0,10))
        self.canvas=tk.Canvas(self.chart_frame,bg=PANEL,bd=0,highlightthickness=0,height=310)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw_chart())
        tk.Label(self.chart_frame,text=' Rosa: ventas entregadas   ·   Verde: gastos operativos',
                 bg=PANEL,fg=MUTED,font=('Segoe UI',9)).pack(anchor='e')
        self.redraw_stats()

    def redraw_stats(self):
        year=int(self.year_var.get())
        self.chart_data=self.db.monthly_series(year)
        sold=sum(x['sales'] for _,x in self.chart_data)
        cost=sum(x['cost'] for _,x in self.chart_data)
        op=sum(x['operating'] for _,x in self.chart_data)
        for w in self.stats_metrics.winfo_children():w.destroy()
        for j,(lab,value,tone) in enumerate([
            ('Ventas entregadas',bs(sold),SOFT),('Costos de producción',bs(cost),'#FFF0E5'),
            ('Gastos operativos',bs(op),'#F5EDF8'),('Resultado estimado',bs(sold-cost-op),MINT)]):
            self.stats_metrics.columnconfigure(j,weight=1)
            self._card(self.stats_metrics,lab,value,tone,large=False).grid(
                row=0,column=j,sticky='ew',padx=(0 if j==0 else 5,5))
        self.draw_chart()

    def draw_chart(self):
        if not hasattr(self,'canvas') or not hasattr(self,'chart_data'):return
        c=self.canvas;c.delete('all')
        w=max(c.winfo_width(),600);h=max(c.winfo_height(),275)
        left,top,right,bottom=62,25,18,47
        plot_w=w-left-right;plot_h=h-top-bottom
        mx=max([1]+[max(t['sales'],t['operating']) for _,t in self.chart_data])
        mx*=1.15
        for i in range(5):
            value=mx*(4-i)/4
            y=top+i*plot_h/4
            c.create_line(left,y,w-right,y,fill='#F2E7ED')
            c.create_text(left-10,y,text=f'{int(value/100):,}',anchor='e',fill=MUTED,
                          font=('Segoe UI',8))
        names=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
        slot=plot_w/12
        bw=max(8,min(21,slot*.27))
        for i, (_,t) in enumerate(self.chart_data):
            cx=left+slot*(i+.5)
            for shift,key,color in [(-bw*.55,'sales',ROSE),(bw*.55,'operating',MINT_TEXT)]:
                height=(t[key]/mx)*plot_h
                c.create_rectangle(cx+shift-bw/2,top+plot_h-height,
                                   cx+shift+bw/2,top+plot_h,fill=color,outline='')
            c.create_text(cx,top+plot_h+17,text=names[i],font=('Segoe UI',9),fill=ROSE_DARK)
        c.create_text(w-right,h-5,anchor='se',text='Importes en Bs · cifras antes de impuestos',
                      font=('Segoe UI',8),fill=MUTED)

    def settings_page(self):
        self._heading(self.content,'Configuración y seguridad',
                      'Tu información se guarda en tu equipo; realiza copias de seguridad frecuentemente.')
        panel=tk.Frame(self.content,bg=PANEL,padx=24,pady=24,
                       highlightbackground=BORDER,highlightthickness=1)
        panel.pack(fill='x',pady=(0,17))
        tk.Label(panel,text='Saldo inicial de caja (Bs)',bg=PANEL,fg=ROSE_DARK,
                 font=('Segoe UI Semibold',11)).pack(anchor='w')
        self.balance_var=tk.StringVar(value=str(self.db.initial_balance()/100).replace('.',','))
        ttk.Entry(panel,textvariable=self.balance_var,width=24).pack(anchor='w',pady=9)
        self._btn(panel,'Guardar saldo inicial',self.save_balance,True).pack(anchor='w')
        tk.Label(panel,text='El saldo inicial se cuenta una sola vez. Si ya tienes movimientos registrados,\n'
                 'no lo modifiques para representar ingresos nuevos.',bg=PANEL,fg=MUTED,
                 justify='left',font=('Segoe UI',9)).pack(anchor='w',pady=(11,0))
        tk.Frame(self.content,height=1,bg=BORDER).pack(fill='x',pady=(9,20))
        tk.Label(self.content,text='Copia de seguridad SQLite',bg=LIGHT,fg=ROSE_DARK,
                 font=('Segoe UI Semibold',13)).pack(anchor='w')
        tk.Label(self.content,text='Guarda una copia de todas tus ventas, pagos y gastos en un archivo .db.',
                 bg=LIGHT,fg=MUTED,font=('Segoe UI',9)).pack(anchor='w',pady=(5,12))
        self._btn(self.content,'Guardar copia de seguridad',self.ui_backup,mint=True).pack(anchor='w')
        tk.Label(self.content,text='Ubicación de datos: '+str(self.db.path),bg=LIGHT,fg=MUTED,
                 wraplength=800,justify='left',font=('Segoe UI',9)).pack(anchor='w',pady=(24,8))
        tk.Label(self.content,text='BLOSSOM v0.1  ·  Moneda: bolivianos (Bs)  ·  Impuestos: por configurar',
                 bg=LIGHT,fg=MUTED,font=('Segoe UI',9)).pack(anchor='w')

    def save_balance(self):
        def task():
            self.db.set_initial_balance(self.balance_var.get())
            messagebox.showinfo('Configuración','Saldo inicial actualizado.',parent=self)
        self._safe(task)

    def ui_backup(self):
        filename=f'BLOSSOM_respaldo_{date.today().strftime("%Y%m%d")}.db'
        path=filedialog.asksaveasfilename(parent=self,title='Guardar respaldo de BLOSSOM',
                                           defaultextension='.db',initialfile=filename,
                                           filetypes=[('Base de datos SQLite','*.db')])
        if not path:return
        self._safe(lambda:(self.db.backup(path),messagebox.showinfo('Respaldo guardado',
                                'La copia se guardó correctamente.',parent=self)))

    def export_sales(self):
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.csv',
               initialfile='BLOSSOM_ventas.csv',filetypes=[('Archivo CSV','*.csv')])
        if path:self._safe(lambda:(self.db.export_sales_csv(path),
                             messagebox.showinfo('Exportado','Ventas exportadas.',parent=self)))

    def export_expenses(self):
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.csv',
               initialfile='BLOSSOM_gastos.csv',filetypes=[('Archivo CSV','*.csv')])
        if path:self._safe(lambda:(self.db.export_expenses_csv(path),
                             messagebox.showinfo('Exportado','Gastos exportados.',parent=self)))

    def close(self):
        self.db.close()
        self.destroy()


if __name__=='__main__':
    BlossomApp().mainloop()
