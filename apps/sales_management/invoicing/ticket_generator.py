# apps/sales_management/invoicing/ticket_generator.py

from django.template.loader import render_to_string
from datetime import datetime


class TicketGenerator:
    """
    Generador de tickets de venta (comprobantes simplificados)
    ✅ ACTUALIZADO: Usa configuración desde system_configuration
    """
    
    @staticmethod
    def generar_ticket_html(venta):
        """
        Genera HTML del ticket para impresión térmica
        
        Args:
            venta: Venta
        
        Returns:
            str: HTML del ticket
        """
        # ✅ Obtener configuración del sistema
        from apps.system_configuration.models import ConfiguracionSistema
        config = ConfiguracionSistema.get_config()
        
        empresa = {
            'nombre': config.nombre_empresa,
            'ruc': config.ruc_empresa,
            'direccion': config.direccion_empresa,
            'telefono': config.telefono_empresa,
            'email': config.email_empresa,
            'sitio_web': config.sitio_web,
        }
        
        context = {
            'empresa': empresa,
            'venta': venta,
            'detalles': venta.detalles.all().select_related(
                'producto', 'quintal', 'unidad_medida'
            ),
            'pagos': venta.pagos.all(),
            'fecha_impresion': datetime.now(),
            'config': config,  # ✅ Pasar config completo al template
        }
        
        return render_to_string('sales/ticket_template.html', context)
    
    @staticmethod
    def generar_ticket_texto(venta):
        """
        Genera ticket en formato texto plano para impresoras ESC/POS
        
        Args:
            venta: Venta
        
        Returns:
            str: Texto del ticket
        """
        # ✅ Obtener configuración del sistema
        from apps.system_configuration.models import ConfiguracionSistema
        config = ConfiguracionSistema.get_config()
        
        lineas = []
        ancho = 40  # Ancho estándar de impresora térmica
        
        # ========================================
        # ENCABEZADO
        # ========================================
        lineas.append(config.nombre_empresa.center(ancho))
        
        if config.ruc_empresa:
            lineas.append(f"RUC: {config.ruc_empresa}".center(ancho))
        
        if config.direccion_empresa:
            # Truncar si es muy larga
            direccion = config.direccion_empresa[:ancho]
            lineas.append(direccion.center(ancho))
        
        if config.telefono_empresa:
            lineas.append(f"Tel: {config.telefono_empresa}".center(ancho))
        
        if config.email_empresa:
            lineas.append(config.email_empresa.center(ancho))
        
        if config.sitio_web:
            sitio = config.sitio_web.replace('https://', '').replace('http://', '')
            lineas.append(sitio.center(ancho))
        
        lineas.append('=' * ancho)
        
        # ========================================
        # DATOS DE VENTA
        # ========================================
        numero_venta = f"{config.prefijo_numero_venta}-{venta.numero_venta}"
        lineas.append(f"Ticket: {numero_venta}")
        lineas.append(f"Fecha: {venta.fecha_venta.strftime('%d/%m/%Y %H:%M')}")
        lineas.append(f"Vendedor: {venta.vendedor.username}")
        
        if venta.cliente:
            lineas.append(f"Cliente: {venta.cliente.nombre_completo()}")
            lineas.append(f"Doc: {venta.cliente.numero_documento}")
        
        lineas.append('=' * ancho)
        
        # ========================================
        # DETALLES
        # ========================================
        lineas.append("PRODUCTO                   CANT    TOTAL")
        lineas.append('-' * ancho)
        
        simbolo = config.simbolo_moneda
        decimales = config.decimales_moneda
        
        for detalle in venta.detalles.all():
            nombre = detalle.producto.nombre[:23]
            
            if detalle.producto.es_quintal():
                unidad = detalle.unidad_medida.abreviatura if detalle.unidad_medida else "kg"
                cant = f"{detalle.peso_vendido:.2f} {unidad}"
            else:
                cant = f"{int(detalle.cantidad_unidades)} un"
            
            total = f"{simbolo}{detalle.total:.{decimales}f}"
            
            linea = f"{nombre:<23} {cant:>7} {total:>8}"
            lineas.append(linea)
        
        lineas.append('=' * ancho)
        
        # ========================================
        # TOTALES
        # ========================================
        lineas.append(f"{'SUBTOTAL:':<30} {simbolo}{venta.subtotal:>{8}.{decimales}f}")
        
        if venta.descuento > 0:
            lineas.append(f"{'DESCUENTO:':<30} -{simbolo}{venta.descuento:>{7}.{decimales}f}")
        
        # ✅ Mostrar IVA solo si está activo
        if config.iva_activo and venta.impuestos > 0:
            iva_label = f"IVA ({config.porcentaje_iva:.0f}%):"
            lineas.append(f"{iva_label:<30} {simbolo}{venta.impuestos:>{8}.{decimales}f}")
        
        lineas.append(f"{'TOTAL:':<30} {simbolo}{venta.total:>{8}.{decimales}f}")
        
        lineas.append('=' * ancho)
        
        # ========================================
        # PAGOS
        # ========================================
        for pago in venta.pagos.all():
            forma = pago.get_forma_pago_display()
            lineas.append(f"{forma:<30} {simbolo}{pago.monto:>{8}.{decimales}f}")
        
        if venta.cambio > 0:
            lineas.append(f"{'CAMBIO:':<30} {simbolo}{venta.cambio:>{8}.{decimales}f}")
        
        lineas.append('=' * ancho)
        
        # ========================================
        # PIE DE TICKET
        # ========================================
        lineas.append("GRACIAS POR SU COMPRA".center(ancho))
        
        if config.sitio_web:
            sitio = config.sitio_web.replace('https://', '').replace('http://', '')
            lineas.append(sitio.center(ancho))
        
        lineas.append('')
        
        return '\n'.join(lineas)