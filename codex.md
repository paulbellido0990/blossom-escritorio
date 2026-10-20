# BLOSSOM: descripción del sistema y posibles mejoras

Documento basado en la revisión de README.md, app.py, db.py, las pruebas y los archivos de compilación.

## 1. Qué es el sistema

BLOSSOM es una aplicación de escritorio para Windows orientada a gestionar las ventas de un pequeño negocio. Está pensada para una persona y un dispositivo, funciona sin Internet y utiliza bolivianos (Bs/BOB).

La interfaz está en español y utiliza colores rosa pastel y verde menta. Permite dar seguimiento a encargos y productos disponibles, registrar el dinero recibido y controlar gastos. Sus resultados son indicadores de gestión; no sustituye un sistema de contabilidad formal.

## 2. Qué hace actualmente

### Inicio

Presenta indicadores de ventas entregadas, cobros, gastos, resultado estimado, importes por cobrar y saldo de caja estimado. También muestra cantidades de pedidos por estado.

### Ventas y pedidos

- Registra cliente, teléfono, producto, modalidad (Encargo o Disponible), cantidad, precio y costo unitarios.
- Incluye envío, descuento, notas y adelanto inicial.
- Permite buscar ventas por cliente, producto o identificador.
- Maneja los estados Pendiente, En preparación, Listo, Entregado y Cancelado.
- Impide cancelar si quedan cobros sin devolver, reabrir pedidos cancelados y retroceder pedidos entregados.

Los estados representan el flujo habitual del pedido; el código no exige recorrer todos los estados intermedios.

### Cobros y devoluciones

- Acepta adelantos y pagos parciales con Efectivo, QR, Transferencia u Otro.
- Consulta el historial de pagos de una venta.
- Evita cobrar por encima del saldo pendiente.
- Registra devoluciones como movimientos negativos y evita devolver más de lo cobrado.

Registrar QR o Transferencia identifica el medio declarado: no implica una conexión con bancos ni la verificación automática del pago.

### Gastos

Registra fecha, categoría, descripción, importe, medio de pago y notas. Las categorías incluyen materiales, delivery, publicidad, servicios, empaque, mantenimiento, equipamiento y retiro personal.

### Estadísticas

Muestra una serie de doce meses por año y una gráfica comparativa de ventas entregadas y gastos operativos, junto con el resultado estimado.

### Configuración y datos

- Configura el saldo inicial de caja.
- Crea copias de seguridad de SQLite.
- Exporta ventas y gastos en CSV, con importes expresados en centavos y columnas identificadas como tales.
- Conserva los registros entre sesiones.

## 3. Reglas de cálculo importantes

| Concepto | Cálculo o criterio |
| --- | --- |
| Total de una venta | Cantidad × precio unitario + envío − descuento |
| Costo de producción | Cantidad × costo unitario registrado |
| Cobros netos | Pagos recibidos menos devoluciones |
| Pendiente por venta | Total menos cobros netos |
| Ventas entregadas | Total de pedidos con estado Entregado, según fecha de entrega |
| Resultado estimado | Ventas entregadas − costos de esas ventas − gastos operativos |
| Caja estimada | Saldo inicial + cobros netos − todos los gastos pagados |

Ejemplo: una venta de Bs 100 con adelanto de Bs 30 genera Bs 30 cobrados y Bs 70 pendientes. Solo se incluye en ventas entregadas cuando se marca como Entregado. Puede entregarse aunque todavía exista saldo por cobrar.

Compra de materiales, Equipamiento y Retiro personal reducen la caja, pero se excluyen de los gastos operativos del resultado. El costo unitario debe incorporar materiales y producción para que el indicador sea útil y no duplique costos.

Los reportes mensuales usan la fecha de entrega para ventas, la fecha del pago para cobros y la fecha del gasto para egresos. El indicador por cobrar es global, incluso al consultar totales de un mes.

## 4. Tecnología y estructura

