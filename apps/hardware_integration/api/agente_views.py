# apps/hardware_integration/api/agente_views.py

from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import BaseThrottle
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from ..models import Impresora, RegistroImpresion, TrabajoImpresion
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# THROTTLING PERSONALIZADO - SIN LÍMITE PARA EL AGENTE
# ============================================================================

class NoThrottle(BaseThrottle):
    """
    Clase de throttling que NO limita las peticiones del agente.
    El agente necesita consultar cada 3 segundos sin restricciones.
    """
    def allow_request(self, request, view):
        return True
    
    def wait(self):
        return None


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def normalizar_nombre_impresora(nombre_solicitado):
    """
    Normaliza el nombre de la impresora para que coincida con el sistema Windows.
    """
    try:
        nombre_solicitado = nombre_solicitado.strip()
        
        # Buscar en BD
        impresoras_bd = Impresora.objects.filter(activa='ACTIVA').values_list('nombre', 'nombre_driver')
        
        # Coincidencia exacta
        for nombre_bd, driver_bd in impresoras_bd:
            if nombre_solicitado == driver_bd or nombre_solicitado == nombre_bd:
                logger.debug(f"✅ Impresora encontrada: '{nombre_solicitado}' → '{driver_bd}'")
                return driver_bd if driver_bd else nombre_bd
        
        # Coincidencia parcial
        nombre_lower = nombre_solicitado.lower()
        for nombre_bd, driver_bd in impresoras_bd:
            nombre_comparar = (driver_bd if driver_bd else nombre_bd).lower()
            if nombre_lower in nombre_comparar or nombre_comparar in nombre_lower:
                nombre_encontrado = driver_bd if driver_bd else nombre_bd
                logger.info(f"📝 Nombre normalizado: '{nombre_solicitado}' → '{nombre_encontrado}'")
                return nombre_encontrado
        
        logger.warning(f"⚠️ Impresora '{nombre_solicitado}' no encontrada en BD")
        return nombre_solicitado
        
    except Exception as e:
        logger.error(f"❌ Error normalizando nombre: {e}")
        return nombre_solicitado


def obtener_usuario_para_impresion():
    """
    Obtiene un usuario válido para crear trabajos de impresión
    """
    try:
        Usuario = settings.AUTH_USER_MODEL
        from django.apps import apps
        UsuarioModel = apps.get_model(Usuario)
        
        # Intentar obtener superusuario
        usuario = UsuarioModel.objects.filter(is_superuser=True, is_active=True).first()
        if usuario:
            return usuario
        
        # Intentar obtener staff
        usuario = UsuarioModel.objects.filter(is_staff=True, is_active=True).first()
        if usuario:
            return usuario
        
        # Cualquier usuario activo
        usuario = UsuarioModel.objects.filter(is_active=True).first()
        if usuario:
            return usuario
        
        raise Exception("No hay usuarios activos en el sistema")
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo usuario: {e}")
        raise


