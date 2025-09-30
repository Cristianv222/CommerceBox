# apps/sales_management/invoicing/ticket_generator.py

from django.template.loader import render_to_string
from django.conf import settings
from datetime import datetime


class TicketGenerator:
    """
    Generador de tickets de venta (comprobantes simplificados)
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
        empresa = {
            'nombre': getattr(settings, 'EMPRESA_NOMBRE', 'CommerceBox'),
            'ruc': getattr(settings, 'EMPRESA_RUC', '0000000000001'),
            'direccion': getattr(settings, 'EMPRESA_DIRECCION', 'Ciudad'),
            'telefono': getattr(settings, 'EMPRESA_TELEFONO', '000-0000'),
        }
        
        context = {
            'empresa': empresa,
            'venta': venta,
            'detalles': venta.detalles.all().select_related(
                'producto', 'quintal', 'unidad_medida'
            ),
            'pagos': venta.pagos.all(),
            'fecha_impresion': datetime.now(),
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
        lineas = []
        ancho = 40  # Ancho estándar de impresora térmica
        
        # Encabezado
        empresa_nombre = getattr(settings, 'EMPRESA_NOMBRE', 'CommerceBox')
        lineas.append(empresa_nombre.center(ancho))
        lineas.append(getattr(settings, 'EMPRESA_RUC', '0000000000001').center(ancho))
        lineas.append(getattr(settings, 'EMPRESA_DIRECCION', 'Ciudad').center(ancho))
        lineas.append(getattr(settings, 'EMPRESA_TELEFONO', '000-0000').center(ancho))
        lineas.append('=' * ancho)
        
        # Datos de venta
        lineas.append(f"Ticket: {venta.numero_venta}")
        lineas.append(f"Fecha: {venta.fecha_venta.strftime('%d/%m/%Y %H:%M')}")
        lineas.append(f"Vendedor: {venta.vendedor.username}")
        
        if venta.cliente:
            lineas.append(f"Cliente: {venta.cliente.nombre_completo()}")
            lineas.append(f"Doc: {venta.cliente.numero_documento}")
        
        lineas.append('=' * ancho)
        
        # Detalles
        lineas.append("PRODUCTO                   CANT    TOTAL")
        lineas.append('-' * ancho)
        
        for detalle in venta.detalles.all():
            nombre = detalle.producto.nombre[:23]
            
            if detalle.producto.es_quintal():
                cant = f"{detalle.peso_vendido} {detalle.unidad_medida.abreviatura}"
            else:
                cant = f"{detalle.cantidad_unidades} un"
            
            total = f"${detalle.total:.2f}"
            
            linea = f"{nombre:<23} {cant:>7} {total:>8}"
            lineas.append(linea)
        
        lineas.append('=' * ancho)
        
        # Totales
        lineas.append(f"{'SUBTOTAL:':<30} ${venta.subtotal:>8.2f}")
        if venta.descuento > 0:
            lineas.append(f"{'DESCUENTO:':<30} -${venta.descuento:>7.2f}")
        if venta.impuestos > 0:
            lineas.append(f"{'IMPUESTOS:':<30} ${venta.impuestos:>8.2f}")
        lineas.append(f"{'TOTAL:':<30} ${venta.total:>8.2f}")
        
        lineas.append('=' * ancho)
        
        # Pagos
        for pago in venta.pagos.all():
            forma = pago.get_forma_pago_display()
            lineas.append(f"{forma:<30} ${pago.monto:>8.2f}")
        
        if venta.cambio > 0:
            lineas.append(f"{'CAMBIO:':<30} ${venta.cambio:>8.2f}")
        
        lineas.append('=' * ancho)
        lineas.append("GRACIAS POR SU COMPRA".center(ancho))
        lineas.append('')
        
        return '\n'.join(lineas)