| Archivo o componente | Responsabilidad |
| --- | --- |
| app.py | Interfaz con Tkinter/ttk, formularios, navegación y gráfica |
| db.py | SQLite, validaciones, cálculos, consultas, respaldos y exportaciones |
| tests/test_database.py | Pruebas de importes, ventas, cobros, devoluciones, gastos, respaldos y CSV |
| assets/logo.png | Recurso gráfico utilizado por la aplicación y su compilación |
| crear_exe_en_windows.bat | Instalación de herramientas, ejecución de pruebas y compilación local |
| .github/workflows/windows-exe.yml | Compilación de Windows y publicación del ejecutable como artefacto de GitHub Actions |

La base tiene cuatro tablas principales: settings, sales, payments y expenses. Los importes se guardan como enteros en centavos; las conversiones utilizan Decimal para evitar errores habituales de precisión monetaria.

La base se crea en `%LOCALAPPDATA%\BLOSSOM\blossom.db` en Windows, separada del ejecutable. El programa utiliza transacciones, claves foráneas e índices para las consultas principales.

Para desarrollo se requiere Python 3.10 o superior con Tkinter:

```sh
python app.py
```

Las pruebas existentes se ejecutan con:

```sh
python -m pytest -q
```

La distribución utiliza PyInstaller para generar `dist\BLOSSOM.exe` en Windows. El equipo que utiliza ese ejecutable no necesita Python instalado.

## 5. Limitaciones actuales

- No hay sincronización, acceso desde móviles ni gestión de varios usuarios.
- No existen fichas independientes de clientes ni catálogo de productos.
- No se controla inventario de materiales o productos terminados.
- No se editan ventas ni gastos y no se eliminan gastos. Las ventas se eliminan con motivo, confirmación, respaldo y auditoría interna.
- Los medios de pago no tienen saldos separados por cuenta.
- La interfaz permite crear y restaurar respaldos; los respaldos automáticos aún no tienen una ubicación configurable.
- No hay facturación fiscal, cálculo de impuestos, impresión de tickets ni integración con WhatsApp.
- El listado de ventas y el de gastos tienen un límite predeterminado de 250 registros; las exportaciones consultan hasta 100.000.
- La cobertura automatizada actual se centra en la lógica de datos; no cubre toda la interacción gráfica.

## 6. Posibles mejoras priorizadas

Las siguientes propuestas no describen funciones ya implementadas.

### Prioridad alta: protección de datos y correcciones

1. **Restaurar respaldos desde la interfaz.** Validar integridad y compatibilidad del archivo, cerrar correctamente las conexiones y crear una copia previa antes de sustituir datos.
2. **Respaldos automáticos.** Guardar copias periódicas con fecha, política de conservación y una ubicación elegida por la persona usuaria. Mostrar cuándo se completó el último respaldo.
3. **Correcciones con historial.** Permitir corregir ventas y gastos guardando valor anterior, motivo y fecha. Definir cómo afectan las correcciones a pagos y reportes históricos.
4. **Proteger la fecha de entrega.** Evitar que volver a seleccionar Entregado cambie accidentalmente la fecha y traslade la venta a otro mes. Implementado: repetir Entregado conserva la fecha original.
5. **Versionar la base de datos.** Incorporar migraciones explícitas y respaldo previo para actualizar la estructura sin perder información.
6. **Ampliar pruebas de reglas sensibles.** Cubrir fechas de entrega repetidas, límites entre meses, devoluciones posteriores a la entrega, transiciones de estados y fallos de respaldo.

### Prioridad media: operación diaria