# ============================================================================
# VISTAS API - SISTEMA CON BASE DE DATOS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([NoThrottle])
def registrar_agente(request):
    """
    Endpoint para registrar un agente local con el servidor
    
    POST /api/hardware/agente/registrar/
    """
    try:
        data = request.data
        computadora = data.get('computadora', 'Unknown')
        usuario_pc = data.get('usuario', 'Unknown')
        version_agente = data.get('version_agente', '0.0.0')
        impresoras = data.get('impresoras', [])
        
        logger.info(f"📝 Agente registrado: {computadora} - {usuario_pc} (v{version_agente})")
        logger.info(f"   Usuario Django: {request.user.username} (ID: {request.user.id})")
        logger.info(f"   Impresoras detectadas: {len(impresoras)}")
        
        if impresoras:
            for idx, imp in enumerate(impresoras, 1):
                logger.info(f"      {idx}. {imp.get('nombre', 'Sin nombre')} - {imp.get('driver', 'Sin driver')}")
        
        # Guardar info en cache (para estado)
        cache_key = f"agente_{request.user.id}_{computadora}"
        agente_info = {
            'computadora': computadora,
            'usuario_pc': usuario_pc,
            'usuario_django': request.user.username,
            'usuario_id': request.user.id,
            'version': version_agente,
            'impresoras': impresoras,
            'ultima_conexion': timezone.now().isoformat(),
            'estado': 'ACTIVO'
        }
        cache.set(cache_key, agente_info, 3600)
        
        return Response({
            'success': True,
            'mensaje': 'Agente registrado correctamente',
            'server_time': timezone.now().isoformat(),
            'usuario': request.user.username,
            'usuario_id': request.user.id,
            'impresoras_registradas': len(impresoras)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Error registrando agente: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e),
            'mensaje': 'Error al registrar el agente'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([NoThrottle])
def obtener_trabajos_pendientes(request):
    """
    Endpoint para obtener trabajos de impresión pendientes
    
    GET /api/hardware/agente/trabajos/
    
    ⚠️ CRÍTICO: Ahora usa TrabajoImpresion de la BASE DE DATOS
    """
    try:
        # 🔥 CAMBIO PRINCIPAL: Obtener desde BD en lugar de cache
        trabajos_query = TrabajoImpresion.objects.filter(
            estado='PENDIENTE',
            creado_por=request.user  # Solo trabajos de este usuario
        ).select_related('impresora', 'venta', 'producto').order_by(
            'prioridad',
            'fecha_creacion'
        )[:10]  # Máximo 10 por petición
        
        trabajos_list = []
        
        for trabajo in trabajos_query:
            # Normalizar nombre de impresora
            if trabajo.impresora and trabajo.impresora.nombre_driver:
                nombre_impresora = trabajo.impresora.nombre_driver
            elif trabajo.impresora:
                nombre_impresora = trabajo.impresora.nombre
            else:
                # Si no tiene impresora asignada, buscar la predeterminada
                impresora_default = Impresora.objects.filter(
                    es_principal_tickets=True,
                    activa='ACTIVA'
                ).first()
                nombre_impresora = impresora_default.nombre_driver if impresora_default else "PrinterPOS-80"
            
            nombre_normalizado = normalizar_nombre_impresora(nombre_impresora)
            
            trabajos_list.append({
                'id': str(trabajo.id),
                'impresora': nombre_normalizado,
                'comandos': trabajo.datos_impresion,  # Ya está en formato hex
                'tipo': trabajo.tipo,
                'prioridad': trabajo.prioridad,
                'fecha_creacion': trabajo.fecha_creacion.isoformat(),
                'copias': trabajo.copias,
                'abrir_gaveta': trabajo.abrir_gaveta,
            })
            
            # 🔥 Marcar como EN PROCESO
            trabajo.marcar_procesando()
            
            logger.info(f"📤 Trabajo {trabajo.id} enviado al agente")
            logger.info(f"   Impresora: {nombre_normalizado}")
            logger.info(f"   Tipo: {trabajo.tipo}")
        
        if trabajos_list:
            logger.info(f"📋 Usuario {request.user.username} - Enviados: {len(trabajos_list)} trabajos")
        else:
            logger.debug(f"📋 Usuario {request.user.username} - Sin trabajos pendientes")
        
        return Response({
            'trabajos': trabajos_list,
            'count': len(trabajos_list),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo trabajos: {e}", exc_info=True)
        return Response({
            'trabajos': [],
            'count': 0,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([NoThrottle])
def reportar_resultado(request):
    """
    Endpoint para que el agente reporte el resultado de una impresión
    
    POST /api/hardware/agente/resultado/
    
    ⚠️ CRÍTICO: Ahora busca en BD en lugar de cache
    """
    try:
        data = request.data
        trabajo_id = data.get('trabajo_id')
        success = data.get('success', False)
        mensaje = data.get('mensaje', 'Sin mensaje')
        detalles = data.get('detalles', {})
        tiempo_ms = detalles.get('tiempo_impresion')
        
        if not trabajo_id:
            logger.warning("⚠️ Intento de reportar resultado sin trabajo_id")
            return Response({
                'success': False,
                'error': 'trabajo_id es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"📊 Resultado trabajo {trabajo_id}: {'✅ ÉXITO' if success else '❌ ERROR'}")
        logger.info(f"   Mensaje: {mensaje}")
        logger.info(f"   Usuario: {request.user.username}")
        
        # 🔥 CAMBIO PRINCIPAL: Buscar en BD
        try:
            trabajo = TrabajoImpresion.objects.get(id=trabajo_id)
            
            if success:
                # Marcar como completado
                trabajo.marcar_completado(tiempo_ms=int(tiempo_ms * 1000) if tiempo_ms else None)
                logger.info(f"   ✅ Trabajo completado exitosamente")
            else:
                # Marcar con error
                trabajo.marcar_error(mensaje)
                logger.warning(f"   ❌ Trabajo marcado con error")
            
            return Response({
                'success': True,
                'mensaje': 'Resultado registrado correctamente'
            }, status=status.HTTP_200_OK)
            
        except TrabajoImpresion.DoesNotExist:
            logger.warning(f"⚠️ Trabajo {trabajo_id} no encontrado en BD")
            return Response({
                'success': False,
                'error': 'Trabajo no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"❌ Error reportando resultado: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e),
            'mensaje': 'Error al registrar el resultado'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([NoThrottle])
def actualizar_estado_trabajo(request, trabajo_id):
    """
    Endpoint para que el agente actualice el estado de un trabajo
    
    POST /api/hardware/agente/trabajos/<trabajo_id>/estado/
    
    Body:
    {
        "estado": "COMPLETADO",  // COMPLETADO, ERROR, PROCESANDO
        "mensaje_error": "Error al conectar con impresora",
        "tiempo_procesamiento": 1500  // en ms
    }
    """
    try:
        trabajo = TrabajoImpresion.objects.get(id=trabajo_id)
        
        estado = request.data.get('estado')
        mensaje_error = request.data.get('mensaje_error', '')
        tiempo_ms = request.data.get('tiempo_procesamiento')
        
        if estado == 'COMPLETADO':
            trabajo.marcar_completado(tiempo_ms)
            logger.info(f"✅ Trabajo {trabajo_id} completado")
        elif estado == 'ERROR':
            trabajo.marcar_error(mensaje_error)
            logger.error(f"❌ Trabajo {trabajo_id} con error: {mensaje_error}")
        elif estado == 'PROCESANDO':
            trabajo.marcar_procesando()
            logger.info(f"⚙️ Trabajo {trabajo_id} en proceso")
        
        return Response({
            'success': True,
            'trabajo_id': str(trabajo.id),
            'estado': trabajo.estado
        })
        
    except TrabajoImpresion.DoesNotExist:
        logger.warning(f"⚠️ Trabajo {trabajo_id} no encontrado")
        return Response({
            'success': False,
            'error': 'Trabajo no encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"❌ Error actualizando trabajo: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([NoThrottle])
def obtener_estado_agente(request):
    """
    Endpoint para verificar el estado del agente y sus trabajos
    
    GET /api/hardware/agente/estado/
    """
    try:
        # Buscar info del agente en cache
        agente_info = None
        for computadora in ['Unknown', 'PC-CAJA-01', 'PC-CAJA-02']:
            cache_key = f"agente_{request.user.id}_{computadora}"
            agente_info = cache.get(cache_key)
            if agente_info:
                break
        
        # 🔥 Contar trabajos desde BD
        trabajos_pendientes = TrabajoImpresion.objects.filter(
            creado_por=request.user,
            estado='PENDIENTE'
        ).count()
        
        trabajos_en_proceso = TrabajoImpresion.objects.filter(
            creado_por=request.user,
            estado='PROCESANDO'
        ).count()
        
        total_en_cola = trabajos_pendientes + trabajos_en_proceso
        
        return Response({
            'agente_registrado': agente_info is not None,
            'trabajos_pendientes': trabajos_pendientes,
            'trabajos_en_proceso': trabajos_en_proceso,
            'total_en_cola': total_en_cola,
            'ultima_conexion': agente_info.get('ultima_conexion') if agente_info else None,
            'version_agente': agente_info.get('version') if agente_info else None,
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# FUNCIONES AUXILIARES PARA CREAR TRABAJOS (COMPATIBILIDAD)
# ============================================================================

def crear_trabajo_impresion(usuario, impresora_nombre, comandos_hex, tipo='ticket', prioridad=1, abrir_gaveta=None):
    """
    Crea un trabajo de impresión en la BD para que el agente lo procese
    
    🔥 ACTUALIZADO: Ahora crea registros en TrabajoImpresion (BD)
    
    Args:
        usuario: Instancia del modelo de Usuario
        impresora_nombre: Nombre del driver de la impresora
        comandos_hex: Comandos ESC/POS en formato hexadecimal
        tipo: Tipo de documento (ticket, factura, test, etc)
        prioridad: 1=Alta, 2=Media, 3=Baja
        abrir_gaveta: True/False o None (None = detectar automáticamente)
    
    Returns:
        str: ID del trabajo creado
    """
    try:
        # Buscar impresora por nombre de driver
        impresora = Impresora.objects.filter(
            nombre_driver__iexact=impresora_nombre
        ).first()
        
        # Si no se encuentra, buscar por nombre
        if not impresora:
            impresora = Impresora.objects.filter(
                nombre__icontains=impresora_nombre[:50],
                activa='ACTIVA'
            ).first()
        
        # Si aún no se encuentra, usar la predeterminada
        if not impresora:
            impresora = Impresora.objects.filter(
                es_principal_tickets=True,
                activa='ACTIVA'
            ).first()
        
        if not impresora:
            raise Exception(f"No se encontró ninguna impresora activa con el nombre '{impresora_nombre}'")
        
        # Validar comandos
        if not comandos_hex or len(comandos_hex) < 10:
            raise ValueError("Los comandos de impresión están vacíos o son demasiado cortos")
        
        # 🔥 DETECTAR SI DEBE ABRIR GAVETA
        # Si abrir_gaveta no se especificó, detectar automáticamente
        if abrir_gaveta is None:
            # Verificar si la impresora tiene gaveta configurada
            abrir_gaveta = impresora.tiene_gaveta
            
            # O buscar si hay una gaveta asociada a esta impresora
            if not abrir_gaveta:
                from ..models import GavetaDinero
                gaveta = GavetaDinero.objects.filter(
                    impresora=impresora,
                    activa='ACTIVA'
                ).first()
                abrir_gaveta = gaveta is not None
        
        # 🔥 CREAR EN BASE DE DATOS
        trabajo = TrabajoImpresion.objects.create(
            tipo=tipo.upper(),
            prioridad=prioridad,
            estado='PENDIENTE',
            impresora=impresora,
            datos_impresion=comandos_hex,
            formato='ESC_POS',
            creado_por=usuario,
            copias=1,
            abrir_gaveta=abrir_gaveta,  # 🔥 Ahora respeta la configuración
            max_intentos=3
        )
        
        logger.info(f"📄 Trabajo de impresión creado: {trabajo.id}")
        logger.info(f"   Usuario: {usuario.username} (ID:{usuario.id})")
        logger.info(f"   Impresora: {impresora.nombre} (Driver: {impresora.nombre_driver})")
        logger.info(f"   Tipo: {tipo}")
        logger.info(f"   Prioridad: {prioridad}")
        logger.info(f"   Abrir gaveta: {'✅ Sí' if abrir_gaveta else '❌ No'}")
        logger.info(f"   Tamaño comandos: {len(comandos_hex)} caracteres")
        
        return str(trabajo.id)
        
    except Exception as e:
        logger.error(f"❌ Error creando trabajo: {e}", exc_info=True)
        raise


def cancelar_trabajo_impresion(usuario, trabajo_id):
    """
    Cancela un trabajo de impresión pendiente
    
    🔥 ACTUALIZADO: Ahora busca en BD
    """
    try:
        trabajo = TrabajoImpresion.objects.get(
            id=trabajo_id,
            creado_por=usuario
        )
        
        if trabajo.estado != 'PENDIENTE':
            logger.warning(f"⚠️ Intento de cancelar trabajo en estado {trabajo.estado}")
            return False
        
        trabajo.cancelar()
        logger.info(f"🚫 Trabajo {trabajo_id} cancelado por {usuario.username}")
        return True
        
    except TrabajoImpresion.DoesNotExist:
        logger.warning(f"⚠️ Trabajo {trabajo_id} no encontrado")
        return False
    except Exception as e:
        logger.error(f"❌ Error cancelando trabajo: {e}", exc_info=True)
        return False
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def imprimir_codigo_barras(request):
    """
    Imprime un código de barras en una impresora de etiquetas
    
    POST /api/hardware/codigos-barras/imprimir/
    
    Body:
    {
        "codigo": "7501234567890",
        "tipo": "EAN13",  // EAN13, CODE128, CODE39, etc.
        "impresora_id": "uuid",  // opcional
        "altura": 100,  // opcional
        "ancho": 2,  // opcional
        "texto_posicion": "BELOW"  // opcional
    }
    """
    try:
        from ..printers.printer_service import PrinterService
        
        # Obtener datos
        codigo = request.data.get('codigo')
        tipo = request.data.get('tipo', 'CODE128')
        impresora_id = request.data.get('impresora_id')
        altura = request.data.get('altura', 100)
        ancho = request.data.get('ancho', 2)
        texto_posicion = request.data.get('texto_posicion', 'BELOW')
        
        # Validar código
        if not codigo:
            return Response({
                'success': False,
                'error': 'El código es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener impresora
        if impresora_id:
            try:
                impresora = Impresora.objects.get(id=impresora_id, activa='ACTIVA')
            except Impresora.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Impresora no encontrada'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Buscar impresora de etiquetas predeterminada
            impresora = Impresora.objects.filter(
                tipo_impresora='ETIQUETAS',
                es_principal_etiquetas=True,
                activa='ACTIVA'
            ).first()
            
            if not impresora:
                impresora = Impresora.objects.filter(
                    tipo_impresora='ETIQUETAS',
                    activa='ACTIVA'
                ).first()
        
        if not impresora:
            return Response({
                'success': False,
                'error': 'No hay impresoras de etiquetas configuradas'
            }, status=status.HTTP_404_NOT_FOUND)
        
        logger.info(f"🏷️ Imprimiendo código de barras: {codigo}")
        logger.info(f"   Tipo: {tipo}")
        logger.info(f"   Impresora: {impresora.nombre}")
        
        # Generar comandos ESC/POS
        comandos = PrinterService.generar_codigo_barras(
            codigo=codigo,
            tipo=tipo,
            altura=altura,
            ancho=ancho,
            texto_posicion=texto_posicion,
            centrar=True
        )
        
        if not comandos:
            return Response({
                'success': False,
                'error': f'No se pudieron generar comandos para el código. Verifica que sea válido para tipo {tipo}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Agregar saltos y corte
        comandos += b'\n\n\n'
        comandos += b'\x1D\x56\x00'
        
        # Convertir a hexadecimal
        comandos_hex = comandos.hex()
        
        # Crear trabajo de impresión
        trabajo_id = crear_trabajo_impresion(
            usuario=request.user,
            impresora_nombre=impresora.nombre_driver or impresora.nombre,
            comandos_hex=comandos_hex,
            tipo='CODIGO_BARRAS',
            prioridad=2,
            abrir_gaveta=False
        )
        
        logger.info(f"✅ Trabajo de impresión creado: {trabajo_id}")
        
        return Response({
            'success': True,
            'mensaje': 'Código de barras enviado a imprimir',
            'trabajo_id': trabajo_id,
            'impresora': impresora.nombre,
            'codigo': codigo,
            'tipo': tipo
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"❌ Error imprimiendo código: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def imprimir_etiqueta_producto(request):
    """
    Imprime una etiqueta completa de producto con código de barras
    
    POST /api/hardware/codigos-barras/etiqueta/
    
    Body:
    {
        "producto_codigo": "PROD-001",
        "producto_nombre": "Producto de Prueba",
        "precio": 99.99,
        "tipo_codigo": "CODE128",  // opcional
        "impresora_id": "uuid",  // opcional
        "copias": 1  // opcional
    }
    """
    try:
        from ..printers.printer_service import PrinterService
        
        # Obtener datos
        producto_codigo = request.data.get('producto_codigo')
        producto_nombre = request.data.get('producto_nombre')
        precio = request.data.get('precio')
        tipo_codigo = request.data.get('tipo_codigo', 'CODE128')
        impresora_id = request.data.get('impresora_id')
        copias = request.data.get('copias', 1)
        
        # Validar datos
        if not all([producto_codigo, producto_nombre, precio is not None]):
            return Response({
                'success': False,
                'error': 'Faltan datos: producto_codigo, producto_nombre, precio'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convertir precio
        try:
            precio = float(precio)
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'error': 'El precio debe ser un número válido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener impresora
        if impresora_id:
            try:
                impresora = Impresora.objects.get(id=impresora_id, activa='ACTIVA')
            except Impresora.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Impresora no encontrada'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            impresora = Impresora.objects.filter(
                tipo_impresora='ETIQUETAS',
                es_principal_etiquetas=True,
                activa='ACTIVA'
            ).first()
            
            if not impresora:
                impresora = Impresora.objects.filter(
                    tipo_impresora='ETIQUETAS',
                    activa='ACTIVA'
                ).first()
        
        if not impresora:
            return Response({
                'success': False,
                'error': 'No hay impresoras de etiquetas configuradas'
            }, status=status.HTTP_404_NOT_FOUND)
        
        logger.info(f"🏷️ Imprimiendo etiqueta: {producto_nombre}")
        logger.info(f"   Código: {producto_codigo}")
        logger.info(f"   Precio: ${precio:.2f}")
        logger.info(f"   Copias: {copias}")
        
        # Generar etiqueta
        comandos = PrinterService.generar_etiqueta_producto(
            producto_codigo=producto_codigo,
            producto_nombre=producto_nombre,
            precio=precio,
            tipo_codigo=tipo_codigo,
            incluir_moneda=True
        )
        
        # Convertir a hexadecimal
        comandos_hex = comandos.hex()
        
        # Crear trabajo de impresión
        trabajo_id = crear_trabajo_impresion(
            usuario=request.user,
            impresora_nombre=impresora.nombre_driver or impresora.nombre,
            comandos_hex=comandos_hex,
            tipo='ETIQUETA',
            prioridad=2,
            abrir_gaveta=False
        )
        
        # Actualizar copias si es necesario
        if copias > 1:
            trabajo = TrabajoImpresion.objects.get(id=trabajo_id)
            trabajo.copias = copias
            trabajo.save(update_fields=['copias'])
        
        logger.info(f"✅ Trabajo creado: {trabajo_id}")
        
        return Response({
            'success': True,
            'mensaje': 'Etiqueta enviada a imprimir',
            'trabajo_id': trabajo_id,
            'impresora': impresora.nombre,
            'producto': producto_nombre,
            'copias': copias
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"❌ Error imprimiendo etiqueta: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def imprimir_prueba_codigos(request):
    """
    Imprime una página de prueba con varios códigos de barras
    
    POST /api/hardware/codigos-barras/prueba/
    
    Body:
    {
        "impresora_id": "uuid"  // opcional
    }
    """
    try:
        from ..printers.printer_service import PrinterService
        
        impresora_id = request.data.get('impresora_id')
        
        # Obtener impresora
        if impresora_id:
            try:
                impresora = Impresora.objects.get(id=impresora_id, activa='ACTIVA')
            except Impresora.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Impresora no encontrada'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            impresora = Impresora.objects.filter(
                tipo_impresora='ETIQUETAS',
                es_principal_etiquetas=True,
                activa='ACTIVA'
            ).first()
            
            if not impresora:
                impresora = Impresora.objects.filter(
                    tipo_impresora='ETIQUETAS',
                    activa='ACTIVA'
                ).first()
        
        if not impresora:
            return Response({
                'success': False,
                'error': 'No hay impresoras configuradas'
            }, status=status.HTTP_404_NOT_FOUND)
        
        logger.info(f"🧪 Imprimiendo página de prueba")
        logger.info(f"   Impresora: {impresora.nombre}")
        
        # Generar página de prueba
        comandos = PrinterService.generar_pagina_prueba_codigos()
        
        # Convertir a hexadecimal
        comandos_hex = comandos.hex()
        
        # Crear trabajo
        trabajo_id = crear_trabajo_impresion(
            usuario=request.user,
            impresora_nombre=impresora.nombre_driver or impresora.nombre,
            comandos_hex=comandos_hex,
            tipo='PRUEBA',
            prioridad=1,
            abrir_gaveta=False
        )
        
        logger.info(f"✅ Trabajo creado: {trabajo_id}")
        
        return Response({
            'success': True,
            'mensaje': 'Página de prueba enviada',
            'trabajo_id': trabajo_id,
            'impresora': impresora.nombre
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)