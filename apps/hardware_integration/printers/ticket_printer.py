# apps/hardware_integration/printers/ticket_printer.py

import logging
from escpos import printer as escpos_printer
from escpos.exceptions import Error as EscposError
from ..models import RegistroImpresion
from django.conf import settings
import io

logger = logging.getLogger(__name__)


class TicketPrinter:
    """
    Servicio para imprimir tickets de venta
    """
    
    @staticmethod
    def generar_comandos_ticket(venta, impresora_obj):
        """
        Genera los comandos ESC/POS para imprimir un ticket
        
        Args:
            venta: Instancia del modelo Venta
            impresora_obj: Instancia del modelo Impresora
        
        Returns:
            str: Comandos ESC/POS en formato hexadecimal
        """
        try:
            # Crear impresora virtual (Dummy) para capturar comandos
            # Esto NO envía a imprimir, solo genera los bytes
            p = escpos_printer.Dummy()
            
            # ========================================
            # ENCABEZADO
            # ========================================
            p.set(align='center', text_type='B', width=2, height=2)
            empresa_nombre = getattr(settings, 'EMPRESA_NOMBRE', 'CommerceBox')
            p.text(f"{empresa_nombre}\n")
            
            p.set(align='center', text_type='normal')
            empresa_ruc = getattr(settings, 'EMPRESA_RUC', '0000000000001')
            empresa_dir = getattr(settings, 'EMPRESA_DIRECCION', 'Ciudad')
            empresa_tel = getattr(settings, 'EMPRESA_TELEFONO', '000-0000')
            
            p.text(f"RUC: {empresa_ruc}\n")
            p.text(f"{empresa_dir}\n")
            p.text(f"Tel: {empresa_tel}\n")
            
            p.text("=" * 42 + "\n")
            
            # ========================================
            # DATOS DE LA VENTA
            # ========================================
            p.set(align='left', text_type='normal')
            p.text(f"Ticket: {venta.numero_venta}\n")
            p.text(f"Fecha: {venta.fecha_venta.strftime('%d/%m/%Y %H:%M')}\n")
            p.text(f"Vendedor: {venta.vendedor.username}\n")
            
            if venta.cliente:
                p.text(f"Cliente: {venta.cliente.nombre_completo()}\n")
                p.text(f"Doc: {venta.cliente.numero_documento}\n")
            
            p.text("=" * 42 + "\n")
            
            # ========================================
            # DETALLES DE PRODUCTOS
            # ========================================
            p.set(text_type='normal')
            p.text("PRODUCTO          CANT      PRECIO     TOTAL\n")
            p.text("-" * 42 + "\n")
            
            for detalle in venta.detalles.all():
                nombre = detalle.producto.nombre[:15].ljust(15)
                
                if detalle.producto.es_quintal():
                    cant = f"{detalle.peso_vendido:.2f}".rjust(4)
                    uni = detalle.unidad_medida.abreviatura if detalle.unidad_medida else "kg"
                    cant_str = f"{cant} {uni}"
                else:
                    cant_str = f"{int(detalle.cantidad_unidades):>4} un"
                
                precio = f"${detalle.precio_unitario:.2f}".rjust(9)
                total = f"${detalle.total:.2f}".rjust(9)
                
                p.text(f"{nombre} {cant_str:>7} {precio} {total}\n")
            
            p.text("=" * 42 + "\n")
            
            # ========================================
            # TOTALES
            # ========================================
            p.set(text_type='B')  # Negrita
            p.text(f"{'SUBTOTAL:':.<30} ${venta.subtotal:>9.2f}\n")
            
            if venta.descuento > 0:
                p.text(f"{'DESCUENTO:':.<30} -${venta.descuento:>8.2f}\n")
            
            if venta.impuestos > 0:
                p.text(f"{'IMPUESTOS:':.<30} ${venta.impuestos:>9.2f}\n")
            
            p.set(text_type='B', width=2, height=2)
            p.text(f"{'TOTAL:':.<30} ${venta.total:>9.2f}\n")
            
            p.set(text_type='normal', width=1, height=1)
            p.text("=" * 42 + "\n")
            
            # ========================================
            # FORMAS DE PAGO
            # ========================================
            for pago in venta.pagos.all():
                forma = pago.get_forma_pago_display()
                p.text(f"{forma:.<30} ${pago.monto:>9.2f}\n")
            
            if venta.cambio > 0:
                p.set(text_type='B')
                p.text(f"{'CAMBIO:':.<30} ${venta.cambio:>9.2f}\n")
                p.set(text_type='normal')
            
            p.text("=" * 42 + "\n\n")
            
            # ========================================
            # PIE DE TICKET
            # ========================================
            p.set(align='center')
            p.text("GRACIAS POR SU COMPRA\n")
            p.text(f"www.tuempresa.com\n\n")
            
            # ========================================
            # ABRIR GAVETA DE DINERO
            # ========================================
            if impresora_obj.tiene_gaveta:
                logger.info("💰 Abriendo gaveta de dinero...")
                p.cashdraw(2)  # Pin 2
                p.cashdraw(5)  # Pin 5 (por compatibilidad)
            
            # Cortar papel
            p.cut()
            
            # Obtener los bytes generados
            comandos_bytes = p.output
            
            # Convertir a hexadecimal para enviar al agente
            comandos_hex = comandos_bytes.hex()
            
            logger.info(f"✅ Comandos generados: {len(comandos_hex)} caracteres hex")
            
            return comandos_hex
            
        except Exception as e:
            logger.error(f"❌ Error generando comandos de ticket: {e}", exc_info=True)
            raise
    
    
    @staticmethod
    def imprimir_ticket(venta, impresora_obj):
        """
        Método de compatibilidad para imprimir directamente
        (usado en pruebas del módulo de hardware)
        """
        try:
            comandos_hex = TicketPrinter.generar_comandos_ticket(venta, impresora_obj)
            
            # Encolar trabajo
            from ..api.agente_views import crear_trabajo_impresion
            
            trabajo_id = crear_trabajo_impresion(
                usuario=venta.vendedor,
                impresora_nombre=impresora_obj.nombre_driver or impresora_obj.nombre,
                comandos_hex=comandos_hex,
                tipo='ticket',
                prioridad=2
            )
            
            logger.info(f"✅ Ticket encolado con ID: {trabajo_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al imprimir ticket: {e}", exc_info=True)
            return False
    
    
    @staticmethod
    def imprimir_ticket_prueba(impresora_obj):
        """
        Imprime un ticket de prueba
        """
        try:
            p = escpos_printer.Dummy()
            
            p.set(align='center', text_type='B', width=2, height=2)
            p.text("TICKET DE PRUEBA\n\n")
            
            p.set(align='left', text_type='normal', width=1, height=1)
            p.text("=" * 42 + "\n")
            p.text("Esta es una prueba de impresion\n")
            p.text(f"Impresora: {impresora_obj.nombre}\n")
            p.text(f"Modelo: {impresora_obj.modelo}\n")
            p.text("=" * 42 + "\n\n")
            
            p.set(align='center')
            p.text("Si puede leer esto,\n")
            p.text("su impresora funciona correctamente\n\n")
            
            # Probar gaveta si está configurada
            if impresora_obj.tiene_gaveta:
                p.text("Probando apertura de gaveta...\n")
                p.cashdraw(2)
                p.cashdraw(5)
            
            p.cut()
            
            comandos_hex = p.output.hex()
            
            from ..api.agente_views import crear_trabajo_impresion, obtener_usuario_para_impresion
            
            usuario = obtener_usuario_para_impresion()
            
            trabajo_id = crear_trabajo_impresion(
                usuario=usuario,
                impresora_nombre=impresora_obj.nombre_driver or impresora_obj.nombre,
                comandos_hex=comandos_hex,
                tipo='test',
                prioridad=3  # Máxima prioridad para pruebas
            )
            
            logger.info(f"✅ Ticket de prueba encolado con ID: {trabajo_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al imprimir ticket de prueba: {e}", exc_info=True)
            return False