1. **Clientes y productos.** Crear fichas reutilizables con teléfono, precios, costos y búsqueda, conservando en cada venta los valores históricos utilizados.
2. **Pedidos con varios productos.** Separar cabecera del pedido y detalle de artículos para vender combinaciones sin registrar pedidos independientes.
3. **Fechas de entrega previstas.** Añadir vencimientos, agenda y avisos de pedidos próximos o atrasados. La fecha de entrega actual representa la entrega registrada.
4. **Filtros y paginación.** Consultar por fecha, estado, modalidad y saldo pendiente; permitir recorrer todo el historial sin depender del límite de 250 registros.
5. **Cuentas y caja.** Separar efectivo, bancos y billeteras, registrar transferencias internas y facilitar cierres y conciliación.
6. **Exportaciones más prácticas.** Ofrecer importes en bolivianos, filtros, historial de pagos y tratamiento de pedidos cancelados que no confunda su total con una deuda vigente.

### Evolución posterior

1. **Inventario y costos.** Registrar entradas, consumos, ajustes y existencias mínimas. Definir la valoración y su relación con el costo unitario antes de modificar el cálculo del resultado.
2. **Reportes de rentabilidad.** Comparar productos, clientes y períodos, y distinguir margen, gastos y flujo de caja.
3. **Comprobantes.** Generar recibos o resúmenes en PDF e impresión. Evaluar por separado los requisitos de una eventual facturación fiscal.
4. **Experiencia de uso.** Mejorar adaptación a pantallas pequeñas, navegación por teclado y mensajes de validación junto a cada campo.
5. **Distribución mantenible.** Fijar versiones de dependencias de compilación, identificar la versión del programa y evaluar instalador y firma del ejecutable.
6. **Acceso compartido.** Si el negocio lo necesita, diseñar usuarios, permisos y una arquitectura de sincronización o servidor. Esto requiere revisar el diseño local actual.

## 7. Criterios para futuros cambios

- Mantener la separación entre venta entregada, cobro y movimiento de caja.
- Conservar importes en centavos y evitar cálculos monetarios con float.
- Preservar el historial y respaldar los datos antes de migraciones o restauraciones.
- Mantener el funcionamiento sin Internet mientras siga siendo un requisito del negocio.
- Validar los cambios financieros con pruebas de casos reales antes de distribuir un nuevo ejecutable.

Como primera etapa conviene implementar restauración, respaldos automáticos, protección de la fecha de entrega y correcciones auditables. Después pueden incorporarse catálogo, clientes, filtros y cuentas separadas.

## 8. Avance de implementación

La primera etapa incorpora eliminación de ventas con motivo, confirmación, respaldo previo y auditoría interna; restauración validada con copia previa; respaldo diario con retención de 30 días de uso; versión inicial del esquema; y protección de la fecha al repetir el estado Entregado.

La eliminación retira también los pagos y devoluciones asociados, modificando caja y reportes. Para devolver dinero realmente debe utilizarse el flujo de devolución. El historial eliminado queda en `audit_log` y puede recuperarse mediante el respaldo completo anterior.

Las propuestas anteriores constituyen el plan original: estos puntos ya están implementados. Siguen pendientes edición auditable de ventas y gastos, ubicación configurable de respaldos, catálogo, clientes, inventario, filtros avanzados y cuentas separadas.


Actualización de consultas: Ventas incorpora la pestaña **Ventas eliminadas**, con ID original, fecha de eliminación, motivo y detalle de los pagos conservados. Estas ventas no afectan los totales activos. Estadísticas muestra pedidos registrados, cobros netos y todos los gastos pagados por separado de las ventas entregadas y añade **Datos por mes**. Los pedidos se agrupan por fecha de registro; las ventas entregadas por entrega; los movimientos de dinero por su fecha.


Comprobantes PDF: en **Ventas → Historial y cobros**, selecciona una venta y pulsa **Comprobante PDF**. Elige dónde guardarlo; abre el archivo para imprimirlo con Ctrl+P. Incluye logo, cliente, producto, cantidad, precio, envío, descuento, pagos, devoluciones y saldo pendiente, con los colores de BLOSSOM. No incluye costos de producción ni notas internas. Es un comprobante de pedido y pagos, no una factura fiscal. Para ejecutar desde código instala primero `py -m pip install -r requirements.txt`; la compilación del ejecutable ya incluye esta dependencia.
