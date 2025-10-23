# apps/hardware_integration/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.urls import path, reverse
from django.shortcuts import redirect
from django.http import HttpResponse
from django.utils import timezone

from .models import (
    Impresora, PlantillaImpresion, ConfiguracionCodigoBarras,
    GavetaDinero, RegistroImpresion, EscanerCodigoBarras
)
from .printers.printer_service import PrinterService
from .printers.cash_drawer_service import CashDrawerService


# ========================
# INLINES
# ========================

class GavetaDineroInline(admin.TabularInline):
    model = GavetaDinero
    extra = 0
    fields = ('nombre', 'ubicacion', 'activa', 'estado')
    readonly_fields = ('estado',)


class PlantillaImpresionInline(admin.TabularInline):
    model = PlantillaImpresion
    extra = 0
    fields = ('nombre', 'tipo_documento', 'activa', 'es_predeterminada')
    readonly_fields = ('es_predeterminada',)


# ========================
# ACCIONES PERSONALIZADAS
# ========================

def test_conexion_impresoras(modeladmin, request, queryset):
    """Probar conexión de impresoras seleccionadas"""
    success_count = 0
    for impresora in queryset:
        try:
            success, msg = PrinterService.test_connection(impresora)
            if success:
                impresora.estado = 'ACTIVA'
                success_count += 1
            else:
                impresora.estado = 'ERROR'
            impresora.save(update_fields=['estado'])
        except Exception as e:
            impresora.estado = 'ERROR'
            impresora.save(update_fields=['estado'])
            modeladmin.message_user(request, f"Error en {impresora.nombre}: {str(e)}", messages.ERROR)
    if success_count > 0:
        modeladmin.message_user(request, f"✅ {success_count} impresoras conectadas exitosamente.", messages.SUCCESS)
test_conexion_impresoras.short_description = "🔍 Probar conexión seleccionadas"


def reiniciar_contador_impresoras(modeladmin, request, queryset):
    """Reiniciar contador de impresiones"""
    for impresora in queryset:
        impresora.contador_impresiones = 0
        impresora.fecha_ultimo_mantenimiento = timezone.now()
        impresora.save(update_fields=['contador_impresiones', 'fecha_ultimo_mantenimiento'])
    modeladmin.message_user(request, "🔄 Contadores reiniciados.", messages.INFO)
reiniciar_contador_impresoras.short_description = "🔄 Reiniciar contador de impresiones"


def abrir_gavetas_seleccionadas(modeladmin, request, queryset):
    """Abrir gavetas seleccionadas"""
    success_count = 0
    for gaveta in queryset:
        if CashDrawerService.abrir_gaveta(gaveta, request.user):
            success_count += 1
    if success_count > 0:
        modeladmin.message_user(request, f"🔓 {success_count} gavetas abiertas.", messages.SUCCESS)
    else:
        modeladmin.message_user(request, "❌ No se pudo abrir ninguna gaveta.", messages.ERROR)
abrir_gavetas_seleccionadas.short_description = "🔓 Abrir gavetas seleccionadas"


# ========================
# ADMIN CLASSES
# ========================

