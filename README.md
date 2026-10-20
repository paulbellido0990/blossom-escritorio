# BLOSSOM · Sistema de ventas (Windows, local)

**Versión 0.1 funcional, pensada para una sola persona.** Interfaz de escritorio en español, con colores rosa pastel y verde menta. Moneda: **bolivianos (Bs/BOB)**. No necesita Internet para usarse.

## 1. Qué hace

- **Inicio:** ventas entregadas, cobros, gastos, resultados estimados, por cobrar y caja estimada.
- **Ventas:** registrar encargos o productos disponibles, cantidad, precio, costo, descuentos, envío, adelanto y medio de pago.
- **Cobros:** cobrar en varias partes, hacer devoluciones y consultar el historial de pagos de un pedido.
- **Pedidos:** estados Pendiente → En preparación → Listo → Entregado; se permite cancelar cuando no hay dinero sin devolver.
- **Gastos:** anotar el dinero pagado por materiales, publicidad, delivery, servicios, equipamiento y otras categorías.
- **Estadísticas:** 12 meses, gráfica comparativa de ventas entregadas y gastos operativos, y resultado estimado.
- **Seguridad:** copia de seguridad de SQLite desde Configuración, exportación de ventas y gastos en CSV.

## 2. La diferencia entre venta y cobro

Un pedido de Bs 100 con un adelanto de Bs 30 genera **Bs 30 en cobros** y **Bs 70 por cobrar**, pero no se contabiliza como venta entregada hasta que lo marcas como **Entregado**. A partir de ese momento, el total del pedido se refleja en las ventas y se compara con su costo registrado.

El resultado estimado es: **ventas entregadas − costos unitarios registrados − gastos operativos**. El saldo de caja estimado es: **saldo inicial + cobros netos − todos los gastos pagados**.

**Importante:** "Compra de materiales", "Equipamiento" y "Retiro personal" disminuyen caja, pero no se descuentan del resultado estimado. El costo unitario del producto debe incluir materiales y producción para evitar restar la misma compra dos veces. Esto es un **indicador gerencial básico**, no un sistema de contabilidad formal ni de impuestos. No registra inventario detallado de insumos ni obligaciones tributarias; los impuestos quedan pendientes de configurar.

## 3. Dónde quedan los datos

Al ejecutar el EXE por primera vez crea la base de datos en:

`%LOCALAPPDATA%\BLOSSOM\blossom.db`

No se guarda dentro del EXE. Si vuelves a abrirlo, los registros siguen allí. **No borres esa carpeta.** Haz un respaldo en una memoria USB o disco externo desde Configuración. No almacenes tu única copia en la misma laptop.

## 4. Cómo crear `BLOSSOM.exe` (opción recomendada: GitHub)

No tienes que instalar Python ni VS Code en la laptop donde vas a usar el programa.

1. Crea en GitHub un repositorio privado, por ejemplo `blossom-escritorio`.
2. Sube **el contenido de esta carpeta** a la raíz del repositorio, **incluida la carpeta oculta `.github/workflows`**.
3. Abre el repositorio en GitHub → pestaña **Actions** → **Crear EXE de BLOSSOM**.
4. Haz clic en **Run workflow** y espera a que finalice.
5. Descarga el archivo de la sección **Artifacts**, cuyo nombre es `BLOSSOM_Windows_Portable`.
6. Descomprime el ZIP descargado: obtendrás **BLOSSOM.exe**.
7. Copia ese EXE a la laptop Windows. Ábrelo con doble clic; no necesita VS Code, Python, servidor ni extensiones.

GitHub necesita conexión durante la compilación y la descarga, pero **la aplicación funciona sin Internet** después. Como el EXE no está firmado, Windows puede solicitar confirmación de seguridad: utilízalo solo si tú mismo lo compilaste y confías en su origen.

## 5. Cómo compilarlo directamente en un PC Windows (alternativa)

Si en un *equipo de desarrollo* tienes Python, ejecuta `crear_exe_en_windows.bat`. Instala PyInstaller y pytest, corre las pruebas y genera `dist\BLOSSOM.exe`. La laptop de BLOSSOM **no necesita** Python.

## 6. Cómo ejecutar el código durante el desarrollo

Requiere Python 3.10+ con Tkinter instalado:

```sh
python app.py
```

Las pruebas de lógica financiera no necesitan interfaz gráfica:

```sh
python -m pytest -q
```

## 7. Limitaciones actuales

- Un solo dispositivo / un usuario; no sincroniza teléfonos ni otras laptops.
- No maneja catálogo, inventario de materiales ni productos terminados todavía.
- Los campos de producto y cliente son libres, sin fichas independientes.
- No se editan ventas ni gastos, ni se eliminan gastos. Las ventas se pueden eliminar con motivo, confirmación, respaldo e historial interno.
- Registro de pagos con métodos Efectivo, QR, Transferencia u Otro, pero **no se separan saldos por cuenta**.
- No factura, no calcula impuestos, no imprime tickets ni integra WhatsApp.
- El archivo EXE debe **compilarse en Windows**. Este paquete contiene el código y las instrucciones de compilación, **no un EXE ya compilado**.

## 8. Archivos

- `app.py` interfaz y navegación.
- `db.py` base de datos SQLite, validación y reportes.
- `assets/logo.png` logo BLOSSOM proporcionado por el negocio (escalado sin modificar su diseño).
- `tests/test_database.py` pruebas automáticas.
- `.github/workflows/windows-exe.yml` compilación de Windows desde GitHub Actions.
- `crear_exe_en_windows.bat` compilación alternativa en Windows.

## 9. Próximos pasos

1. Probar una venta real con adelanto y una entrega.
2. Confirmar si quieres separar efectivo, QR y bancos.
3. Incorporar edición controlada de registros, catálogo, inventario y reportes de rentabilidad.
4. Ampliar las correcciones auditables y permitir elegir una ubicación externa para los respaldos automáticos.

## Mejoras implementadas: protección de datos y eliminación

- En **Ventas → Historial y cobros**, selecciona una venta y pulsa **Eliminar venta**. Indica un motivo y confirma. Se eliminan la venta y sus pagos/devoluciones; se recalculan caja y reportes. Esta acción corrige registros: no sustituye una devolución real de dinero.
- Antes de eliminar se crea un respaldo completo. El detalle eliminado y el motivo quedan en la tabla interna `audit_log`.
- En **Configuración → Restaurar copia de seguridad** puedes cargar un respaldo compatible. Primero se validan integridad, estructura y relaciones, y se guarda una copia de los datos actuales. La restauración reemplaza el conjunto completo de datos.
- Al iniciar se crea un respaldo diario; se conservan los últimos 30 días de uso. Los respaldos previos a eliminación, restauración y migración se conservan por separado.
- Las copias automáticas se guardan junto a la base, en `blossom_respaldos`. Mantén además copias externas desde Configuración.
- Volver a seleccionar Entregado conserva la fecha original de entrega.
- La base utiliza `PRAGMA user_version=1`; se admiten respaldos de la versión inicial y se incorpora el historial interno al restaurarlos.
