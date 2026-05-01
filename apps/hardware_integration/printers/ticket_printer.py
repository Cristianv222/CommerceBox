# apps/hardware_integration/printers/ticket_printer.py

import logging
from escpos import printer as escpos_printer
from escpos.exceptions import Error as EscposError
from ..models import RegistroImpresion
from django.conf import settings
import io

logger = logging.getLogger(__name__)


def precalcular_clave_acceso_sri(venta):
    """
    Intenta calcular la clave de acceso del SRI antes de que el comprobante sea guardado.
    Útil para impresión inmediata de tickets en el POS.
    """
    try:
        from apps.electronic_invoicing.models import SRIConfig, PuntoEmision
        from apps.electronic_invoicing.utils import generar_clave_acceso
        import random
        
        config_sri = SRIConfig.objects.first()
        if not config_sri:
            return None
            
        # Determinar el punto de emisión (usamos el primero activo por defecto si no se especifica)
        punto = PuntoEmision.objects.filter(activo=True).first()
        if not punto:
            return None
            
        # Datos para la clave
        fecha = venta.fecha_venta
        tipo_comprobante = "01"  # Factura
        ruc = config_sri.ruc
        ambiente = str(config_sri.ambiente)
        serie = f"{punto.establecimiento}{punto.punto_emision}"
        
        # El secuencial debe ser el número de venta formateado a 9 dígitos
        # NOTA: Esto asume que el numero_venta coincide con el secuencial del SRI
        secuencial = str(venta.numero_venta).zfill(9)
        
        # El código numérico suele ser aleatorio o fijo (usamos uno basado en la venta)
        codigo_numerico = str(venta.id.int)[:8]
        tipo_emision = str(config_sri.tipo_emision)
        
        clave = generar_clave_acceso(
            fecha, tipo_comprobante, ruc, ambiente, serie, secuencial, codigo_numerico, tipo_emision
        )
        return clave
    except Exception as e:
        logger.error(f"Error precalculando clave SRI: {e}")
        return None