@admin.register(Impresora)
class ImpresoraAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'marca', 'modelo', 'tipo_impresora_display',
        'estado_badge', 'ubicacion', 'contador_impresiones', 'ultima_prueba'
    ]
    list_filter = [
        'tipo_impresora', 'estado', 'ubicacion', 'marca',
        'es_principal_tickets', 'es_principal_facturas', 'es_principal_etiquetas'
    ]
    search_fields = ['nombre', 'codigo', 'marca', 'modelo', 'numero_serie']
    readonly_fields = [
        'id', 'codigo', 'fecha_instalacion', 'fecha_ultima_prueba',
        'fecha_ultimo_mantenimiento', 'contador_impresiones',
        'botones_prueba_impresora'
    ]
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo', 'nombre', 'marca', 'modelo', 'numero_serie'),
            'description': '📌 El código se genera automáticamente si se deja vacío'
        }),
        ('Tipo y Conexión', {
            'fields': ('tipo_impresora', 'tipo_conexion', 'protocolo')
        }),
        ('Configuración de Conexión', {
            'fields': (
                ('direccion_ip', 'puerto_red', 'mac_address'),
                ('puerto_usb', 'vid_usb', 'pid_usb'),
                ('puerto_serial', 'baudrate'),
                'nombre_driver'
            )
        }),
        ('Papel y Etiquetas', {
            'fields': (
                ('ancho_papel', 'largo_maximo'),
                ('ancho_etiqueta', 'alto_etiqueta', 'gap_etiquetas')
            )
        }),
        ('Capacidades', {
            'fields': (
                'soporta_corte_automatico', 'soporta_corte_parcial',
                'soporta_codigo_barras', 'soporta_qr', 'soporta_imagenes'
            )
        }),
        ('Gaveta de Dinero', {
            'fields': ('tiene_gaveta', 'pin_gaveta')
        }),
        ('Estado y Ubicación', {
            'fields': ('estado', 'ubicacion', 'notas')
        }),
        ('Uso Predeterminado', {
            'fields': (
                'es_principal_tickets',
                'es_principal_facturas',
                'es_principal_etiquetas'
            )
        }),
        ('Prueba de Impresora', {
            'fields': ('botones_prueba_impresora',),
            'description': '🔧 Herramientas para probar la configuración e impresión'
        }),
        ('Auditoría', {
            'fields': (
                'fecha_instalacion', 'fecha_ultima_prueba',
                'fecha_ultimo_mantenimiento', 'contador_impresiones'
            )
        }),
        ('Configuración Avanzada', {
            'fields': ('configuracion_extra',),
            'classes': ('collapse',)
        }),
    )
    inlines = [GavetaDineroInline, PlantillaImpresionInline]
    actions = [test_conexion_impresoras, reiniciar_contador_impresoras]

    def save_model(self, request, obj, form, change):
        """
        Genera automáticamente el código si está vacío
        """
        # Si el código está vacío o solo contiene espacios, generar uno nuevo
        if not obj.codigo or obj.codigo.strip() == '':
            # Buscar el último código generado
            ultimo = Impresora.objects.filter(
                codigo__startswith='IMP-'
            ).order_by('-codigo').first()
            
            if ultimo and ultimo.codigo:
                try:
                    # Extraer el número del último código (IMP-001 -> 001)
                    numero = int(ultimo.codigo.split('-')[1]) + 1
                except (IndexError, ValueError):
                    # Si hay error al parsear, empezar desde 1
                    numero = 1
            else:
                # No hay códigos previos, empezar desde 1
                numero = 1
            
            # Generar el nuevo código con formato IMP-XXX
            obj.codigo = f'IMP-{numero:03d}'
            
            # Mensaje informativo
            messages.info(
                request,
                f"✅ Código generado automáticamente: {obj.codigo}"
            )
        
        # Guardar el objeto
        super().save_model(request, obj, form, change)

    def tipo_impresora_display(self, obj):
        return obj.get_tipo_impresora_display()
    tipo_impresora_display.short_description = 'Tipo'

    def estado_badge(self, obj):
        badges = {
            'ACTIVA': '<span style="color: green;">🟢 Activa</span>',
            'INACTIVA': '<span style="color: orange;">🟡 Inactiva</span>',
            'ERROR': '<span style="color: red;">🔴 Error</span>',
            'MANTENIMIENTO': '<span style="color: blue;">🔧 Mantenimiento</span>',
        }
        return format_html(badges.get(obj.estado, obj.estado))
    estado_badge.short_description = 'Estado'

    def ultima_prueba(self, obj):
        return obj.fecha_ultima_prueba.strftime('%d/%m/%Y %H:%M') if obj.fecha_ultima_prueba else '-'
    ultima_prueba.short_description = 'Última Prueba'
    
    def botones_prueba_impresora(self, obj):
        """Muestra botones para probar la impresora"""
        if not obj.pk:
            return "Guarda la impresora primero para poder probarla."
        
        url_test = reverse('admin:probar_impresora', args=[obj.pk])
        url_print_direct = reverse('admin:imprimir_prueba_directa', args=[obj.pk])
        url_comandos = reverse('admin:obtener_comandos_raw', args=[obj.pk])
        url_codigos_barras = reverse('admin:imprimir_prueba_codigos_barras', args=[obj.pk])
        
        # Determinar si es una impresora de etiquetas/códigos de barras
        es_impresora_etiquetas = obj.tipo_impresora == 'ETIQUETAS'
        
        # Construir botones según el tipo
        botones = []
        
        # Botón 1: Probar configuración (siempre visible)
        botones.append(format_html(
            '<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">'
            '<a class="button" href="{}" style="padding: 10px 15px; '
            'background-color: #417690; color: white; text-decoration: none; '
            'border-radius: 4px; display: inline-block; white-space: nowrap;">'
            '🔍 Probar Configuración</a>'
            '<span style="font-size: 11px; color: #666;">Valida la configuración sin imprimir</span>'
            '</div>',
            url_test
        ))
        
        # Botón 2: Imprimir directo (solo para impresoras térmicas)
        if not es_impresora_etiquetas:
            botones.append(format_html(
                '<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">'
                '<a class="button" href="{}" style="padding: 10px 15px; '
                'background-color: #28a745; color: white; text-decoration: none; '
                'border-radius: 4px; display: inline-block; white-space: nowrap;">'
                '⚡ Imprimir Ticket Prueba</a>'
                '<span style="font-size: 11px; color: #666;">Imprime ticket y abre gaveta</span>'
                '</div>',
                url_print_direct
            ))
        
        # Botón 3: Códigos de barras (solo para impresoras de etiquetas)
        if es_impresora_etiquetas:
            botones.append(format_html(
                '<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">'
                '<a class="button" href="{}" style="padding: 10px 15px; '
                'background-color: #ff9800; color: white; text-decoration: none; '
                'border-radius: 4px; display: inline-block; white-space: nowrap;">'
                '🏷️ Imprimir Códigos Barras</a>'
                '<span style="font-size: 11px; color: #666;">Imprime etiqueta con varios códigos</span>'
                '</div>',
                url_codigos_barras
            ))
        
        # Botón 4: Comandos ESC/POS (siempre visible)
        botones.append(format_html(
            '<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">'
            '<a class="button" href="{}" target="_blank" style="padding: 10px 15px; '
            'background-color: #6c757d; color: white; text-decoration: none; '
            'border-radius: 4px; display: inline-block; white-space: nowrap;">'
            '📋 Comandos ESC/POS</a>'
            '<span style="font-size: 11px; color: #666;">Para usar con agente local</span>'
            '</div>',
            url_comandos
        ))
        
        # Unir todos los botones
        from django.utils.safestring import mark_safe
        return mark_safe(''.join(str(b) for b in botones))
    
    botones_prueba_impresora.short_description = "Herramientas de Prueba"
    
    def get_urls(self):
        """Agrega URLs personalizadas"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:impresora_id>/probar/',
                self.admin_site.admin_view(self.probar_impresora_view),
                name='probar_impresora',
            ),
            path(
                '<uuid:impresora_id>/imprimir-directa/',
                self.admin_site.admin_view(self.imprimir_prueba_directa_view),
                name='imprimir_prueba_directa',
            ),
            path(
                '<uuid:impresora_id>/comandos-raw/',
                self.admin_site.admin_view(self.obtener_comandos_raw_view),
                name='obtener_comandos_raw',
            ),
            path(
                '<uuid:impresora_id>/prueba-codigos-barras/',
                self.admin_site.admin_view(self.imprimir_prueba_codigos_barras_view),
                name='imprimir_prueba_codigos_barras',
            ),
        ]
        return custom_urls + urls
    
    def probar_impresora_view(self, request, impresora_id):
        """Vista para probar configuración (sin imprimir)"""
        try:
            impresora = Impresora.objects.get(pk=impresora_id)
            
            # Probar la configuración
            success, msg = PrinterService.test_connection(impresora)
            
            # Actualizar estado
            if success:
                impresora.estado = 'ACTIVA'
                impresora.fecha_ultima_prueba = timezone.now()
                impresora.save(update_fields=['estado', 'fecha_ultima_prueba'])
                
                self.message_user(request, msg, messages.SUCCESS)
            else:
                impresora.estado = 'ERROR'
                impresora.save(update_fields=['estado'])
                
                self.message_user(request, msg, messages.ERROR)
                
        except Impresora.DoesNotExist:
            self.message_user(request, "❌ Impresora no encontrada.", messages.ERROR)
        except Exception as e:
            self.message_user(request, f"❌ Error: {str(e)}", messages.ERROR)
        
        return redirect('admin:hardware_integration_impresora_change', impresora_id)
    
    def imprimir_prueba_directa_view(self, request, impresora_id):
        """Vista para imprimir directamente y abrir gaveta"""
        try:
            impresora = Impresora.objects.get(pk=impresora_id)
            
            # Intentar imprimir directamente
            if PrinterService.print_test_page(impresora):
                self.message_user(
                    request,
                    "✅ ¡Página de prueba enviada y gaveta abierta!",
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request,
                    "⚠️ No se pudo imprimir directamente. "
                    "Configure el agente local o use impresora de red.",
                    messages.WARNING
                )
                
        except Impresora.DoesNotExist:
            self.message_user(request, "❌ Impresora no encontrada.", messages.ERROR)
        except Exception as e:
            self.message_user(request, f"❌ Error: {str(e)}", messages.ERROR)
        
        return redirect('admin:hardware_integration_impresora_change', impresora_id)
    
    def obtener_comandos_raw_view(self, request, impresora_id):
        """Devuelve los comandos ESC/POS raw en formato hexadecimal"""
        try:
            impresora = Impresora.objects.get(pk=impresora_id)
            
            # Generar comandos raw
            comandos = PrinterService.generar_comando_raw_test(impresora)
            
            # Convertir a hexadecimal legible
            hex_string = ' '.join(f'{b:02x}' for b in comandos)
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Comandos ESC/POS - {impresora.nombre}</title>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .commands {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 12px;
            line-height: 1.6;
            word-break: break-all;
        }}
        .button {{
            background: #28a745;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        .button:hover {{
            background: #218838;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>📋 Comandos ESC/POS para: {impresora.nombre}</h2>
        <p><strong>Uso:</strong> Copia estos comandos y envíalos desde el agente local de Windows</p>
        <p><strong>Formato:</strong> Hexadecimal (listo para enviar a la impresora)</p>
    </div>
    
    <h3>Comandos en Hexadecimal:</h3>
    <div class="commands" id="commands">{hex_string}</div>
    
    <br>
    <button class="button" onclick="copyToClipboard()">📋 Copiar al Portapapeles</button>
    
    <script>
        function copyToClipboard() {{
            const text = document.getElementById('commands').innerText;
            navigator.clipboard.writeText(text).then(() => {{
                alert('✅ Comandos copiados al portapapeles');
            }});
        }}
    </script>
</body>
</html>
            """
            
            return HttpResponse(html)
                
        except Impresora.DoesNotExist:
            return HttpResponse("❌ Impresora no encontrada", status=404)
        except Exception as e:
            return HttpResponse(f"❌ Error: {str(e)}", status=500)
    
    def imprimir_prueba_codigos_barras_view(self, request, impresora_id):
        """Vista para imprimir prueba de códigos de barras con impresión directa"""
        try:
            impresora = Impresora.objects.get(pk=impresora_id)
            
            # Verificar que sea una impresora de etiquetas
            if impresora.tipo_impresora != 'ETIQUETAS':
                self.message_user(
                    request,
                    "⚠️ Esta función es solo para impresoras de etiquetas/códigos de barras.",
                    messages.WARNING
                )
                return redirect('admin:hardware_integration_impresora_change', impresora_id)
            
            # Generar página de prueba con códigos de barras
            comandos = PrinterService.generar_pagina_prueba_codigos()
            
            if not comandos:
                self.message_user(
                    request,
                    "❌ No se pudieron generar los comandos de códigos de barras.",
                    messages.ERROR
                )
                return redirect('admin:hardware_integration_impresora_change', impresora_id)
            
            # 🔥 PRIMERO: INTENTAR IMPRESIÓN DIRECTA
            impreso_directo = False
            metodo_usado = ""
            
            # Intentar con Windows (si está disponible)
            import platform
            if platform.system() == 'Windows' and impresora.nombre_driver:
                try:
                    import win32print
                    
                    # Abrir impresora
                    handle = win32print.OpenPrinter(impresora.nombre_driver)
                    
                    # Iniciar trabajo
                    job_info = ("Prueba Codigos Barras", None, "RAW")
                    job_id = win32print.StartDocPrinter(handle, 1, job_info)
                    
                    # Enviar comandos
                    win32print.StartPagePrinter(handle)
                    win32print.WritePrinter(handle, comandos)
                    win32print.EndPagePrinter(handle)
                    
                    # Finalizar
                    win32print.EndDocPrinter(handle)
                    win32print.ClosePrinter(handle)
                    
                    impreso_directo = True
                    metodo_usado = "Windows directo"
                    
                except Exception as e:
                    import logging
                    logging.warning(f"No se pudo imprimir por Windows: {e}")
            
            # Intentar con Puerto Serial (COM)
            if not impreso_directo and impresora.puerto_serial:
                try:
                    import serial
                    
                    # Abrir puerto serial
                    baudrate = impresora.baudrate or 9600
                    with serial.Serial(impresora.puerto_serial, baudrate, timeout=5) as ser:
                        ser.write(comandos)
                        ser.flush()
                    
                    impreso_directo = True
                    metodo_usado = f"Puerto serial {impresora.puerto_serial}"
                    
                except Exception as e:
                    import logging
                    logging.warning(f"No se pudo imprimir por serial: {e}")
            
            # Intentar con Red
            if not impreso_directo and impresora.tipo_conexion in ['LAN', 'WIFI', 'RAW'] and impresora.direccion_ip:
                try:
                    import socket
                    
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(5)
                        s.connect((impresora.direccion_ip, impresora.puerto_red or 9100))
                        s.sendall(comandos)
                    
                    impreso_directo = True
                    metodo_usado = f"Red {impresora.direccion_ip}"
                    
                except Exception as e:
                    import logging
                    logging.warning(f"No se pudo imprimir por red: {e}")
            
            # Si se imprimió directo, actualizar y mostrar mensaje
            if impreso_directo:
                impresora.fecha_ultima_prueba = timezone.now()
                impresora.save(update_fields=['fecha_ultima_prueba'])
                
                self.message_user(
                    request,
                    f"✅ ¡Página de prueba enviada directamente! Método: {metodo_usado}",
                    messages.SUCCESS
                )
            else:
                # 🔥 SI NO SE PUDO IMPRIMIR DIRECTO, USAR AGENTE
                try:
                    from .api.agente_views import crear_trabajo_impresion, obtener_usuario_para_impresion
                    
                    # Convertir a hexadecimal
                    comandos_hex = comandos.hex()
                    
                    usuario = obtener_usuario_para_impresion()
                    
                    trabajo_id = crear_trabajo_impresion(
                        usuario=usuario,
                        impresora_nombre=impresora.nombre_driver or impresora.nombre,
                        comandos_hex=comandos_hex,
                        tipo='PRUEBA',
                        prioridad=1,
                        abrir_gaveta=False
                    )
                    
                    self.message_user(
                        request,
                        f"⚠️ No se pudo imprimir directamente. "
                        f"Trabajo enviado al agente (ID: {trabajo_id}). "
                        f"Verifica que el agente esté ejecutándose.",
                        messages.WARNING
                    )
                    
                except Exception as e:
                    self.message_user(
                        request,
                        f"❌ No se pudo imprimir ni directamente ni con el agente: {str(e)}",
                        messages.ERROR
                    )
            
        except Impresora.DoesNotExist:
            self.message_user(request, "❌ Impresora no encontrada.", messages.ERROR)
        except Exception as e:
            self.message_user(request, f"❌ Error: {str(e)}", messages.ERROR)
        
        return redirect('admin:hardware_integration_impresora_change', impresora_id)


