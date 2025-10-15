# apps/hardware_integration/printers/printer_service.py

import socket
import serial
import usb.core
import usb.util
#import cups
import subprocess
import time
import logging
import os
from typing import Optional
from django.conf import settings
from django.utils import timezone
from escpos import printer as escpos_printer

logger = logging.getLogger(__name__)


class PrinterService:
    """
    Servicio unificado para manejo de impresoras
    Soporta múltiples tipos de conexión y protocolos
    """
    
    # TIMEOUTS para operaciones
    CONNECTION_TIMEOUT = 5
    OPERATION_TIMEOUT = 10
    
    @staticmethod
    def get_printer_connection(impresora):
        """
        Obtiene la conexión a la impresora según su tipo
        
        Args:
            impresora: Modelo Impresora
        
        Returns:
            Objeto de conexión o None si falla
        """
        try:
            if impresora.tipo_conexion == 'USB':
                return PrinterService._conectar_usb(impresora)
            elif impresora.tipo_conexion in ['LAN', 'WIFI']:
                return PrinterService._conectar_red(impresora)
            elif impresora.tipo_conexion == 'SERIAL':
                return PrinterService._conectar_serial(impresora)
            elif impresora.tipo_conexion == 'DRIVER':
                return PrinterService._conectar_driver(impresora)
            elif impresora.tipo_conexion == 'RAW':
                return PrinterService._conectar_raw_socket(impresora)
            else:
                logger.error(f"Tipo de conexión no soportado: {impresora.tipo_conexion}")
                return None
        except Exception as e:
            logger.error(f"Error al conectar con impresora {impresora.nombre}: {str(e)}")
            return None
    
    @staticmethod
    def _conectar_usb(impresora):
        """Conexión USB directa o usando librería escpos"""
        try:
            if impresora.protocolo == 'ESC_POS':
                if impresora.vid_usb and impresora.pid_usb:
                    p = escpos_printer.Usb(
                        int(impresora.vid_usb, 16),
                        int(impresora.pid_usb, 16),
                        timeout=PrinterService.CONNECTION_TIMEOUT
                    )
                else:
                    p = escpos_printer.File(impresora.puerto_usb)
                return p
            else:
                if impresora.vid_usb and impresora.pid_usb:
                    dev = usb.core.find(
                        idVendor=int(impresora.vid_usb, 16),
                        idProduct=int(impresora.pid_usb, 16)
                    )
                    if dev is None:
                        raise ValueError('Dispositivo USB no encontrado')
                    dev.set_configuration()
                    return dev
                else:
                    return open(impresora.puerto_usb, 'wb')
        except Exception as e:
            logger.error(f"Error en conexión USB: {str(e)}")
            raise
    
    @staticmethod
    def _conectar_red(impresora):
        """Conexión de red (LAN/WiFi)"""
        try:
            if impresora.protocolo == 'ESC_POS':
                p = escpos_printer.Network(
                    impresora.direccion_ip,
                    port=impresora.puerto_red or 9100,
                    timeout=PrinterService.CONNECTION_TIMEOUT
                )
                return p
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(PrinterService.CONNECTION_TIMEOUT)
                s.connect((impresora.direccion_ip, impresora.puerto_red or 9100))
                return s
        except Exception as e:
            logger.error(f"Error en conexión de red: {str(e)}")
            raise
    
    @staticmethod
    def _conectar_serial(impresora):
        """Conexión serial (COM/ttyS)"""
        try:
            if impresora.protocolo == 'ESC_POS':
                return escpos_printer.Serial(
                    devfile=impresora.puerto_serial,
                    baudrate=impresora.baudrate or 9600,
                    timeout=PrinterService.CONNECTION_TIMEOUT
                )
            else:
                ser = serial.Serial(
                    port=impresora.puerto_serial,
                    baudrate=impresora.baudrate or 9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=PrinterService.CONNECTION_TIMEOUT
                )
                return ser
        except Exception as e:
            logger.error(f"Error en conexión serial: {str(e)}")
            raise
    
    @staticmethod
    def _conectar_driver(impresora):
        """Conexión usando driver del sistema (Windows/CUPS)"""
        try:
            if hasattr(cups, 'Connection'):
                conn = cups.Connection()
                printers = conn.getPrinters()
                if impresora.nombre_driver in printers:
                    return {'type': 'cups', 'connection': conn, 'printer': impresora.nombre_driver}
            return {'type': 'windows', 'printer': impresora.nombre_driver}
        except Exception as e:
            logger.error(f"Error en conexión por driver: {str(e)}")
            raise
    
    @staticmethod
    def _conectar_raw_socket(impresora):
        """Conexión Raw Socket TCP/IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(PrinterService.CONNECTION_TIMEOUT)
            s.connect((impresora.direccion_ip, impresora.puerto_red or 9100))
            return s
        except Exception as e:
            logger.error(f"Error en conexión raw socket: {str(e)}")
            raise
    
    @staticmethod
    def test_connection(impresora):
        """
        Prueba la conexión con la impresora
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            conn = PrinterService.get_printer_connection(impresora)
            if conn is None:
                return False, "No se pudo establecer conexión"
            
            # Probar según tipo de protocolo
            if impresora.protocolo == 'ESC_POS' and hasattr(conn, 'device'):
                conn.text("Prueba\\n")
                if impresora.soporta_corte_automatico:
                    conn.cut()
                return True, "Conexión ESC/POS exitosa"
            
            # Para otros protocolos
            if isinstance(conn, socket.socket):
                conn.send(b"TEST\\n")
                conn.close()
                return True, "Conexión de red exitosa"
            
            if isinstance(conn, serial.Serial):
                conn.write(b"TEST\\n")
                conn.close()
                return True, "Conexión serial exitosa"
            
            return True, "Conexión establecida"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
        finally:
            try:
                if hasattr(conn, 'close') and callable(getattr(conn, 'close')):
                    conn.close()
            except:
                pass
    
    @staticmethod
    def print_test_page(impresora):
        """
        Imprime una página de prueba
        
        Returns:
            bool: True si fue exitoso
        """
        from ..models import RegistroImpresion
        
        inicio = time.time()
        
        try:
            conn = PrinterService.get_printer_connection(impresora)
            if conn is None:
                raise Exception("No se pudo conectar a la impresora")
            
            if impresora.protocolo == 'ESC_POS' and hasattr(conn, 'text'):
                PrinterService._imprimir_test_escpos(conn, impresora)
            else:
                texto = PrinterService._generar_texto_test(impresora)
                PrinterService._enviar_texto_generico(conn, texto)
            
            # Registrar impresión
            tiempo_ms = int((time.time() - inicio) * 1000)
            RegistroImpresion.objects.create(
                impresora=impresora,
                tipo_documento='OTRO',
                numero_documento='TEST-PAGE',
                contenido_resumen='Página de prueba',
                estado='EXITOSO',
                tiempo_procesamiento=tiempo_ms
            )
            
            impresora.fecha_ultima_prueba = timezone.now()
            impresora.save(update_fields=['fecha_ultima_prueba'])
            return True
            
        except Exception as e:
            logger.error(f"Error al imprimir página de prueba: {str(e)}")
            RegistroImpresion.objects.create(
                impresora=impresora,
                tipo_documento='OTRO',
                numero_documento='TEST-PAGE',
                contenido_resumen='Página de prueba',
                estado='ERROR',
                mensaje_error=str(e)
            )
            return False
        finally:
            try:
                if hasattr(conn, 'close') and callable(getattr(conn, 'close')):
                    conn.close()
            except:
                pass
    
    @staticmethod
    def _imprimir_test_escpos(conn, impresora):
        """Imprime página de prueba ESC/POS"""
        from django.conf import settings
        
        # Usar valores por defecto si no existen en settings
        empresa_nombre = getattr(settings, 'EMPRESA_NOMBRE', 'COMMERCEBOX')
        empresa_ruc = getattr(settings, 'EMPRESA_RUC', 'RUC: 1234567890001')
        empresa_direccion = getattr(settings, 'EMPRESA_DIRECCION', 'Dirección de la empresa')
        empresa_telefono = getattr(settings, 'EMPRESA_TELEFONO', 'Teléfono')
        
        conn.set(align='center', text_type='B', width=2, height=2)
        conn.text(f"{empresa_nombre}\\n")
        conn.text("=" * 42 + "\\n\\n")
        
        conn.set(align='left', text_type='NORMAL')
        conn.text(f"Impresora: {impresora.nombre}\\n")
        conn.text(f"Modelo: {impresora.marca} {impresora.modelo}\\n")
        conn.text(f"Conexión: {impresora.get_connection_info()}\\n")
        conn.text(f"Fecha: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")
        
        if impresora.soporta_codigo_barras:
            conn.text("Código de Barras:\\n")
            conn.barcode('1234567890128', 'EAN13', 64, 2, '', '')
            conn.text("\\n")
        
        if impresora.soporta_qr:
            conn.text("Código QR:\\n")
            conn.qr("https://commercebox.com", size=4)
            conn.text("\\n")
        
        conn.text("=" * 42 + "\\n")
        conn.text("PRUEBA EXITOSA\\n")
        conn.text("=" * 42 + "\\n")
        
        if impresora.soporta_corte_automatico:
            conn.cut()
        
        if impresora.tiene_gaveta:
            conn.cashdraw(impresora.pin_gaveta or 0)
    
    @staticmethod
    def _generar_texto_test(impresora):
        """Genera texto de prueba genérico"""
        return f"""
COMMERCEBOX - PÁGINA DE PRUEBA
================================
Impresora: {impresora.nombre}
Modelo: {impresora.marca} {impresora.modelo}
Conexión: {impresora.get_connection_info()}
Fecha: {timezone.now()}
================================
PRUEBA EXITOSA
================================
        """
    
    @staticmethod
    def _enviar_texto_generico(conn, texto):
        """Envía texto a conexiones genéricas"""
        if isinstance(conn, socket.socket):
            conn.send(texto.encode())
        elif isinstance(conn, serial.Serial):
            conn.write(texto.encode())
        elif isinstance(conn, dict) and conn['type'] == 'cups':
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(texto)
                temp_file = f.name
            try:
                conn['connection'].printFile(conn['printer'], temp_file, "Prueba CommerceBox", {})
            finally:
                os.unlink(temp_file)
    
    @staticmethod
    def enviar_comando_raw(impresora, comando: bytes):
        """Envía comando raw a la impresora"""
        conn = PrinterService.get_printer_connection(impresora)
        if conn is None:
            raise Exception("No se pudo conectar a la impresora")
        
        try:
            if isinstance(conn, socket.socket):
                conn.send(comando)
            elif isinstance(conn, serial.Serial):
                conn.write(comando)
            elif hasattr(conn, 'device'):  # ESC/POS
                conn._raw(comando)
            else:
                raise Exception("Tipo de conexión no soportado para comandos raw")
        finally:
            try:
                if hasattr(conn, 'close') and callable(getattr(conn, 'close')):
                    conn.close()
            except:
                pass
    
    @staticmethod
    def enviar_comando_raw_con_timeout(impresora, comando: bytes, timeout: int = 5) -> bool:
        """Envía comando raw con timeout"""
        try:
            # Crear socket con timeout si es red
            if impresora.tipo_conexion in ['LAN', 'WIFI', 'RAW']:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    s.connect((impresora.direccion_ip, impresora.puerto_red or 9100))
                    s.send(comando)
                return True
            else:
                # Para otros tipos, usar método normal
                PrinterService.enviar_comando_raw(impresora, comando)
                return True
        except Exception as e:
            logger.error(f"Error con timeout: {e}")
            return False


