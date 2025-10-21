================================================================================
                    DOCUMENTACIÓN COMPLETA - PROYECTO APP
================================================================================

INFORMACIÓN GENERAL
-------------------
Fecha de generación: 2025-10-20 22:13:32
Ubicación: /app
Python Version: Python 3.11.14
Pip Version: pip 24.0 from /usr/local/lib/python3.11/site-packages/pip (python 3.11)
Entorno Virtual: ❌ NO ACTIVO
Sistema Operativo: Linux
Usuario: Desconocido

================================================================================
                            ESTRUCTURA DEL PROYECTO
================================================================================

├── venv/ (excluido)
├── apps/ (11 elementos)
│   ├── authentication/ (16 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (3 elementos)
│   │   │   │   ├── __init__.py (0B)
│   │   │   │   ├── crear_roles_base.py (2.1KB)
│   │   │   │   └── diagnostico_roles.py (3.6KB)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (4 elementos)
│   │   │   ├── 0001_initial.py (11.7KB)
│   │   │   ├── 0002_rol.py (2.2KB)
│   │   │   ├── 0003_alter_logacceso_tipo_evento_alter_usuario_rol.py (1.8KB)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (9.6KB)
│   │   ├── apps.py (1.2KB)
│   │   ├── decorators.py (14.7KB)
│   │   ├── forms.py (16.4KB)
│   │   ├── middleware.py (4.7KB)
│   │   ├── models.py (12.8KB)
│   │   ├── permissions.py (9.8KB)
│   │   ├── serializers.py (19.5KB)
│   │   ├── signals.py (9.3KB)
│   │   ├── tests.py (63.0B)
│   │   ├── urls.py (5.5KB)
│   │   ├── utils.py (12.2KB)
│   │   └── views.py (39.0KB)
│   ├── custom_admin/ (8 elementos)
│   │   ├── migrations/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (66.0B)
│   │   ├── apps.py (166.0B)
│   │   ├── models.py (60.0B)
│   │   ├── tests.py (63.0B)
│   │   ├── urls.py (12.8KB)
│   │   └── views.py (215.2KB)
│   ├── financial_management/ (15 elementos)
│   │   ├── accounting/ (4 elementos)
│   │   │   ├── __init__.py (404.0B)
│   │   │   ├── accounting_service.py (15.1KB)
│   │   │   ├── cost_calculator.py (15.5KB)
│   │   │   └── entry_generator.py (13.7KB)
│   │   ├── cash_management/ (4 elementos)
│   │   │   ├── __init__.py (352.0B)
│   │   │   ├── cash_calculator.py (12.9KB)
│   │   │   ├── cash_service.py (12.8KB)
│   │   │   └── reconciliation_service.py (14.5KB)
│   │   ├── migrations/ (2 elementos)
│   │   │   ├── 0001_initial.py (23.2KB)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (9.7KB)
│   │   ├── admin.py.backup2 (8.6KB)
│   │   ├── apps.py (467.0B)
│   │   ├── forms.py (15.5KB)
│   │   ├── mixins.py (5.2KB)
│   │   ├── models.py (26.4KB)
│   │   ├── signals.py (13.7KB)
│   │   ├── tests.py (63.0B)
│   │   ├── urls.py (3.1KB)
│   │   ├── views.py (36.1KB)
│   │   └── views.py.backup2 (33.3KB)
│   ├── hardware_integration/ (14 elementos)
│   │   ├── api/ (3 elementos)
│   │   │   ├── __init__.py (676.0B)
│   │   │   ├── agente_views.py (28.9KB)
│   │   │   └── urls.py (740.0B)
│   │   ├── cash_drawer/ (0 elementos)
│   │   ├── migrations/ (3 elementos)
│   │   │   ├── 0001_initial.py (37.4KB)
│   │   │   ├── 0002_trabajoimpresion.py (8.1KB)
│   │   │   └── __init__.py (0B)
│   │   ├── printers/ (4 elementos)
│   │   │   ├── __init__.py (0B)
│   │   │   ├── cash_drawer_service.py (7.0KB)
│   │   │   ├── printer_service.py (34.1KB)
│   │   │   └── ticket_printer.py (8.8KB)
│   │   ├── scales/ (0 elementos)
│   │   ├── scanners/ (0 elementos)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (17.8KB)
│   │   ├── apps.py (182.0B)
│   │   ├── forms.py (14.2KB)
│   │   ├── middleware.py (820.0B)
│   │   ├── models.py (33.9KB)
│   │   ├── tests.py (63.0B)
│   │   └── views.py (27.9KB)
│   ├── inventory_management/ (15 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (4 elementos)
│   │   │   │   ├── __init__.py (0B)
│   │   │   │   ├── generate_barcodes.py (1.6KB)
│   │   │   │   ├── setup_inventory_data.py (3.8KB)
│   │   │   │   └── validate_inventory_integrity.py (3.4KB)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (4 elementos)
│   │   │   ├── 0001_initial.py (39.0KB)
│   │   │   ├── 0002_producto_iva.py (562.0B)
│   │   │   ├── 0003_agregar_marca.py (3.1KB)
│   │   │   └── __init__.py (0B)
│   │   ├── services/ (5 elementos)
│   │   │   ├── __init__.py (329.0B)
│   │   │   ├── barcode_service.py (6.5KB)
│   │   │   ├── inventory_service.py (9.5KB)
│   │   │   ├── stock_service.py (6.2KB)
│   │   │   └── traceability_service.py (6.6KB)
│   │   ├── utils/ (5 elementos)
│   │   │   ├── __init__.py (296.0B)
│   │   │   ├── barcode_generator.py (2.9KB)
│   │   │   ├── fifo_calculator.py (1.9KB)
│   │   │   ├── unit_converter.py (1.4KB)
│   │   │   └── validators.py (1.2KB)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (26.6KB)
│   │   ├── apps.py (182.0B)
│   │   ├── decorators.py (2.3KB)
│   │   ├── forms.py (24.8KB)
│   │   ├── mixins.py (3.9KB)
│   │   ├── models.py (45.6KB)
│   │   ├── signals.py (8.2KB)
│   │   ├── tests.py (63.0B)
│   │   ├── urls.py (8.5KB)
│   │   └── views.py (65.5KB)
│   ├── notifications/ (10 elementos)
│   │   ├── migrations/ (2 elementos)
│   │   │   ├── 0001_initial.py (27.4KB)
│   │   │   └── __init__.py (0B)
│   │   ├── services/ (2 elementos)
│   │   │   ├── __init__.py (0B)
│   │   │   └── notification_service.py (26.0KB)
│   │   ├── __init__.py (100.0B)
│   │   ├── admin.py (17.9KB)
│   │   ├── apps.py (405.0B)
│   │   ├── models.py (25.3KB)
│   │   ├── signals.py (10.6KB)
│   │   ├── tests.py (63.0B)
│   │   ├── url.py (471.0B)
│   │   └── views.py (1.0KB)
│   ├── reports_analytics/ (11 elementos)
│   │   ├── generators/ (6 elementos)
│   │   │   ├── __init__.py (507.0B)
│   │   │   ├── dashboard_data.py (16.6KB)
│   │   │   ├── financial_reports.py (19.4KB)
│   │   │   ├── inventory_reports.py (17.8KB)
│   │   │   ├── sales_reports.py (19.1KB)
│   │   │   └── traceability_reports.py (21.3KB)
│   │   ├── migrations/ (2 elementos)
│   │   │   ├── 0001_initial.py (10.6KB)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (270.0B)
│   │   ├── admin.py (7.5KB)
│   │   ├── apps.py (667.0B)
│   │   ├── forms.py (9.8KB)
│   │   ├── models.py (8.0KB)
│   │   ├── signals.py (9.1KB)
│   │   ├── tests.py (63.0B)
│   │   ├── urls.py (6.0KB)
│   │   └── views.py (31.9KB)
│   ├── sales_management/ (14 elementos)
│   │   ├── invoicing/ (3 elementos)
│   │   │   ├── __init__.py (0B)
│   │   │   ├── invoice_service.py (4.8KB)
│   │   │   └── ticket_generator.py (4.0KB)
│   │   ├── migrations/ (5 elementos)
│   │   │   ├── 0001_initial.py (1.1KB)
│   │   │   ├── 0002_cliente_detalleventa_devolucion_pago_and_more.py (16.8KB)
│   │   │   ├── 0003_alter_venta_numero_venta.py (647.0B)
│   │   │   ├── 0004_alter_devolucion_descripcion.py (505.0B)
│   │   │   └── __init__.py (0B)
│   │   ├── pos/ (3 elementos)
│   │   │   ├── __init__.py (0B)
│   │   │   ├── pos_service.py (24.7KB)
│   │   │   └── pricing_calculator.py (8.4KB)
│   │   ├── __init__.py (110.0B)
│   │   ├── admin.py (19.8KB)
│   │   ├── apps.py (401.0B)
│   │   ├── forms.py (15.7KB)
│   │   ├── models.py (23.2KB)
│   │   ├── quintal_service.py (2.1KB)
│   │   ├── signals.py (3.3KB)
│   │   ├── tasks.py (2.1KB)
│   │   ├── tests.py (63.0B)
│   │   ├── urls.py (3.4KB)
│   │   └── views.py (53.1KB)
│   ├── stock_alert_system/ (12 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (3 elementos)
│   │   │   │   ├── __init__.py (0B)
│   │   │   │   ├── procesar_alertas.py (6.0KB)
│   │   │   │   └── recalcular_stock.py (9.7KB)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (3 elementos)
│   │   │   ├── 0001_initial.py (10.2KB)
│   │   │   ├── 0002_estadostock_historialestado_and_more.py (14.1KB)
│   │   │   └── __init__.py (0B)
│   │   ├── utils/ (0 elementos)
│   │   ├── __init__.py (212.0B)
│   │   ├── admin.py (35.6KB)
│   │   ├── apps.py (633.0B)
│   │   ├── models.py (25.0KB)
│   │   ├── signals.py (7.3KB)
│   │   ├── status_calculator.py (20.3KB)
│   │   ├── tasks.py (19.1KB)
│   │   ├── tests.py (63.0B)
│   │   └── views.py (66.0B)
│   ├── system_configuration/ (11 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (4 elementos)
│   │   │   │   ├── __init__.py (0B)
│   │   │   │   ├── backup_system.py (7.8KB)
│   │   │   │   ├── setup_commercebox.py (27.9KB)
│   │   │   │   └── system_health_check.py (9.1KB)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (2 elementos)
│   │   │   ├── 0001_initial.py (36.4KB)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (23.3KB)
│   │   ├── apps.py (182.0B)
│   │   ├── forms.py (15.0KB)
│   │   ├── models.py (29.9KB)
│   │   ├── signals.py (0B)
│   │   ├── tests.py (63.0B)
│   │   ├── urls.py (2.3KB)
│   │   └── views.py (23.6KB)
│   └── context_processors.py (544.0B)
├── commercebox/ (7 elementos)
│   ├── __pycache__/ (excluido)
│   ├── __init__.py (257.0B)
│   ├── asgi.py (415.0B)
│   ├── celery.py (811.0B)
│   ├── settings.py (18.2KB)
│   ├── urls.py (1.4KB)
│   └── wsgi.py (415.0B)
├── logs/ (3 elementos)
│   ├── commercebox.log (929.7KB)
│   ├── commercebox.log.1 (15.0MB)
│   └── commercebox_audit.log (0B)
├── media/ (6 elementos)
│   ├── barcodes/ (2 elementos)
│   │   ├── productos/ (0 elementos)
│   │   └── quintales/ (0 elementos)
│   ├── empresa/ (1 elementos)
│   │   └── logos/ (1 elementos)
│   │       └── Captura_de_pantalla_2025-10-09_004451.png (131.0KB)
│   ├── invoices/ (0 elementos)
│   ├── productos/ (0 elementos)
│   ├── reports/ (0 elementos)
│   └── uploads/ (0 elementos)
├── scripts/ (2 elementos)
│   ├── init_db.sql/ (0 elementos)
│   └── test_financial_module.py (11.1KB)
├── static/ (4 elementos)
│   ├── css/ (0 elementos)
│   ├── icons/ (0 elementos)
│   ├── js/ (0 elementos)
│   └── vendor/ (0 elementos)
├── staticfiles/ (3 elementos)
│   ├── admin/ (3 elementos)
│   │   ├── css/ (13 elementos)
│   │   │   ├── vendor/ (1 elementos)
│   │   │   │   └── select2/ (3 elementos)
│   │   │   │       ├── LICENSE-SELECT2.md (1.1KB)
│   │   │   │       ├── select2.css (17.0KB)
│   │   │   │       └── select2.min.css (14.6KB)
│   │   │   ├── autocomplete.css (8.9KB)
│   │   │   ├── base.css (20.7KB)
│   │   │   ├── changelists.css (6.4KB)
│   │   │   ├── dark_mode.css (2.9KB)
│   │   │   ├── dashboard.css (441.0B)
│   │   │   ├── forms.css (8.8KB)
│   │   │   ├── login.css (958.0B)
│   │   │   ├── nav_sidebar.css (2.6KB)
│   │   │   ├── responsive.css (18.1KB)
│   │   │   ├── responsive_rtl.css (1.7KB)
│   │   │   ├── rtl.css (4.7KB)
│   │   │   └── widgets.css (11.6KB)
│   │   ├── img/ (21 elementos)
│   │   │   ├── gis/ (2 elementos)
│   │   │   │   ├── move_vertex_off.svg (1.1KB)
│   │   │   │   └── move_vertex_on.svg (1.1KB)
│   │   │   ├── calendar-icons.svg (1.1KB)
│   │   │   ├── icon-addlink.svg (331.0B)
│   │   │   ├── icon-alert.svg (504.0B)
│   │   │   ├── icon-calendar.svg (1.1KB)
│   │   │   ├── icon-changelink.svg (380.0B)
│   │   │   ├── icon-clock.svg (677.0B)
│   │   │   ├── icon-deletelink.svg (392.0B)
│   │   │   ├── icon-no.svg (560.0B)
│   │   │   ├── icon-unknown-alt.svg (655.0B)
│   │   │   ├── icon-unknown.svg (655.0B)
│   │   │   ├── icon-viewlink.svg (581.0B)
│   │   │   ├── icon-yes.svg (436.0B)
│   │   │   ├── inline-delete.svg (560.0B)
│   │   │   ├── LICENSE (1.1KB)
│   │   │   ├── README.txt (319.0B)
│   │   │   ├── search.svg (458.0B)
│   │   │   ├── selector-icons.svg (3.2KB)
│   │   │   ├── sorting-icons.svg (1.1KB)
│   │   │   ├── tooltag-add.svg (331.0B)
│   │   │   └── tooltag-arrowright.svg (280.0B)
│   │   └── js/ (20 elementos)
│   │       ├── admin/ (2 elementos)
│   │       │   ├── DateTimeShortcuts.js (18.9KB)
│   │       │   └── RelatedObjectLookups.js (8.7KB)
│   │       ├── vendor/ (3 elementos)
│   │       │   ├── jquery/ (3 elementos)
│   │       │   │   ├── jquery.js (285.6KB)
│   │       │   │   ├── jquery.min.js (87.7KB)
│   │       │   │   └── LICENSE.txt (1.1KB)
│   │       │   ├── select2/ (4 elementos)
│   │       │   │   ├── i18n/ (59 elementos)
│   │       │   │   │   ├── af.js (866.0B)
│   │       │   │   │   ├── ar.js (905.0B)
│   │       │   │   │   ├── az.js (721.0B)
│   │       │   │   │   ├── bg.js (968.0B)
│   │       │   │   │   ├── bn.js (1.3KB)
│   │       │   │   │   ├── bs.js (965.0B)
│   │       │   │   │   ├── ca.js (900.0B)
│   │       │   │   │   ├── cs.js (1.3KB)
│   │       │   │   │   ├── da.js (828.0B)
│   │       │   │   │   ├── de.js (866.0B)
│   │       │   │   │   ├── dsb.js (1017.0B)
│   │       │   │   │   ├── el.js (1.2KB)
│   │       │   │   │   ├── en.js (844.0B)
│   │       │   │   │   ├── es.js (922.0B)
│   │       │   │   │   ├── et.js (801.0B)
│   │       │   │   │   ├── eu.js (868.0B)
│   │       │   │   │   ├── fa.js (1023.0B)
│   │       │   │   │   ├── fi.js (803.0B)
│   │       │   │   │   ├── fr.js (924.0B)
│   │       │   │   │   ├── gl.js (924.0B)
│   │       │   │   │   ├── he.js (984.0B)
│   │       │   │   │   ├── hi.js (1.1KB)
│   │       │   │   │   ├── hr.js (852.0B)
│   │       │   │   │   ├── hsb.js (1018.0B)
│   │       │   │   │   ├── hu.js (831.0B)
│   │       │   │   │   ├── hy.js (1.0KB)
│   │       │   │   │   ├── id.js (768.0B)
│   │       │   │   │   ├── is.js (807.0B)
│   │       │   │   │   ├── it.js (897.0B)
│   │       │   │   │   ├── ja.js (862.0B)
│   │       │   │   │   ├── ka.js (1.2KB)
│   │       │   │   │   ├── km.js (1.1KB)
│   │       │   │   │   ├── ko.js (855.0B)
│   │       │   │   │   ├── lt.js (944.0B)
│   │       │   │   │   ├── lv.js (900.0B)
│   │       │   │   │   ├── mk.js (1.0KB)
│   │       │   │   │   ├── ms.js (811.0B)
│   │       │   │   │   ├── nb.js (778.0B)
│   │       │   │   │   ├── ne.js (1.3KB)
│   │       │   │   │   ├── nl.js (904.0B)
│   │       │   │   │   ├── pl.js (947.0B)
│   │       │   │   │   ├── ps.js (1.0KB)
│   │       │   │   │   ├── pt-BR.js (876.0B)
│   │       │   │   │   ├── pt.js (878.0B)
│   │       │   │   │   ├── ro.js (938.0B)
│   │       │   │   │   ├── ru.js (1.1KB)
│   │       │   │   │   ├── sk.js (1.3KB)
│   │       │   │   │   ├── sl.js (925.0B)
│   │       │   │   │   ├── sq.js (903.0B)
│   │       │   │   │   ├── sr-Cyrl.js (1.1KB)
│   │       │   │   │   ├── sr.js (980.0B)
│   │       │   │   │   ├── sv.js (786.0B)
│   │       │   │   │   ├── th.js (1.0KB)
│   │       │   │   │   ├── tk.js (771.0B)
│   │       │   │   │   ├── tr.js (775.0B)
│   │       │   │   │   ├── uk.js (1.1KB)
│   │       │   │   │   ├── vi.js (796.0B)
│   │       │   │   │   ├── zh-CN.js (768.0B)
│   │       │   │   │   └── zh-TW.js (707.0B)
│   │       │   │   ├── LICENSE.md (1.1KB)
│   │       │   │   ├── select2.full.js (169.5KB)
│   │       │   │   └── select2.full.min.js (77.4KB)
│   │       │   └── xregexp/ (3 elementos)
│   │       │       ├── LICENSE.txt (1.1KB)
│   │       │       ├── xregexp.js (226.9KB)
│   │       │       └── xregexp.min.js (122.3KB)
│   │       ├── actions.js (7.7KB)
│   │       ├── autocomplete.js (1.0KB)
│   │       ├── calendar.js (8.3KB)
│   │       ├── cancel.js (884.0B)
│   │       ├── change_form.js (606.0B)
│   │       ├── collapse.js (1.8KB)
│   │       ├── core.js (5.5KB)
│   │       ├── filters.js (978.0B)
│   │       ├── inlines.js (15.2KB)
│   │       ├── jquery.init.js (347.0B)
│   │       ├── nav_sidebar.js (3.0KB)
│   │       ├── popup_response.js (551.0B)
│   │       ├── prepopulate.js (1.5KB)
│   │       ├── prepopulate_init.js (586.0B)
│   │       ├── SelectBox.js (4.4KB)
│   │       ├── SelectFilter2.js (14.9KB)
│   │       ├── theme.js (1.9KB)
│   │       └── urlify.js (7.7KB)
│   ├── django_extensions/ (3 elementos)
│   │   ├── css/ (1 elementos)
│   │   │   └── jquery.autocomplete.css (740.0B)
│   │   ├── img/ (1 elementos)
│   │   │   └── indicator.gif (1.5KB)
│   │   └── js/ (3 elementos)
│   │       ├── jquery.ajaxQueue.js (2.7KB)
│   │       ├── jquery.autocomplete.js (35.8KB)
│   │       └── jquery.bgiframe.js (1.8KB)
│   └── rest_framework/ (5 elementos)
│       ├── css/ (8 elementos)
│       │   ├── bootstrap-theme.min.css (22.9KB)
│       │   ├── bootstrap-theme.min.css.map (73.8KB)
│       │   ├── bootstrap-tweaks.css (3.3KB)
│       │   ├── bootstrap.min.css (118.6KB)
│       │   ├── bootstrap.min.css.map (527.8KB)
│       │   ├── default.css (1.1KB)
│       │   ├── font-awesome-4.0.3.css (21.2KB)
│       │   └── prettify.css (817.0B)
│       ├── docs/ (3 elementos)
│       │   ├── css/ (3 elementos)
│       │   │   ├── base.css (6.0KB)
│       │   │   ├── highlight.css (1.6KB)
│       │   │   └── jquery.json-view.min.css (1.3KB)
│       │   ├── img/ (2 elementos)
│       │   │   ├── favicon.ico (5.3KB)
│       │   │   └── grid.png (1.4KB)
│       │   └── js/ (3 elementos)
│       │       ├── api.js (10.1KB)
│       │       ├── highlight.pack.js (293.7KB)
│       │       └── jquery.json-view.min.js (2.6KB)
│       ├── fonts/ (9 elementos)
│       │   ├── fontawesome-webfont.eot (37.3KB)
│       │   ├── fontawesome-webfont.svg (197.4KB)
│       │   ├── fontawesome-webfont.ttf (78.8KB)
│       │   ├── fontawesome-webfont.woff (43.4KB)
│       │   ├── glyphicons-halflings-regular.eot (19.7KB)
│       │   ├── glyphicons-halflings-regular.svg (106.2KB)
│       │   ├── glyphicons-halflings-regular.ttf (44.3KB)
│       │   ├── glyphicons-halflings-regular.woff (22.9KB)
│       │   └── glyphicons-halflings-regular.woff2 (17.6KB)
│       ├── img/ (3 elementos)
│       │   ├── glyphicons-halflings-white.png (8.6KB)
│       │   ├── glyphicons-halflings.png (12.5KB)
│       │   └── grid.png (1.4KB)
│       └── js/ (7 elementos)
│           ├── ajax-form.js (3.5KB)
│           ├── bootstrap.min.js (38.8KB)
│           ├── coreapi-0.1.1.js (153.9KB)
│           ├── csrf.js (1.7KB)
│           ├── default.js (1.2KB)
│           ├── jquery-3.5.1.min.js (87.4KB)
│           └── prettify-min.js (13.3KB)
├── templates/ (9 elementos)
│   ├── authentication/ (1 elementos)
│   │   └── login.html (22.4KB)
│   ├── custom_admin/ (9 elementos)
│   │   ├── finanzas/ (4 elementos)
│   │   │   ├── arqueos_list.html (17.4KB)
│   │   │   ├── cajas_list.html (30.6KB)
│   │   │   ├── cajas_list.html.new (5.1KB)
│   │   │   └── movimientos.html (1.4KB)
│   │   ├── inventario/ (6 elementos)
│   │   │   ├── categorias_list.html (51.3KB)
│   │   │   ├── entrada_inventario.html (92.4KB)
│   │   │   ├── marcas_list.html (53.0KB)
│   │   │   ├── movimientos_list.html (42.9KB)
│   │   │   ├── productos_list.html (79.8KB)
│   │   │   └── proveedores_list.html (42.9KB)
│   │   ├── pos/ (1 elementos)
│   │   │   └── punto_venta.html (77.5KB)
│   │   ├── roles/ (1 elementos)
│   │   │   └── list.html (54.0KB)
│   │   ├── sesiones/ (1 elementos)
│   │   │   └── activas.html (35.9KB)
│   │   ├── usuarios/ (1 elementos)
│   │   │   └── usuarios.html (66.6KB)
│   │   ├── ventas/ (3 elementos)
│   │   │   ├── clientes_list.html (22.0KB)
│   │   │   ├── devoluciones_list.html (38.0KB)
│   │   │   └── list.html (52.0KB)
│   │   ├── base_admin.html (37.4KB)
│   │   └── dashboard.html (28.9KB)
│   ├── financial/ (0 elementos)
│   ├── inventory/ (0 elementos)
│   ├── reports/ (0 elementos)
│   ├── sales/ (0 elementos)
│   ├── stock_alerts/ (0 elementos)
│   ├── base.html (23.9KB)
│   └── base_login.html (6.1KB)
├── tests/ (0 elementos)
├── utils/ (0 elementos)
├── .env (546.0B)
├── .gitignore (2.0KB)
├── celerybeat-schedule (24.0KB)
├── create_structure.ps1 (2.8KB)
├── docker-compose.yml (3.6KB)
├── dockerfile (1.3KB)
├── docmenter.md (23.1KB)
├── DOCUMENTACION_COMPLETA.md (24.7KB)
├── documenter.py (36.0KB)
├── entrypoint.sh (8.9KB)
├── env.example (1.0KB)
├── index.html (18.9KB)
├── manage.py (689.0B)
├── README.md (9.9KB)
├── requirements.txt (2.4KB)
└── test_endpint.py (7.7KB)

================================================================================
                            ANÁLISIS DE ARCHIVOS
================================================================================

ARCHIVOS IMPORTANTES
--------------------
manage.py                 ✅ Existe (689.0B)
requirements.txt          ✅ Existe (2.4KB)
.env                      ✅ Existe (546.0B)
.env.example              ❌ Faltante
.gitignore                ✅ Existe (2.0KB)
README.md                 ✅ Existe (9.9KB)
docker-compose.yml        ✅ Existe (3.6KB)
Dockerfile                ✅ Existe (1.3KB)
pytest.ini                ❌ Faltante
setup.cfg                 ❌ Faltante

ESTADÍSTICAS POR EXTENSIÓN
--------------------------
.py                   192 archivos ( 48.2%)
.js                    98 archivos ( 24.6%)
.css                   24 archivos (  6.0%)
.svg                   22 archivos (  5.5%)
.html                  22 archivos (  5.5%)
.png                    5 archivos (  1.3%)
.md                     5 archivos (  1.3%)
(sin extensión)         5 archivos (  1.3%)
.txt                    4 archivos (  1.0%)
.backup2                2 archivos (  0.5%)

TOTALES
-------
Total de archivos: 398
Total de directorios: 106

================================================================================
                           APLICACIONES DJANGO
================================================================================

ESTADO DE LAS APPS
--------------------------------------------------------------------------------
App                  Estado     Básicos    Total      Archivos Existentes      
--------------------------------------------------------------------------------
authentication       Completa   5/5      18         models.py, views.py, urls.py...
custom_admin         Completa   5/5      6          models.py, views.py, urls.py...
financial_management Completa   5/5      16         models.py, views.py, urls.py...
hardware_integration Parcial    4/5      14         models.py, views.py, admin.py...
inventory_management Completa   5/5      24         models.py, views.py, urls.py...
notifications        Parcial    4/5      9          models.py, views.py, admin.py...
reports_analytics    Completa   5/5      14         models.py, views.py, urls.py...
sales_management     Completa   5/5      18         models.py, views.py, urls.py...
stock_alert_system   Parcial    4/5      12         models.py, views.py, admin.py...
system_configuration Completa   5/5      12         models.py, views.py, urls.py...

DETALLE POR APP
==================================================

📦 App: authentication
   Ubicación: apps/authentication/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, forms.py, serializers.py, tests.py, signals.py
   ✅ Todos los archivos básicos presentes

📦 App: custom_admin
   Ubicación: apps/custom_admin/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, tests.py
   ✅ Todos los archivos básicos presentes

📦 App: financial_management
   Ubicación: apps/financial_management/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, forms.py, tests.py, signals.py
   ✅ Todos los archivos básicos presentes

📦 App: hardware_integration
   Ubicación: apps/hardware_integration/
   Estado: Parcial
   Archivos básicos: 4/5
   Archivos encontrados: models.py, views.py, admin.py, apps.py, forms.py, tests.py
   ❌ Archivos faltantes: urls.py

📦 App: inventory_management
   Ubicación: apps/inventory_management/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, forms.py, tests.py, signals.py
   ✅ Todos los archivos básicos presentes

📦 App: notifications
   Ubicación: apps/notifications/
   Estado: Parcial
   Archivos básicos: 4/5
   Archivos encontrados: models.py, views.py, admin.py, apps.py, tests.py, signals.py
   ❌ Archivos faltantes: urls.py

📦 App: reports_analytics
   Ubicación: apps/reports_analytics/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, forms.py, tests.py, signals.py
   ✅ Todos los archivos básicos presentes

📦 App: sales_management
   Ubicación: apps/sales_management/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, forms.py, tests.py, signals.py
   ✅ Todos los archivos básicos presentes

📦 App: stock_alert_system
   Ubicación: apps/stock_alert_system/
   Estado: Parcial
   Archivos básicos: 4/5
   Archivos encontrados: models.py, views.py, admin.py, apps.py, tests.py, signals.py
   ❌ Archivos faltantes: urls.py

📦 App: system_configuration
   Ubicación: apps/system_configuration/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, forms.py, tests.py
   ✅ Todos los archivos básicos presentes

================================================================================
                         CONFIGURACIÓN DJANGO
================================================================================

✅ ARCHIVO settings.py ENCONTRADO
----------------------------------------
INSTALLED_APPS       ❌ Faltante      Apps instaladas
DATABASES            ✅ Configurado   Configuración de BD
REST_FRAMEWORK       ✅ Configurado   API REST Framework
STATIC_URL           ✅ Configurado   Archivos estáticos
DEBUG                ✅ Configurado   Modo debug
SECRET_KEY           ✅ Configurado   Clave secreta

================================================================================
                         PAQUETES PYTHON
================================================================================

PAQUETES REQUERIDOS PARA SRI
----------------------------
Django                    ❌ Faltante      No instalado    (Req: 4.2.7)
djangorestframework       ❌ Faltante      No instalado    (Req: 3.14.0)
psycopg2-binary           ❌ Faltante      No instalado    (Req: 2.9.7)
python-decouple           ❌ Faltante      No instalado    (Req: 3.8)
celery                    ❌ Faltante      No instalado    (Req: 5.3.4)
redis                     ❌ Faltante      No instalado    (Req: 5.0.1)
cryptography              ❌ Faltante      No instalado    (Req: 41.0.7)
lxml                      ❌ Faltante      No instalado    (Req: 4.9.3)
zeep                      ❌ Faltante      No instalado    (Req: 4.2.1)
reportlab                 ❌ Faltante      No instalado    (Req: 4.0.7)
Pillow                    ❌ Faltante      No instalado    (Req: 10.1.0)
drf-spectacular           ❌ Faltante      No instalado    (Req: 0.26.5)
django-cors-headers       ❌ Faltante      No instalado    (Req: 4.3.1)


TODOS LOS PAQUETES INSTALADOS
-----------------------------

================================================================================
                    ESTRUCTURA DE ALMACENAMIENTO SEGURO
================================================================================

DIRECTORIOS DE STORAGE
----------------------
storage/certificates/encrypted/     ❌ Certificados .p12 encriptados 
storage/certificates/temp/          ❌ Temporal para procesamiento 
storage/invoices/xml/               ❌ Facturas XML firmadas 
storage/invoices/pdf/               ❌ Facturas PDF generadas 
storage/invoices/sent/              ❌ Facturas enviadas al SRI 
storage/logs/                       ❌ Logs del sistema 
storage/backups/                    ❌ Respaldos de BD 
media/                              ✅ Archivos de media (10 archivos)
static/                             ✅ Archivos estáticos (4 archivos)
uploads/                            ❌ Archivos subidos 

================================================================================
                         ANÁLISIS Y PRÓXIMOS PASOS
================================================================================

APPS DJANGO SIN CONFIGURAR
------------------------------
❌ hardware_integration - Parcial
❌ notifications - Parcial
❌ stock_alert_system - Parcial

TAREAS PRIORITARIAS
===================

1. COMPLETAR APPS DJANGO
   Crear archivos faltantes en:
   - hardware_integration: urls.py
   - notifications: urls.py
   - stock_alert_system: urls.py

COMANDOS ÚTILES
===============
# Instalar dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Ejecutar servidor
python manage.py runserver

================================================================================
                                MÉTRICAS FINALES
================================================================================

PROGRESO DEL PROYECTO
---------------------
Estructura básica:       ✅ Completada (100%)
Configuración Django:    ⚠️  Parcial (80%)
Apps implementadas:      ❌ Pendiente (70%)
Documentación:           ⚠️  Iniciada (60%)

ESTADÍSTICAS GENERALES
---------------------
Total directorios:       106
Total archivos:          398
Apps Django:             10
Archivos Python:         192
Paquetes instalados:     0

================================================================================
Reporte generado automáticamente el 2025-10-20 22:13:32
Para actualizar, ejecuta: python documenter.py
================================================================================