@admin.register(GavetaDinero)
class GavetaDineroAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'ubicacion', 'tipo_conexion', 'impresora', 'estado', 'activa'
    ]
    list_filter = ['tipo_conexion', 'estado', 'activa', 'requiere_autorizacion']
    search_fields = ['nombre', 'codigo', 'ubicacion']
    readonly_fields = [
        'id', 'codigo', 'contador_aperturas', 'fecha_ultima_apertura',
        'usuario_ultima_apertura'
    ]
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo', 'nombre', 'ubicacion'),
            'description': '📌 El código se genera automáticamente si se deja vacío'
        }),
        ('Conexión', {
            'fields': ('tipo_conexion', 'impresora', 'puerto')
        }),
        ('Configuración', {
            'fields': ('comando_apertura', 'duracion_pulso')
        }),
        ('Control', {
            'fields': (
                'estado', 'activa', 'abrir_en_venta',
                'abrir_en_cobro', 'requiere_autorizacion'
            )
        }),
        ('Auditoría', {
            'fields': (
                'contador_aperturas', 'fecha_ultima_apertura',
                'usuario_ultima_apertura'
            )
        }),
        ('Notas', {
            'fields': ('notas',)
        }),
    )
    actions = [abrir_gavetas_seleccionadas]
    
    def save_model(self, request, obj, form, change):
        """
        Genera automáticamente el código si está vacío
        """
        if not obj.codigo or obj.codigo.strip() == '':
            # Buscar el último código generado
            ultimo = GavetaDinero.objects.filter(
                codigo__startswith='GAV-'
            ).order_by('-codigo').first()
            
            if ultimo and ultimo.codigo:
                try:
                    numero = int(ultimo.codigo.split('-')[1]) + 1
                except (IndexError, ValueError):
                    numero = 1
            else:
                numero = 1
            
            obj.codigo = f'GAV-{numero:03d}'
            
            messages.info(
                request,
                f"✅ Código generado automáticamente: {obj.codigo}"
            )
        
        super().save_model(request, obj, form, change)