class TicketPrinter:
    """
    Servicio específico para impresión de tickets de venta
    """
    
    @staticmethod
    def imprimir_ticket(venta, impresora=None):
        """
        Imprime ticket de venta
        
        Args:
            venta: Modelo Venta
            impresora: Modelo Impresora (opcional, usa la principal si no se especifica)
        
        Returns:
            bool: True si fue exitoso
        """
        from ..models import Impresora, RegistroImpresion
        
        # Si no se especifica impresora, usar la principal
        if impresora is None:
            impresora = Impresora.objects.filter(
                es_principal_tickets=True,
                estado='ACTIVA'
            ).first()
            
            if not impresora:
                logger.error("No hay impresora de tickets configurada")
                return False
        
        inicio = time.time()
        
        try:
            conn = PrinterService.get_printer_connection(impresora)
            if conn is None:
                raise Exception("No se pudo conectar a la impresora")
            
            if impresora.protocolo == 'ESC_POS' and hasattr(conn, 'text'):
                # Imprimir con ESC/POS
                TicketPrinter._imprimir_ticket_escpos(conn, venta, impresora)
            else:
                # Imprimir con otro protocolo
                texto = TicketPrinter._generar_texto_ticket(venta)
                PrinterService._enviar_texto_generico(conn, texto)
            
            # Registrar impresión exitosa
            tiempo_ms = int((time.time() - inicio) * 1000)
            
            RegistroImpresion.objects.create(
                impresora=impresora,
                tipo_documento='TICKET',
                venta=venta,
                numero_documento=venta.numero_venta,
                contenido_resumen=f"Ticket de venta ${venta.total}",
                estado='EXITOSO',
                tiempo_procesamiento=tiempo_ms,
                usuario=venta.vendedor
            )
            
            # Incrementar contador
            impresora.incrementar_contador()
            
            return True
            
        except Exception as e:
            logger.error(f"Error al imprimir ticket: {str(e)}")
            
            # Registrar fallo
            RegistroImpresion.objects.create(
                impresora=impresora,
                tipo_documento='TICKET',
                venta=venta,
                numero_documento=venta.numero_venta,
                contenido_resumen=f"Ticket de venta ${venta.total}",
                estado='ERROR',
                mensaje_error=str(e),
                usuario=venta.vendedor
            )
            
            return False
        finally:
            try:
                if hasattr(conn, 'close') and callable(getattr(conn, 'close')):
                    conn.close()
            except:
                pass
    
    @staticmethod
    def _imprimir_ticket_escpos(conn, venta, impresora):
        """
        Imprime ticket usando comandos ESC/POS
        """
        # Usar valores por defecto si no existen en settings
        empresa_nombre = getattr(settings, 'EMPRESA_NOMBRE', 'COMMERCEBOX')
        empresa_ruc = getattr(settings, 'EMPRESA_RUC', 'RUC: 1234567890001')
        empresa_direccion = getattr(settings, 'EMPRESA_DIRECCION', 'Dirección de la empresa')
        empresa_telefono = getattr(settings, 'EMPRESA_TELEFONO', 'Teléfono')
        
        # Encabezado
        conn.set(align='center', text_type='B', width=2, height=2)
        conn.text(f"{empresa_nombre}\\n")
        conn.set(align='center', text_type='NORMAL')
        conn.text(f"{empresa_ruc}\\n")
        conn.text(f"{empresa_direccion}\\n")
        conn.text(f"Tel: {empresa_telefono}\\n")
        conn.text("=" * 42 + "\\n")
        
        # Datos de venta
        conn.set(align='left')
        conn.text(f"Ticket: {venta.numero_venta}\\n")
        conn.text(f"Fecha: {venta.fecha_venta.strftime('%d/%m/%Y %H:%M')}\\n")
        conn.text(f"Vendedor: {venta.vendedor.username}\\n")
        
        if venta.cliente:
            conn.text(f"Cliente: {venta.cliente.nombre_completo()}\\n")
            conn.text(f"Doc: {venta.cliente.numero_documento}\\n")
        
        conn.text("-" * 42 + "\\n")
        
        # Detalles
        conn.text("PRODUCTO               CANT    P.UNIT  TOTAL\\n")
        conn.text("-" * 42 + "\\n")
        
        for detalle in venta.detalles.all():
            # Nombre del producto (máx 20 caracteres)
            nombre = detalle.producto.nombre[:20].ljust(20)
            
            if detalle.producto.es_quintal():
                cant = f"{detalle.peso_vendido:.2f}"
                precio = f"{detalle.precio_por_unidad_peso:.2f}"
            else:
                cant = f"{detalle.cantidad_unidades}"
                precio = f"{detalle.precio_unitario:.2f}"
            
            total = f"{detalle.total:.2f}"
            
            linea = f"{nombre} {cant:>6} {precio:>8} {total:>8}\\n"
            conn.text(linea)
            
            # Si es quintal, mostrar código
            if detalle.quintal:
                conn.set(text_type='NORMAL', width=1, height=1)
                conn.text(f"  Quintal: {detalle.quintal.codigo_unico}\\n")
        
        conn.text("=" * 42 + "\\n")
        
        # Totales
        conn.set(align='right')
        conn.text(f"SUBTOTAL: ${venta.subtotal:>10.2f}\\n")
        if venta.descuento > 0:
            conn.text(f"DESCUENTO: -${venta.descuento:>9.2f}\\n")
        if venta.impuestos > 0:
            conn.text(f"IMPUESTOS: ${venta.impuestos:>10.2f}\\n")
        
        conn.set(text_type='B', width=2, height=2)
        conn.text(f"TOTAL: ${venta.total:>10.2f}\\n")
        
        conn.set(text_type='NORMAL', width=1, height=1)
        conn.text("=" * 42 + "\\n")
        
        # Pagos
        for pago in venta.pagos.all():
            conn.text(f"{pago.get_forma_pago_display()}: ${pago.monto:>10.2f}\\n")
        
        if venta.cambio > 0:
            conn.text(f"CAMBIO: ${venta.cambio:>10.2f}\\n")
        
        conn.text("=" * 42 + "\\n")
        
        # Pie
        conn.set(align='center')
        conn.text("GRACIAS POR SU COMPRA\\n")
        conn.text("\\n")
        
        # Código de barras o QR
        if impresora.soporta_codigo_barras:
            conn.barcode(venta.numero_venta, 'CODE128', 64, 2, '', '')
            conn.text("\\n")
        
        # Cortar
        if impresora.soporta_corte_automatico:
            if impresora.soporta_corte_parcial:
                conn.cut(mode='PART')
            else:
                conn.cut()
        
        # Abrir gaveta si está configurado
        if impresora.tiene_gaveta:
            conn.cashdraw(impresora.pin_gaveta or 0)
    
    @staticmethod
    def _generar_texto_ticket(venta):
        """
        Genera texto plano del ticket
        """
        lineas = []
        ancho = 42
        
        # Encabezado
        empresa_nombre = getattr(settings, 'EMPRESA_NOMBRE', 'COMMERCEBOX')
        empresa_ruc = getattr(settings, 'EMPRESA_RUC', 'RUC: 1234567890001')
        empresa_direccion = getattr(settings, 'EMPRESA_DIRECCION', 'Dirección de la empresa')
        empresa_telefono = getattr(settings, 'EMPRESA_TELEFONO', 'Teléfono')
        
        lineas.append(empresa_nombre.center(ancho))
        lineas.append(empresa_ruc.center(ancho))
        lineas.append(empresa_direccion.center(ancho))
        lineas.append(f"Tel: {empresa_telefono}".center(ancho))
        lineas.append("=" * ancho)
        
        # Datos de venta
        lineas.append(f"Ticket: {venta.numero_venta}")
        lineas.append(f"Fecha: {venta.fecha_venta.strftime('%d/%m/%Y %H:%M')}")
        lineas.append(f"Vendedor: {venta.vendedor.username}")
        
        if venta.cliente:
            lineas.append(f"Cliente: {venta.cliente.nombre_completo()}")
            lineas.append(f"Doc: {venta.cliente.numero_documento}")
        
        lineas.append("-" * ancho)
        
        # Detalles
        lineas.append("PRODUCTO               CANT    P.UNIT  TOTAL")
        lineas.append("-" * ancho)
        
        for detalle in venta.detalles.all():
            nombre = detalle.producto.nombre[:20].ljust(20)
            
            if detalle.producto.es_quintal():
                cant = f"{detalle.peso_vendido:.2f}"
                precio = f"{detalle.precio_por_unidad_peso:.2f}"
            else:
                cant = f"{detalle.cantidad_unidades}"
                precio = f"{detalle.precio_unitario:.2f}"
            
            total = f"{detalle.total:.2f}"
            
            linea = f"{nombre} {cant:>6} {precio:>8} {total:>8}"
            lineas.append(linea)
            
            if detalle.quintal:
                lineas.append(f"  Quintal: {detalle.quintal.codigo_unico}")
        
        lineas.append("=" * ancho)
        
        # Totales
        lineas.append(f"{'SUBTOTAL:':>30} ${venta.subtotal:>10.2f}")
        if venta.descuento > 0:
            lineas.append(f"{'DESCUENTO:':>30} -${venta.descuento:>9.2f}")
        if venta.impuestos > 0:
            lineas.append(f"{'IMPUESTOS:':>30} ${venta.impuestos:>10.2f}")
        lineas.append(f"{'TOTAL:':>30} ${venta.total:>10.2f}")
        
        lineas.append("=" * ancho)
        
        # Pagos
        for pago in venta.pagos.all():
            lineas.append(f"{pago.get_forma_pago_display():>30} ${pago.monto:>10.2f}")
        
        if venta.cambio > 0:
            lineas.append(f"{'CAMBIO:':>30} ${venta.cambio:>10.2f}")
        
        lineas.append("=" * ancho)
        lineas.append("GRACIAS POR SU COMPRA".center(ancho))
        lineas.append("")
        
        return "\\n".join(lineas)