class TicketPrinter:
    """
    Servicio para imprimir tickets de venta
    ✅ ACTUALIZADO: Usa configuración desde system_configuration
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
            # ✅ Obtener configuración del sistema
            from apps.system_configuration.models import ConfiguracionSistema
            config = ConfiguracionSistema.get_config()
            
            # Crear impresora virtual (Dummy) para capturar comandos
            # Esto NO envía a imprimir, solo genera los bytes
            p = escpos_printer.Dummy()
            
            # ========================================
            # ENCABEZADO
            # ========================================
            p.set(align='center', bold=True, double_width=True, double_height=True)
            p.text(f"{config.nombre_empresa}\n")
            
            p.set(align='center', bold=False, double_width=False, double_height=False)
            
            # RUC/NIT
            if config.ruc_empresa:
                p.text(f"RUC: {config.ruc_empresa}\n")
            
            # Dirección
            if config.direccion_empresa:
                # Truncar dirección si es muy larga (máx 42 caracteres)
                direccion = config.direccion_empresa[:42]
                p.text(f"{direccion}\n")
            
            # Teléfono
            if config.telefono_empresa:
                p.text(f"Tel: {config.telefono_empresa}\n")
            
            # Email
            if config.email_empresa:
                p.text(f"{config.email_empresa}\n")
            
            # Sitio web
            if config.sitio_web:
                # Remover http:// o https:// para ahorrar espacio
                sitio = config.sitio_web.replace('https://', '').replace('http://', '')
                p.text(f"{sitio}\n")
            
            p.text("=" * 42 + "\n")
            
            # ========================================
            # DATOS DE LA VENTA
            # ========================================
            p.set(align='left', bold=False)
            
            # Número de ticket con el prefijo configurado
            numero_venta = f"{config.prefijo_numero_venta}-{venta.numero_venta}"
            p.text(f"Ticket: {numero_venta}\n")
            
            # Fecha en formato configurado
            fecha_formato = venta.fecha_venta.strftime('%d/%m/%Y %H:%M')
            p.text(f"Fecha: {fecha_formato}\n")
            p.text(f"Vendedor: {venta.vendedor.username}\n")
            
            if venta.cliente:
                p.text(f"Cliente: {venta.cliente.nombre_completo()}\n")
                p.text(f"Doc: {venta.cliente.numero_documento}\n")
            
            p.text("=" * 42 + "\n")
            
            # ========================================
            # DETALLES DE PRODUCTOS
            # ========================================
            p.set(bold=False)
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
                
                # ✅ Usar símbolo de moneda configurado
                simbolo = config.simbolo_moneda
                decimales = config.decimales_moneda
                
                precio = f"{simbolo}{detalle.precio_unitario:.{decimales}f}".rjust(9)
                total = f"{simbolo}{detalle.total:.{decimales}f}".rjust(9)
                
                p.text(f"{nombre} {cant_str:>7} {precio} {total}\n")
            
            p.text("=" * 42 + "\n")
            
            # ========================================
            # TOTALES
            # ========================================
            p.set(bold=True)  # Negrita
            
            simbolo = config.simbolo_moneda
            decimales = config.decimales_moneda
            
            # Subtotal (Base Imponible)
            p.text(f"{'SUBTOTAL:':.<30} {simbolo}{venta.subtotal:>9.{decimales}f}\n")
            
            if venta.descuento > 0:
                p.text(f"{'DESCUENTO:':.<30} -{simbolo}{venta.descuento:>8.{decimales}f}\n")
            
            # ✅ Mostrar IVA desglosado siempre que el producto lo grabe (PVP Incluido)
            if venta.impuestos > 0:
                p.text(f"{'IVA ({:.0f}%):'.format(config.porcentaje_iva):.<30} {simbolo}{venta.impuestos:>9.{decimales}f}\n")
            else:
                p.text(f"{'IVA (0%):':.<30} {simbolo}{'0.00':>9}\n")
            
            p.set(bold=True, double_width=True, double_height=True)
            p.text(f"{'TOTAL:':.<30} {simbolo}{venta.total:>9.{decimales}f}\n")
            
            p.set(bold=False, double_width=False, double_height=False)
            p.text("=" * 42 + "\n")
            
            # ========================================
            # FORMAS DE PAGO
            # ========================================
            for pago in venta.pagos.all():
                forma = pago.get_forma_pago_display()
                p.text(f"{forma:.<30} {simbolo}{pago.monto:>9.{decimales}f}\n")
            
            if venta.cambio > 0:
                p.set(bold=True)
                p.text(f"{'CAMBIO:':.<30} {simbolo}{venta.cambio:>9.{decimales}f}\n")
                p.set(bold=False)
            
            p.text("=" * 42 + "\n")

            # ========================================
            # ✅ INFORMACIÓN SRI (SOLO SI ES FACTURA)
            # ========================================
            try:
                clave_acceso = None
                ambiente_str = "PRUEBAS"
                
                # 1. Intentar obtener del objeto real si ya existe
                if hasattr(venta, 'comprobante_electronico') and venta.comprobante_electronico:
                    ce = venta.comprobante_electronico
                    clave_acceso = ce.clave_acceso
                    ambiente_str = ce.get_ambiente_display().upper()
                
                # 2. Si no existe aún (POS inmediato), precalcularla
                if not clave_acceso:
                    clave_acceso = precalcular_clave_acceso_sri(venta)
                    from apps.electronic_invoicing.models import SRIConfig
                    cfg = SRIConfig.objects.first()
                    if cfg:
                        ambiente_str = cfg.get_ambiente_display().upper()
                
                if clave_acceso:
                    p.set(align='center', bold=True)
                    p.text("\nFACTURA ELECTRONICA SRI\n")
                    p.set(align='left', bold=False)
                    
                    p.text(f"CLAVE DE ACCESO:\n")
                    p.set(font='b') # Fuente más pequeña para la clave larga
                    p.text(f"{clave_acceso}\n")
                    p.set(font='a')
                    
                    p.text(f"AMBIENTE: {ambiente_str}\n")
                    p.text(f"EMISION: NORMAL\n")
                    p.text("-" * 42 + "\n")
            except Exception as e:
                logger.error(f"Error imprimiendo info SRI en ticket: {e}")

            p.text("\n")
            
            # ========================================
            # PIE DE TICKET
            # ========================================
            p.set(align='center')
            p.text("GRACIAS POR SU COMPRA\n")
            
            # Mensaje personalizado si existe
            if hasattr(venta, 'mensaje_personalizado') and venta.mensaje_personalizado:
                p.text(f"{venta.mensaje_personalizado}\n")
            
            # Sitio web en el pie
            if config.sitio_web:
                sitio = config.sitio_web.replace('https://', '').replace('http://', '')
                p.text(f"{sitio}\n")
            
            p.text("\n")
            
            # ========================================
            # ABRIR GAVETA DE DINERO
            # ========================================
            if impresora_obj.tiene_gaveta:
                logger.info("Abriendo gaveta de dinero...")
                p.cashdraw(2)  # Pin 2
                p.cashdraw(5)  # Pin 5 (por compatibilidad)
            
            # Cortar papel
            p.cut()
            
            # Obtener los bytes generados
            comandos_bytes = p.output
            
            # Convertir a hexadecimal para enviar al agente
            comandos_hex = comandos_bytes.hex()
            
            logger.info(f"Comandos generados: {len(comandos_hex)} caracteres hex")
            logger.info(f"   Empresa: {config.nombre_empresa}")
            logger.info(f"   Moneda: {config.simbolo_moneda} ({config.moneda})")
            logger.info(f"   IVA activo: {config.iva_activo}")
            
            return comandos_hex
            
        except Exception as e:
            logger.error(f"Error generando comandos de ticket: {e}", exc_info=True)
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
            
            logger.info(f"Ticket encolado con ID: {trabajo_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error al imprimir ticket: {e}", exc_info=True)
            return False
    
    
    @staticmethod
    def imprimir_ticket_prueba(impresora_obj):
        """
        Imprime un ticket de prueba
        ✅ ACTUALIZADO: Usa configuración del sistema
        """
        try:
            # ✅ Obtener configuración del sistema
            from apps.system_configuration.models import ConfiguracionSistema
            config = ConfiguracionSistema.get_config()
            
            p = escpos_printer.Dummy()
            
            # Encabezado de prueba
            p.set(align='center', bold=True, double_width=True, double_height=True)
            p.text("TICKET DE PRUEBA\n\n")
            
            # Información de la empresa
            p.set(align='center', bold=False, double_width=False, double_height=False)
            p.text(f"{config.nombre_empresa}\n")
            
            if config.ruc_empresa:
                p.text(f"RUC: {config.ruc_empresa}\n")
            
            p.text("=" * 42 + "\n")
            
            # Información técnica
            p.set(align='left', bold=False)
            p.text(f"Impresora: {impresora_obj.nombre}\n")
            p.text(f"Modelo: {impresora_obj.modelo}\n")
            p.text(f"Moneda: {config.moneda} ({config.simbolo_moneda})\n")
            p.text(f"Decimales: {config.decimales_moneda}\n")
            p.text(f"IVA: {config.porcentaje_iva}% ")
            p.text(f"({'Activo' if config.iva_activo else 'Inactivo'})\n")
            p.text(f"Zona Horaria: {config.zona_horaria}\n")
            
            p.text("=" * 42 + "\n\n")
            
            # Mensaje de éxito
            p.set(align='center')
            p.text("Si puede leer esto,\n")
            p.text("su impresora funciona correctamente\n\n")
            
            # Información de contacto
            if config.telefono_empresa:
                p.text(f"Tel: {config.telefono_empresa}\n")
            
            if config.email_empresa:
                p.text(f"{config.email_empresa}\n")
            
            if config.sitio_web:
                sitio = config.sitio_web.replace('https://', '').replace('http://', '')
                p.text(f"{sitio}\n")
            
            p.text("\n")
            
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
            
            logger.info(f"Ticket de prueba encolado con ID: {trabajo_id}")
            logger.info(f"   Configuración: {config.nombre_empresa}")
            return True
            
        except Exception as e:
            logger.error(f"Error al imprimir ticket de prueba: {e}", exc_info=True)
            return False