@admin.register(PlantillaImpresion)
class PlantillaImpresionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo_documento', 'formato', 'activa', 'es_predeterminada', 'impresora']
    list_filter = ['tipo_documento', 'formato', 'activa', 'es_predeterminada']
    search_fields = ['nombre', 'codigo']
    readonly_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    list_editable = ['activa', 'es_predeterminada']
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo', 'nombre', 'descripcion'),
            'description': '📌 El código se genera automáticamente si se deja vacío'
        }),
        ('Tipo y Formato', {
            'fields': ('tipo_documento', 'formato', 'impresora')
        }),
        ('Contenido', {
            'fields': ('contenido', 'variables_disponibles')
        }),
        ('Diseño', {
            'fields': (
                'incluir_logo', 'incluir_encabezado', 'incluir_pie',
                ('margen_superior', 'margen_inferior'),
                ('margen_izquierdo', 'margen_derecho')
            )
        }),
        ('Estado', {
            'fields': ('activa', 'es_predeterminada')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """
        Genera automáticamente el código si está vacío
        """
        if not obj.codigo or obj.codigo.strip() == '':
            # Buscar el último código generado
            ultimo = PlantillaImpresion.objects.filter(
                codigo__startswith='PLT-'
            ).order_by('-codigo').first()
            
            if ultimo and ultimo.codigo:
                try:
                    numero = int(ultimo.codigo.split('-')[1]) + 1
                except (IndexError, ValueError):
                    numero = 1
            else:
                numero = 1
            
            obj.codigo = f'PLT-{numero:03d}'
            
            messages.info(
                request,
                f"✅ Código generado automáticamente: {obj.codigo}"
            )
        
        super().save_model(request, obj, form, change)


@admin.register(ConfiguracionCodigoBarras)
class ConfiguracionCodigoBarrasAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo_codigo', 'prefijo', 'sufijo', 'activa', 'es_predeterminada']
    list_filter = ['tipo_codigo', 'activa', 'es_predeterminada']
    search_fields = ['nombre']
    readonly_fields = ['id', 'fecha_creacion', 'fecha_actualizacion', 'ultimo_numero']
    list_editable = ['activa', 'es_predeterminada']


@admin.register(RegistroImpresion)
class RegistroImpresionAdmin(admin.ModelAdmin):
    list_display = ['tipo_documento', 'estado_badge', 'impresora', 'venta', 'usuario', 'fecha_impresion_short']
    list_filter = ['tipo_documento', 'estado', 'impresora', 'fecha_impresion']
    search_fields = ['numero_documento', 'contenido_resumen']
    readonly_fields = [f.name for f in RegistroImpresion._meta.fields]
    ordering = ['-fecha_impresion']

    def has_add_permission(self, request):
        return False

    def estado_badge(self, obj):
        badges = {
            'EXITOSO': '<span style="color: green;">✅ Exitoso</span>',
            'ERROR': '<span style="color: red;">❌ Error</span>',
            'CANCELADO': '<span style="color: orange;">⚠️ Cancelado</span>',
            'REINTENTANDO': '<span style="color: blue;">🔄 Reintentando</span>',
        }
        return format_html(badges.get(obj.estado, obj.estado))
    estado_badge.short_description = 'Estado'

    def fecha_impresion_short(self, obj):
        return obj.fecha_impresion.strftime('%d/%m/%Y %H:%M')
    fecha_impresion_short.short_description = 'Fecha'


@admin.register(EscanerCodigoBarras)
class EscanerCodigoBarrasAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'marca', 'modelo', 'tipo_escaner', 'modo_operacion', 'ubicacion', 'activo']
    list_filter = ['tipo_escaner', 'modo_operacion', 'activo', 'marca']
    search_fields = ['nombre', 'codigo', 'marca', 'modelo', 'numero_serie']
    readonly_fields = ['id', 'codigo', 'fecha_instalacion', 'contador_lecturas']
    list_editable = ['activo']
    fieldsets = (
        ('Identificación', {
            'fields': ('codigo', 'nombre', 'marca', 'modelo', 'numero_serie'),
            'description': '📌 El código se genera automáticamente si se deja vacío'
        }),
        ('Tipo y Conexión', {
            'fields': ('tipo_escaner', 'modo_operacion')
        }),
        ('Configuración', {
            'fields': ('prefijo', 'sufijo')
        }),
        ('Códigos Soportados', {
            'fields': (
                'soporta_ean13', 'soporta_ean8', 'soporta_upc',
                'soporta_code128', 'soporta_code39',
                'soporta_qr', 'soporta_datamatrix'
            )
        }),
        ('Estado y Ubicación', {
            'fields': ('activo', 'ubicacion')
        }),
        ('Auditoría', {
            'fields': ('fecha_instalacion', 'contador_lecturas')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """
        Genera automáticamente el código si está vacío
        """
        if not obj.codigo or obj.codigo.strip() == '':
            # Buscar el último código generado
            ultimo = EscanerCodigoBarras.objects.filter(
                codigo__startswith='ESC-'
            ).order_by('-codigo').first()
            
            if ultimo and ultimo.codigo:
                try:
                    numero = int(ultimo.codigo.split('-')[1]) + 1
                except (IndexError, ValueError):
                    numero = 1
            else:
                numero = 1
            
            obj.codigo = f'ESC-{numero:03d}'
            
            messages.info(
                request,
                f"✅ Código generado automáticamente: {obj.codigo}"
            )
        
        super().save_model(request, obj, form, change)