class LabelPrinter:
    """
    Servicio para impresión de etiquetas y códigos de barras
    """
    
    @staticmethod
    def imprimir_etiqueta_producto(producto, cantidad=1, impresora=None, configuracion=None):
        """
        Imprime etiquetas de producto
        
        Args:
            producto: Modelo Producto
            cantidad: Número de etiquetas a imprimir
            impresora: Modelo Impresora (opcional)
            configuracion: Modelo ConfiguracionCodigoBarras (opcional)
        
        Returns:
            bool: True si fue exitoso
        """
        from ..models import Impresora, ConfiguracionCodigoBarras, RegistroImpresion
        
        # Obtener impresora si no se especifica
        if impresora is None:
            impresora = Impresora.objects.filter(
                es_principal_etiquetas=True,
                estado='ACTIVA',
                tipo_impresora='ETIQUETAS'
            ).first()
            
            if not impresora:
                logger.error("No hay impresora de etiquetas configurada")
                return False
        
        # Obtener configuración si no se especifica
        if configuracion is None:
            configuracion = ConfiguracionCodigoBarras.objects.filter(
                es_predeterminada=True,
                activa=True
            ).first()
            
            if not configuracion:
                logger.error("No hay configuración de códigos de barras")
                return False
        
        try:
            conn = PrinterService.get_printer_connection(impresora)
            if conn is None:
                raise Exception("No se pudo conectar a la impresora")
            
            # Según el protocolo de la impresora
            if impresora.protocolo == 'ZPL':
                LabelPrinter._imprimir_etiqueta_zpl(
                    conn, producto, cantidad, impresora, configuracion
                )
            elif impresora.protocolo == 'TSPL':
                LabelPrinter._imprimir_etiqueta_tspl(
                    conn, producto, cantidad, impresora, configuracion
                )
            elif impresora.protocolo == 'ESC_POS':
                LabelPrinter._imprimir_etiqueta_escpos(
                    conn, producto, cantidad, impresora, configuracion
                )
            else:
                raise ValueError(f"Protocolo no soportado: {impresora.protocolo}")
            
            # Registrar impresión
            RegistroImpresion.objects.create(
                impresora=impresora,
                tipo_documento='ETIQUETA',
                producto=producto,
                contenido_resumen=f"Etiqueta de {producto.nombre} x{cantidad}",
                estado='EXITOSO'
            )
            
            # Incrementar contador
            for _ in range(cantidad):
                impresora.incrementar_contador()
            
            return True
            
        except Exception as e:
            logger.error(f"Error al imprimir etiqueta: {str(e)}")
            
            RegistroImpresion.objects.create(
                impresora=impresora,
                tipo_documento='ETIQUETA',
                producto=producto,
                contenido_resumen=f"Etiqueta de {producto.nombre} x{cantidad}",
                estado='ERROR',
                mensaje_error=str(e)
            )
            
            return False
        finally:
            try:
                if hasattr(conn, 'close') and callable(getattr(conn, 'close')):
                    conn.close()
            except:
                pass
    
    @staticmethod
    def _imprimir_etiqueta_zpl(conn, producto, cantidad, impresora, config):
        """
        Imprime etiqueta usando ZPL (Zebra)
        """
        # Comandos ZPL para etiqueta
        zpl = []
        
        # Configuración inicial
        zpl.append("^XA")  # Inicio de formato
        zpl.append(f"^PW{impresora.ancho_etiqueta * 8}")  # Ancho de etiqueta (en dots)
        zpl.append(f"^LL{impresora.alto_etiqueta * 8}")  # Alto de etiqueta (en dots)
        
        # Nombre del producto
        if config.incluir_nombre_producto:
            zpl.append("^FO50,30")  # Posición
            zpl.append("^A0N,25,25")  # Fuente
            zpl.append(f"^FD{producto.nombre[:30]}^FS")
        
        # Marca
        if config.incluir_marca and producto.marca:
            zpl.append("^FO50,60")
            zpl.append("^A0N,20,20")
            zpl.append(f"^FD{producto.marca.nombre}^FS")
        
        # Código de barras
        zpl.append("^FO50,90")
        if config.tipo_codigo == 'CODE128':
            zpl.append("^BCN,70,Y,N,N")
        elif config.tipo_codigo == 'EAN13':
            zpl.append("^BEN,70,Y,N")
        zpl.append(f"^FD{producto.codigo_barras}^FS")
        
        # Precio
        if config.incluir_precio:
            precio = producto.precio_unitario if producto.es_normal() else producto.precio_por_unidad_peso
            zpl.append("^FO50,180")
            zpl.append("^A0N,35,35")
            zpl.append(f"^FD${precio:.2f}^FS")
        
        # Cantidad de copias
        zpl.append(f"^PQ{cantidad}")
        
        # Fin de formato
        zpl.append("^XZ")
        
        # Enviar comandos
        comando_completo = "\\n".join(zpl)
        
        if isinstance(conn, socket.socket):
            conn.send(comando_completo.encode())
        elif isinstance(conn, serial.Serial):
            conn.write(comando_completo.encode())
    
    @staticmethod
    def _imprimir_etiqueta_tspl(conn, producto, cantidad, impresora, config):
        """
        Imprime etiqueta usando TSPL (TSC)
        """
        # Comandos TSPL
        tspl = []
        
        # Configuración inicial
        tspl.append(f"SIZE {impresora.ancho_etiqueta} mm, {impresora.alto_etiqueta} mm")
        tspl.append(f"GAP {impresora.gap_etiquetas} mm, 0")
        tspl.append("CLS")
        
        # Nombre del producto
        if config.incluir_nombre_producto:
            tspl.append(f'TEXT 50,30,"2",0,1,1,"{producto.nombre[:30]}"')
        
        # Marca
        if config.incluir_marca and producto.marca:
            tspl.append(f'TEXT 50,60,"1",0,1,1,"{producto.marca.nombre}"')
        
        # Código de barras
        if config.tipo_codigo == 'CODE128':
            tspl.append(f"BARCODE 50,90,\"128\",70,1,0,2,2,\"{producto.codigo_barras}\"")
        elif config.tipo_codigo == 'EAN13':
            tspl.append(f"BARCODE 50,90,\"EAN13\",70,1,0,2,2,\"{producto.codigo_barras}\"")
        
        # Precio
        if config.incluir_precio:
            precio = producto.precio_unitario if producto.es_normal() else producto.precio_por_unidad_peso
            tspl.append(f'TEXT 50,180,"3",0,1,1,"${precio:.2f}"')
        
        # Imprimir
        tspl.append(f"PRINT {cantidad}")
        
        # Enviar comandos
        comando_completo = "\\n".join(tspl)
        
        if isinstance(conn, socket.socket):
            conn.send(comando_completo.encode())
        elif isinstance(conn, serial.Serial):
            conn.write(comando_completo.encode())
    
    @staticmethod
    def _imprimir_etiqueta_escpos(conn, producto, cantidad, impresora, config):
        """
        Imprime etiqueta usando ESC/POS
        """
        if not hasattr(conn, 'text'):
            raise ValueError("Conexión no compatible con ESC/POS")
        
        for i in range(cantidad):
            # Nombre del producto
            if config.incluir_nombre_producto:
                conn.set(align='center', text_type='B')
                conn.text(f"{producto.nombre[:30]}\\n")
            
            # Marca
            if config.incluir_marca and producto.marca:
                conn.set(align='center', text_type='NORMAL')
                conn.text(f"{producto.marca.nombre}\\n")
            
            # Código de barras
            conn.barcode(producto.codigo_barras, 'CODE128', 64, 2, '', '')
            
            # Precio
            if config.incluir_precio:
                precio = producto.precio_unitario if producto.es_normal() else producto.precio_por_unidad_peso
                conn.set(align='center', text_type='B', width=2)
                conn.text(f"${precio:.2f}\\n")
            
            conn.text("\\n\\n")
            
            # Cortar después de cada etiqueta
            if impresora.soporta_corte_automatico and i < cantidad - 1:
                conn.cut(mode='PART')
        
        # Corte final
        if impresora.soporta_corte_automatico:
            conn.cut()