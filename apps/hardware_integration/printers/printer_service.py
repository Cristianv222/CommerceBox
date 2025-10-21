# apps/hardware_integration/printers/printer_service.py

import socket
import serial
import usb.core
import usb.util
import subprocess
import time
import logging
import os
import platform
from typing import Optional, Tuple, Dict
from django.conf import settings
from django.utils import timezone
from escpos import printer as escpos_printer

# Intentar importar win32print solo si estamos en Windows
if platform.system() == 'Windows':
    try:
        import win32print
        import win32api
        WINDOWS_PRINTING_AVAILABLE = True
    except ImportError:
        WINDOWS_PRINTING_AVAILABLE = False
        logging.warning("pywin32 no está instalado. Algunas funciones no estarán disponibles.")
else:
    WINDOWS_PRINTING_AVAILABLE = False

logger = logging.getLogger(__name__)


class PrinterService:
    """
    Servicio unificado para manejo de impresoras
    Soporta múltiples tipos de conexión y protocolos
    
    SOLUCIONES IMPLEMENTADAS:
    1. Impresión directa con comandos ESC/POS optimizados
    2. Detección de impresoras en Windows
    3. API para agente local
    """
    
    # TIMEOUTS para operaciones
    CONNECTION_TIMEOUT = 5
    OPERATION_TIMEOUT = 10
    
    # ========================================================================
    # DETECCIÓN DE IMPRESORAS (WINDOWS)
    # ========================================================================
    
    @staticmethod
    def detectar_impresoras_sistema() -> list:
        """
        Detecta todas las impresoras instaladas en el sistema
        Solo funciona si se ejecuta en Windows
        
        Returns:
            list: Lista de diccionarios con info de impresoras
        """
        impresoras = []
        
        try:
            if platform.system() == 'Windows' and WINDOWS_PRINTING_AVAILABLE:
                # Listar impresoras en Windows
                flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                printers = win32print.EnumPrinters(flags)
                
                for printer in printers:
                    nombre = printer[2]  # Nombre de la impresora
                    
                    try:
                        # Obtener información del puerto
                        handle = win32print.OpenPrinter(nombre)
                        info = win32print.GetPrinter(handle, 2)
                        puerto = info.get('pPortName', '')
                        driver = info.get('pDriverName', '')
                        win32print.ClosePrinter(handle)
                        
                        impresoras.append({
                            'nombre': nombre,
                            'puerto': puerto,
                            'driver': driver,
                            'estado': 'Disponible'
                        })
                    except Exception as e:
                        logger.error(f"Error obteniendo info de {nombre}: {e}")
                        impresoras.append({
                            'nombre': nombre,
                            'puerto': 'Desconocido',
                            'driver': '',
                            'estado': 'Error'
                        })
            
            elif platform.system() == 'Linux':
                # Listar impresoras en Linux usando CUPS
                try:
                    import cups
                    conn = cups.Connection()
                    printers_dict = conn.getPrinters()
                    
                    for nombre, info in printers_dict.items():
                        impresoras.append({
                            'nombre': nombre,
                            'puerto': info.get('device-uri', ''),
                            'driver': info.get('printer-make-and-model', ''),
                            'estado': info.get('printer-state-message', 'Disponible')
                        })
                except Exception as e:
                    logger.error(f"Error en CUPS: {e}")
            else:
                logger.info("Detección de impresoras no disponible en este sistema")
        
        except Exception as e:
            logger.error(f"Error detectando impresoras: {e}")
        
        return impresoras
    
    @staticmethod
    def probar_puerto_usb_windows(nombre_impresora: str) -> Tuple[bool, str, Dict]:
        """
        Prueba si una impresora USB en Windows está accesible
        Solo funciona si se ejecuta en Windows con pywin32
        
        Args:
            nombre_impresora: Nombre del driver de Windows (ej: 'PrinterPOS-80')
        
        Returns:
            tuple: (success: bool, message: str, info: dict)
        """
        if platform.system() != 'Windows':
            return False, "Esta función solo funciona en Windows", {}
        
        if not WINDOWS_PRINTING_AVAILABLE:
            return False, "pywin32 no está instalado", {}
        
        try:
            # Intentar abrir la impresora
            handle = win32print.OpenPrinter(nombre_impresora)
            
            # Obtener información de la impresora
            info = win32print.GetPrinter(handle, 2)
            
            puerto = info.get('pPortName', 'Desconocido')
            driver = info.get('pDriverName', 'Desconocido')
            estado = info.get('Status', 0)
            
            # Cerrar el handle
            win32print.ClosePrinter(handle)
            
            info_dict = {
                'puerto': puerto,
                'driver': driver,
                'estado_codigo': estado,
                'estado_texto': 'Activa' if estado == 0 else 'Con problemas'
            }
            
            return True, f"✅ Impresora accesible en puerto {puerto}", info_dict
            
        except Exception as e:
            return False, f"❌ Error: {str(e)}", {}
    
    # ========================================================================
    # GENERACIÓN DE COMANDOS ESC/POS OPTIMIZADOS
    # ========================================================================
    
    @staticmethod
    def generar_comando_raw_test(impresora) -> bytes:
        """
        Genera comandos ESC/POS raw optimizados para papel térmico
        INCLUYE comando para abrir gaveta si está configurada
        
        Args:
            impresora: Modelo Impresora
        
        Returns:
            bytes: Comandos ESC/POS listos para enviar
        """
        empresa_nombre = getattr(settings, 'EMPRESA_NOMBRE', 'COMMERCEBOX')
        empresa_ruc = getattr(settings, 'EMPRESA_RUC', 'RUC: 1234567890001')
        
        comandos = b''
        
        # ESC @ - Inicializar impresora
        comandos += b'\x1B\x40'
        
        # ============================================
        # ENCABEZADO
        # ============================================
        
        # ESC a 1 - Centrar
        comandos += b'\x1B\x61\x01'
        
        # ESC ! - Texto doble tamaño (ancho y alto)
        comandos += b'\x1B\x21\x30'
        comandos += empresa_nombre.encode('utf-8') + b'\n'
        
        # ESC ! - Texto normal
        comandos += b'\x1B\x21\x00'
        comandos += empresa_ruc.encode('utf-8') + b'\n'
        
        # ESC ! - Negrita
        comandos += b'\x1B\x21\x08'
        comandos += b'PAGINA DE PRUEBA\n'
        
        # ESC ! - Texto normal
        comandos += b'\x1B\x21\x00'
        
        # Línea separadora
        comandos += b'================================\n'
        
        # ============================================
        # INFORMACIÓN DE IMPRESORA
        # ============================================
        
        # ESC a 0 - Alinear izquierda
        comandos += b'\x1B\x61\x00'
        
        # Título de sección centrado
        comandos += b'\x1B\x61\x01'
        comandos += b'\x1B\x21\x08'  # Negrita
        comandos += b'INFORMACION DE IMPRESORA\n'
        comandos += b'\x1B\x21\x00'  # Normal
        
        # Línea sólida
        comandos += b'================================\n'
        
        # ESC a 0 - Alinear izquierda
        comandos += b'\x1B\x61\x00'
        
        # Información (formato: label: valor)
        def agregar_linea(label, valor):
            ancho_total = 48
            label_con_espacios = f"{label}:"
            espacios_necesarios = ancho_total - len(label_con_espacios) - len(str(valor))
            if espacios_necesarios < 1:
                espacios_necesarios = 1
            return f"{label_con_espacios}{' ' * espacios_necesarios}{valor}\n".encode('utf-8')
        
        comandos += agregar_linea("Nombre", impresora.nombre)
        comandos += agregar_linea("Marca", impresora.marca)
        comandos += agregar_linea("Modelo", impresora.modelo)
        comandos += agregar_linea("Conexion", impresora.get_tipo_conexion_display())
        comandos += agregar_linea("Protocolo", impresora.get_protocolo_display())
        
        if impresora.puerto_usb:
            comandos += agregar_linea("Puerto", impresora.puerto_usb)
        
        if impresora.nombre_driver:
            comandos += agregar_linea("Driver", impresora.nombre_driver)
        
        if impresora.direccion_ip:
            comandos += agregar_linea("IP", f"{impresora.direccion_ip}:{impresora.puerto_red}")
        
        # 🔥 MOSTRAR ESTADO DE GAVETA
        if impresora.tiene_gaveta:
            comandos += agregar_linea("Gaveta", "SI - Se abrira")
        else:
            comandos += agregar_linea("Gaveta", "NO configurada")
        
        # Línea separadora
        comandos += b'--------------------------------\n'
        
        # Fecha y hora
        fecha_actual = timezone.now()
        comandos += agregar_linea("Fecha", fecha_actual.strftime('%d/%m/%Y'))
        comandos += agregar_linea("Hora", fecha_actual.strftime('%H:%M:%S'))
        
        # Línea separadora
        comandos += b'================================\n'
        
        # ============================================
        # CÓDIGO DE BARRAS (si soporta)
        # ============================================
        
        if impresora.soporta_codigo_barras:
            # Centrar
            comandos += b'\x1B\x61\x01'
            comandos += b'CODIGO DE BARRAS:\n'
            
            # GS k - Imprimir código de barras
            codigo = f"TEST{impresora.codigo}"
            comandos += b'\x1D\x6B\x49'  # GS k 73 (CODE128)
            comandos += bytes([len(codigo)])  # Longitud
            comandos += codigo.encode('utf-8')
            comandos += b'\x00'  # NUL
            comandos += b'\n'
        
        # ============================================
        # TEXTO GRANDE
        # ============================================
        
        # Centrar
        comandos += b'\x1B\x61\x01'
        comandos += b'\n'
        
        # ESC ! - Texto doble tamaño + negrita
        comandos += b'\x1B\x21\x38'
        comandos += b'PRUEBA EXITOSA\n'
        
        # ESC ! - Texto normal
        comandos += b'\x1B\x21\x00'
        
        # Línea separadora
        comandos += b'================================\n'
        
        # ============================================
        # PIE DE PÁGINA
        # ============================================
        
        # Centrar
        comandos += b'\x1B\x61\x01'
        comandos += b'\n'
        comandos += b'CommerceBox - Sistema POS\n'
        comandos += b'www.commercebox.com\n'
        
        # Espacios antes del corte
        comandos += b'\n\n\n\n'
        
        # ============================================
        # CORTAR PAPEL
        # ============================================
        
        if impresora.soporta_corte_automatico:
            if impresora.soporta_corte_parcial:
                # GS V - Corte parcial
                comandos += b'\x1D\x56\x01'
            else:
                # GS V - Corte completo
                comandos += b'\x1D\x56\x00'
        else:
            # Si no tiene corte, agregar más líneas en blanco
            comandos += b'\n\n\n\n\n\n'
        
        # ============================================
        # 🔥🔥🔥 ABRIR GAVETA (SIEMPRE AL FINAL) 🔥🔥🔥
        # ============================================
        
        if impresora.tiene_gaveta:
            logger.info("🔓 AGREGANDO COMANDO PARA ABRIR GAVETA")
            
            # ESC p - Pulso a gaveta
            # Formato: ESC p m t1 t2
            # m = pin (0 o 1)
            # t1 = tiempo ON en unidades de 2ms
            # t2 = tiempo OFF en unidades de 2ms
            
            pin = impresora.pin_gaveta if impresora.pin_gaveta is not None else 0
            
            # Comando: ESC p pin 50 50
            # 50 * 2ms = 100ms ON, 100ms OFF
            comandos += b'\x1B\x70'  # ESC p
            comandos += bytes([pin])  # Pin (0 o 1)
            comandos += b'\x32'  # 50 decimal = 0x32
            comandos += b'\x32'  # 50 decimal = 0x32
            
            logger.info(f"   Pin: {pin}")
            logger.info(f"   Comando: ESC p {pin} 50 50 (hex: 1B 70 {pin:02X} 32 32)")
        else:
            logger.info("⚠️ Gaveta NO configurada - no se agregará comando")
        
        return comandos
    
    # ========================================================================
    # IMPRESIÓN DIRECTA EN WINDOWS
    # ========================================================================
    
    @staticmethod
    def imprimir_raw_windows(nombre_impresora: str, comandos: bytes) -> Tuple[bool, str]:
        """
        Envía comandos raw directamente a impresora en Windows
        
        Args:
            nombre_impresora: Nombre del driver (ej: 'PrinterPOS-80')
            comandos: Bytes con comandos ESC/POS
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if platform.system() != 'Windows':
            return False, "Esta función solo funciona en Windows"
        
        if not WINDOWS_PRINTING_AVAILABLE:
            return False, "pywin32 no está instalado"
        
        try:
            logger.info(f"🖨️ Enviando {len(comandos)} bytes a {nombre_impresora}")
            
            # Abrir impresora
            handle = win32print.OpenPrinter(nombre_impresora)
            
            try:
                # Iniciar trabajo de impresión RAW
                job_info = ("CommerceBox Print", None, "RAW")
                job_id = win32print.StartDocPrinter(handle, 1, job_info)
                
                # Iniciar página
                win32print.StartPagePrinter(handle)
                
                # Enviar comandos
                bytes_written = win32print.WritePrinter(handle, comandos)
                
                # Finalizar
                win32print.EndPagePrinter(handle)
                win32print.EndDocPrinter(handle)
                
                logger.info(f"✅ Enviados {bytes_written} bytes correctamente")
                
                return True, f"✅ Impresión exitosa ({bytes_written} bytes)"
                
            finally:
                win32print.ClosePrinter(handle)
                
        except Exception as e:
            error_msg = f"Error al imprimir: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, f"❌ {error_msg}"
    
    # ========================================================================
    # VALIDACIÓN DE CONFIGURACIÓN (CLOUD)
    # ========================================================================
    
    @staticmethod
    def test_connection_cloud(impresora) -> Tuple[bool, str]:
        """
        Prueba de conexión que funciona desde Docker/Cloud
        Solo valida la configuración, no la conexión física
        
        Args:
            impresora: Modelo Impresora
        
        Returns:
            tuple: (success: bool, message: str)
        """
        errores = []
        warnings = []
        
        # Validar configuración según tipo de conexión
        if impresora.tipo_conexion == 'USB':
            if not impresora.puerto_usb and not impresora.nombre_driver:
                errores.append("Falta configurar puerto USB o nombre del driver")
            else:
                warnings.append(f"Puerto USB configurado: {impresora.puerto_usb or impresora.nombre_driver}")
        
        elif impresora.tipo_conexion in ['LAN', 'WIFI']:
            if not impresora.direccion_ip:
                errores.append("Falta configurar dirección IP")
            if not impresora.puerto_red:
                errores.append("Falta configurar puerto de red")
            else:
                # Intentar hacer ping a la IP
                try:
                    cmd = ['ping', '-c', '1', '-W', '2', impresora.direccion_ip] if platform.system() != 'Windows' else ['ping', '-n', '1', '-w', '2000', impresora.direccion_ip]
                    resultado = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=3
                    )
                    if resultado.returncode == 0:
                        return True, f"✅ Configuración correcta. IP {impresora.direccion_ip} responde a ping"
                    else:
                        warnings.append(f"IP {impresora.direccion_ip} no responde a ping")
                except Exception as e:
                    warnings.append(f"No se pudo verificar conectividad: {str(e)}")
        
        elif impresora.tipo_conexion == 'SERIAL':
            if not impresora.puerto_serial:
                errores.append("Falta configurar puerto serial")
            if not impresora.baudrate:
                errores.append("Falta configurar baudrate")
        
        elif impresora.tipo_conexion == 'DRIVER':
            if not impresora.nombre_driver:
                errores.append("Falta configurar nombre del driver")
        
        # Validaciones generales
        if not impresora.nombre:
            errores.append("Falta el nombre de la impresora")
        
        if not impresora.protocolo:
            errores.append("Falta seleccionar el protocolo")
        
        if errores:
            return False, "❌ Errores de configuración:\n" + "\n".join(f"• {e}" for e in errores)
        
        mensaje = "✅ Configuración correcta"
        if warnings:
            mensaje += "\n\n⚠️ Advertencias:\n" + "\n".join(f"• {w}" for w in warnings)
        
        mensaje += "\n\n💡 Para imprimir, use el botón 'Imprimir Directo' o configure el agente local"
        
        return True, mensaje
    
    # ========================================================================
    # PRUEBA DE CONEXIÓN UNIFICADA
    # ========================================================================
    
    @staticmethod
    def test_connection(impresora) -> Tuple[bool, str]:
        """
        Prueba la conexión con la impresora
        Usa el método apropiado según el entorno de ejecución
        
        Returns:
            tuple: (success: bool, message: str)
        """
        # Si estamos en cloud/docker, usar validación de configuración
        if not WINDOWS_PRINTING_AVAILABLE and impresora.tipo_conexion in ['USB', 'DRIVER']:
            return PrinterService.test_connection_cloud(impresora)
        
        # Si tenemos acceso a Windows y es impresora con driver
        if WINDOWS_PRINTING_AVAILABLE and impresora.nombre_driver and impresora.tipo_conexion in ['USB', 'DRIVER']:
            success, msg, info = PrinterService.probar_puerto_usb_windows(impresora.nombre_driver)
            return success, msg
        
        # Para impresoras de red, intentar conexión directa
        if impresora.tipo_conexion in ['LAN', 'WIFI', 'RAW']:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(PrinterService.CONNECTION_TIMEOUT)
                s.connect((impresora.direccion_ip, impresora.puerto_red or 9100))
                s.close()
                return True, "✅ Conexión de red exitosa"
            except Exception as e:
                return False, f"❌ Error: {str(e)}"
        
        # Fallback a validación de configuración
        return PrinterService.test_connection_cloud(impresora)
    
    # ========================================================================
    # IMPRESIÓN DE PÁGINA DE PRUEBA
    # ========================================================================
    
    @staticmethod
    def print_test_page(impresora, usar_agente=True) -> bool:
        """
        Imprime una página de prueba usando el método más apropiado
        
        PARA DOCKER: Por defecto usa el agente local (usar_agente=True)
        ya que Docker no puede acceder directamente a impresoras Windows
        
        Args:
            impresora: Instancia del modelo Impresora
            usar_agente: Si True, crea trabajo para el agente local (recomendado para Docker)
        
        Returns:
            bool: True si el trabajo fue creado/enviado exitosamente, False en caso contrario
        """
        from ..models import RegistroImpresion
        from ..api.agente_views import crear_trabajo_impresion, obtener_usuario_para_impresion
        from django.conf import settings
        
        inicio = time.time()
        
        try:
            # ===========================================================
            # PASO 1: GENERAR COMANDOS ESC/POS
            # ===========================================================
            
            logger.info(f"🖨️ Iniciando impresión de prueba para: {impresora.nombre}")
            logger.info(f"   Gaveta configurada: {'✅ Sí' if impresora.tiene_gaveta else '❌ No'}")
            
            # Generar comandos ESC/POS para la página de prueba
            # Los comandos YA incluyen el pulso de gaveta si está configurada
            comandos = PrinterService.generar_comando_raw_test(impresora)
            
            # Convertir bytes a hexadecimal para transmisión
            comandos_hex = comandos.hex()
            
            logger.debug(f"   Comandos generados: {len(comandos)} bytes ({len(comandos_hex)} chars hex)")
            
            # ===========================================================
            # PASO 2: MÉTODO PREFERIDO - USAR AGENTE LOCAL
            # ===========================================================
            
            if usar_agente:
                try:
                    logger.info(f"📍 Método seleccionado: Agente Local")
                    
                    # Verificar que la impresora tenga nombre de driver configurado
                    if not impresora.nombre_driver:
                        raise Exception(
                            "⚠️ La impresora no tiene configurado el 'Nombre del Driver'.\n\n"
                            "SOLUCIÓN:\n"
                            "1. Ve a la configuración de la impresora en Django Admin\n"
                            "2. En el agente de Windows, ve a la pestaña 'Impresoras'\n"
                            "3. Copia el nombre EXACTO de la impresora\n"
                            "4. Pégalo en el campo 'Nombre del Driver' en Django\n"
                            "5. Guarda los cambios\n\n"
                            "Ejemplo: 'PrinterPOS-80' o 'POS-80 Printer'"
                        )
                    
                    # Obtener usuario para crear el trabajo
                    try:
                        usuario = obtener_usuario_para_impresion()
                        logger.debug(f"   Usuario asignado: {usuario.username} (ID:{usuario.id})")
                    except Exception as e:
                        raise Exception(f"No se pudo obtener un usuario válido: {str(e)}")
                    
                    # Crear trabajo de impresión
                    trabajo_id = crear_trabajo_impresion(
                        usuario=usuario,
                        impresora_nombre=impresora.nombre_driver,
                        comandos_hex=comandos_hex,
                        tipo='PRUEBA'
                    )
                    
                    logger.info(f"✅ Trabajo #{trabajo_id} creado exitosamente")
                    logger.info(f"   El agente lo procesará automáticamente en los próximos 3 segundos")
                    
                    # Registrar en base de datos como trabajo enviado
                    tiempo_ms = int((time.time() - inicio) * 1000)
                    RegistroImpresion.objects.create(
                        impresora=impresora,
                        tipo_documento='OTRO',
                        numero_documento=trabajo_id[:100],
                        contenido_resumen=f'Página de prueba enviada al agente (ID: {trabajo_id})',
                        estado='EXITOSO',
                        tiempo_procesamiento=tiempo_ms,
                        usuario=usuario
                    )
                    
                    # Actualizar fecha de última prueba
                    impresora.fecha_ultima_prueba = timezone.now()
                    impresora.save(update_fields=['fecha_ultima_prueba'])
                    
                    logger.info(
                        f"📋 INSTRUCCIONES:\n"
                        f"   1. Abre el agente en Windows\n"
                        f"   2. Ve a la pestaña 'Log'\n"
                        f"   3. En 3-5 segundos verás el trabajo procesándose\n"
                        f"   4. La impresora imprimirá automáticamente\n"
                        f"   5. {'✅ La gaveta se abrirá automáticamente' if impresora.tiene_gaveta else '⚠️ La gaveta NO se abrirá (no configurada)'}"
                    )
                    
                    return True
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"⚠️ No se pudo usar el agente: {error_msg}")
                    
                    # Si explícitamente se pidió usar agente, no continuar con métodos directos
                    if usar_agente:
                        logger.info("💡 SOLUCIONES:")
                        logger.info("   1. ✅ RECOMENDADO: Verifica que el agente esté ejecutándose:")
                        logger.info("      - Abre CommerceBox-Agente.exe en Windows")
                        logger.info("      - Verifica estado: '🟢 Ejecutando'")
                        logger.info("      - Verifica configuración (URL y Token correctos)")
                        logger.info("   2. Configura el 'Nombre del Driver' en la impresora")
                        logger.info("   3. O usa una impresora de red (configura IP y puerto)")
                        
                        # Re-lanzar la excepción para que el admin vea el error
                        raise Exception(
                            f"{error_msg}\n\n"
                            "RECOMENDACIÓN: Asegúrate de que el agente local esté ejecutándose en Windows.\n"
                            "Si el agente está corriendo, verifica que el 'Nombre del Driver' esté configurado correctamente."
                        )
            
            # ===========================================================
            # PASO 3: MÉTODOS ALTERNATIVOS (FALLBACK)
            # ===========================================================
            
            success = False
            mensaje = ""
            
            logger.info("📍 Intentando métodos de impresión directa...")
            
            # MÉTODO ALTERNATIVO 1: Impresión directa Windows (si disponible)
            if WINDOWS_PRINTING_AVAILABLE and impresora.nombre_driver:
                logger.info(f"   Probando: Impresión directa Windows")
                logger.info(f"   Driver: {impresora.nombre_driver}")
                
                try:
                    success, mensaje = PrinterService.imprimir_raw_windows(
                        impresora.nombre_driver, 
                        comandos
                    )
                    if success:
                        logger.info(f"   ✅ Impresión Windows exitosa")
                except Exception as e:
                    logger.warning(f"   ❌ Falló impresión Windows: {e}")
                    mensaje = str(e)
            
            # MÉTODO ALTERNATIVO 2: Impresora de Red
            elif impresora.tipo_conexion in ['LAN', 'WIFI', 'RAW'] and impresora.direccion_ip:
                logger.info(f"   Probando: Impresión por red")
                logger.info(f"   IP: {impresora.direccion_ip}:{impresora.puerto_red or 9100}")
                
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(5)
                        s.connect((impresora.direccion_ip, impresora.puerto_red or 9100))
                        s.sendall(comandos)
                        success = True
                        mensaje = "Impresión por red exitosa"
                        logger.info(f"   ✅ {mensaje}")
                except Exception as e:
                    success = False
                    mensaje = f"Error de red: {str(e)}"
                    logger.warning(f"   ❌ {mensaje}")
            
            else:
                # No hay métodos disponibles
                raise Exception(
                    "⚠️ No se pudo imprimir con ningún método disponible.\n\n"
                    "TU SITUACIÓN:\n"
                    f"- Sistema: {'Docker/Linux' if not WINDOWS_PRINTING_AVAILABLE else 'Windows'}\n"
                    f"- Nombre driver configurado: {'✅ Sí' if impresora.nombre_driver else '❌ No'}\n"
                    f"- Tipo conexión: {impresora.tipo_conexion}\n"
                    f"- IP configurada: {'✅ ' + impresora.direccion_ip if impresora.direccion_ip else '❌ No'}\n\n"
                    "SOLUCIONES:\n"
                    "1. ✅ RECOMENDADO (especialmente para Docker):\n"
                    "   - Asegúrate de que el agente local esté ejecutándose en Windows\n"
                    "   - Verifica: Estado '🟢 Ejecutando' en el agente\n"
                    "   - Configura el 'Nombre del Driver' de la impresora\n"
                    "   - URL del agente debe apuntar a este servidor\n\n"
                    "2. O configura una impresora de red:\n"
                    "   - Tipo conexión: LAN/WIFI/RAW\n"
                    "   - Dirección IP y puerto de la impresora\n\n"
                    "3. O ejecuta Django directamente en Windows (no en Docker)"
                )
            
            # Verificar resultado
            if not success:
                raise Exception(mensaje or "Impresión fallida sin mensaje de error")
            
            # ===========================================================
            # PASO 4: REGISTRAR RESULTADO EXITOSO
            # ===========================================================
            
            tiempo_ms = int((time.time() - inicio) * 1000)
            
            # Obtener usuario para el registro (si es método directo)
            try:
                usuario_registro = obtener_usuario_para_impresion()
            except:
                usuario_registro = None
            
            RegistroImpresion.objects.create(
                impresora=impresora,
                tipo_documento='OTRO',
                numero_documento='TEST-PAGE-DIRECT',
                contenido_resumen='Página de prueba (impresión directa)',
                estado='EXITOSO',
                tiempo_procesamiento=tiempo_ms,
                usuario=usuario_registro
            )
            
            impresora.fecha_ultima_prueba = timezone.now()
            impresora.save(update_fields=['fecha_ultima_prueba'])
            
            logger.info(f"✅ {mensaje} (tiempo: {tiempo_ms}ms)")
            return True
            
        except Exception as e:
            # ===========================================================
            # MANEJO DE ERRORES
            # ===========================================================
            
            error_msg = str(e)
            logger.error(f"❌ Error al imprimir página de prueba: {error_msg}")
            
            # Obtener usuario para el registro de error
            try:
                usuario_registro = obtener_usuario_para_impresion()
            except:
                usuario_registro = None
            
            # Registrar error en base de datos
            RegistroImpresion.objects.create(
                impresora=impresora,
                tipo_documento='OTRO',
                numero_documento='TEST-PAGE-ERROR',
                contenido_resumen='Intento de página de prueba',
                estado='ERROR',
                mensaje_error=error_msg[:500],
                usuario=usuario_registro
            )
            
            # Mostrar información útil para debugging
            logger.error("🔍 INFORMACIÓN DE DEBUGGING:")
            logger.error(f"   Impresora: {impresora.nombre}")
            logger.error(f"   Nombre driver: {impresora.nombre_driver or '(no configurado)'}")
            logger.error(f"   Tipo conexión: {impresora.tipo_conexion}")
            logger.error(f"   En Windows: {WINDOWS_PRINTING_AVAILABLE}")
            logger.error(f"   Usar agente: {usar_agente}")
            
            return False
    
    # ========================================================================
    # ENVÍO DE COMANDOS RAW CON TIMEOUT
    # ========================================================================
    
    @staticmethod
    def enviar_comando_raw_con_timeout(impresora, comando: bytes, timeout: int = 5) -> bool:
        """
        Envía comando raw con timeout
        Usado principalmente para abrir gavetas
        """
        try:
            # Si es Windows con driver
            if WINDOWS_PRINTING_AVAILABLE and impresora.nombre_driver:
                success, msg = PrinterService.imprimir_raw_windows(impresora.nombre_driver, comando)
                return success
            
            # Si es red
            elif impresora.tipo_conexion in ['LAN', 'WIFI', 'RAW']:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    s.connect((impresora.direccion_ip, impresora.puerto_red or 9100))
                    s.send(comando)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error con timeout: {e}")
            return False