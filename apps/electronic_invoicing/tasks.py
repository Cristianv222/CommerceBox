import logging
from celery import shared_task
from django.utils import timezone
from .models import ComprobanteElectronico, SRIConfig, PuntoEmision, CertificadoDigital
from .services.xml_generator import XMLGeneratorSRI
from .services.signature import SignatureServiceSRI
from zeep import Client
from zeep.transports import Transport
import requests

import base64
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

def notificar_monitor(comprobante, mensaje=None):
    """Auxiliar para notificar al WebSocket monitor"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "sri_monitor",
        {
            "type": "sri_status_update",
            "comprobante_id": str(comprobante.id),
            "venta_numero": comprobante.venta.numero_venta,
            "estado": comprobante.estado,
            "clave_acceso": comprobante.clave_acceso,
            "numero_autorizacion": comprobante.numero_autorizacion,
            "mensaje": mensaje,
            "mensajes_error": comprobante.mensajes_error,
            "email_enviado": comprobante.email_enviado,
            "error_email": comprobante.error_email,
        }
    )

def to_list(obj):
    if obj is None: return []
    if isinstance(obj, list): return obj
    return [obj]

import zeep.helpers

def extraer_errores_sri_recursivo(data, errores):
    if isinstance(data, dict):
        # Zeep dictionaries often have their data nested, so we check for 'mensaje' or 'informacionAdicional' globally
        if 'mensaje' in data and data['mensaje'] and isinstance(data['mensaje'], str):
            ident = data.get('identificador', '?')
            msg = data.get('mensaje', '')
            info = data.get('informacionAdicional', '')
            err = f"[{ident}] {msg}"
            if info: err += f" - Detalles: {info}"
            errores.append(err)
        for val in data.values():
            extraer_errores_sri_recursivo(val, errores)
    elif isinstance(data, list):
        for item in data:
            extraer_errores_sri_recursivo(item, errores)

def extraer_errores_sri(respuesta):
    errores = []
    try:
        dict_resp = zeep.helpers.serialize_object(respuesta)
        extraer_errores_sri_recursivo(dict_resp, errores)
    except Exception as e:
        logger.error(f"Error parseando estructura SRI con serialize: {e}")
        # Intentar anexarlo crudo si falla serialize
        errores.append("Error crudo: " + str(respuesta))
        
    return " | ".join(errores) if errores else ("Rechazado sin detalle (Suele ser por firma electrónica o clave no válida para RUC). " + str(respuesta))


def es_error_secuencial_registrado(mensaje):
    """
    Detecta si el SRI rechazó porque el secuencial / clave de acceso YA está
    registrado en sus servidores (códigos 43 y 45). En ese caso el contador local
    quedó atrás del SRI y hay que avanzar al siguiente número, no reutilizar el actual.
    """
    if not mensaje:
        return False
    m = str(mensaje).upper()
    return (
        'CLAVE ACCESO REGISTRADA' in m
        or 'SECUENCIAL REGISTRADO' in m
        or '[43]' in m
        or '[45]' in m
    )

@shared_task
def procesar_factura_electronica(comprobante_id):
    """
    Tarea asíncrona para procesar una factura completa ante el SRI con reintentos asíncronos.
    """
    try:
        comprobante = ComprobanteElectronico.objects.get(pk=comprobante_id)
        venta = comprobante.venta
        config = SRIConfig.objects.first()
        punto_emision = PuntoEmision.objects.filter(activo=True).first()
        
        if not config or not punto_emision:
            comprobante.estado = 'ERROR'
            comprobante.mensajes_error = "Configuración SRI o Punto de Emisión no encontrados."
            comprobante.save()
            return

        # 1. GENERAR XML (Solo si no existe clave de acceso aún)
        if not comprobante.clave_acceso:
            comprobante.estado = 'GENERADO'
            comprobante.save()
            notificar_monitor(comprobante, "XML Generado")
            
            # Obtener el secuencial actual disponible sin incrementarlo aún en la BD
            secuencial_num = punto_emision.ultimo_secuencial + 1
            
            generator = XMLGeneratorSRI(config, punto_emision)
            xml_bruto, clave_acceso = generator.generar_xml_factura(venta, secuencial_num=secuencial_num)
            
            comprobante.clave_acceso = clave_acceso
            comprobante.xml_generado = xml_bruto.decode('utf-8')
            comprobante.save()
            
            # 2. FIRMAR XML
            certificado = CertificadoDigital.objects.filter(activo=True).first()
            if not certificado:
                # No incrementamos secuencial si falla la firma
                raise ValueError("No hay certificado digital (firma) activo.")
                
            signer = SignatureServiceSRI(certificado)
            xml_firmado_bytes = signer.firmar_xml(xml_bruto)
            
            # Corregir error de conversión bytes -> str en la DB
            xml_firmado_str = xml_firmado_bytes.decode('utf-8') if isinstance(xml_firmado_bytes, bytes) else xml_firmado_bytes
            
            comprobante.xml_firmado = xml_firmado_str
            comprobante.estado = 'FIRMADO'
            comprobante.save()
            notificar_monitor(comprobante, "XML Firmado")
        else:
            xml_firmado_str = comprobante.xml_firmado
            clave_acceso = comprobante.clave_acceso
            try:
                secuencial_num = int(clave_acceso[30:39])
            except Exception:
                secuencial_num = punto_emision.ultimo_secuencial + 1

        # 3. ENVIAR AL SRI (RECEPCIÓN) - Si no ha sido recibido aún
        if comprobante.estado != 'RECIBIDO' and comprobante.estado != 'AUTORIZADO':
            ambiente = config.ambiente
            url_recepcion = config.wsdl_recepcion_pruebas if ambiente == 1 else config.wsdl_recepcion_produccion
            client_recepcion = Client(url_recepcion)
            
            # Limpiar cualquier residuo de b'' en la DB si el registro era viejo
            if xml_firmado_str.startswith("b'") or xml_firmado_str.startswith('b"'):
                import ast
                try:
                    xml_firmado_str = ast.literal_eval(xml_firmado_str).decode('utf-8')
                    comprobante.xml_firmado = xml_firmado_str
                    comprobante.save()
                except:
                    pass
                    
            # CRITICAL FIX: DO NOT manually base64 encode! Zeep expects raw bytes 
            # for 'base64Binary' WSDL fields and encodes them automatically.
            xml_raw_bytes = xml_firmado_str.encode('utf-8')
            
            try:
                respuesta_recepcion = client_recepcion.service.validarComprobante(xml_raw_bytes)
            except Exception as e:
                logger.error(f"Error de conexión con SRI (Recepción): {e}")
                comprobante.estado = 'ERROR'
                comprobante.mensajes_error = f"No hay conexión con SRI: {str(e)}"
                comprobante.save()
                notificar_monitor(comprobante, "Fallo red SRI")
                return False

            if respuesta_recepcion.estado == 'RECIBIDA':
                comprobante.estado = 'RECIBIDO'
                comprobante.save()

                # ✅ EL SRI YA RESERVÓ/REGISTRÓ ESTE SECUENCIAL al recibir el documento.
                # Confirmamos el contador AHORA (no al autorizar). Así, aunque el polling
                # de autorización dé timeout, el contador nunca se queda atrás del SRI y
                # la próxima factura usa un número nuevo (evita el bloqueo por error 43/45).
                if 'secuencial_num' in locals() and secuencial_num:
                    if punto_emision.ultimo_secuencial < secuencial_num:
                        punto_emision.ultimo_secuencial = secuencial_num
                        punto_emision.save(update_fields=['ultimo_secuencial'])
                        punto_emision.refresh_from_db()

                notificar_monitor(comprobante, "Recibido por SRI")
            else:
                comprobante.estado = 'RECHAZADO'
                error_detalles = extraer_errores_sri(respuesta_recepcion)
                comprobante.mensajes_error = f"Recepción SRI ({respuesta_recepcion.estado}): {error_detalles}"

                # Si el SRI dice que el secuencial/clave YA está registrado (43/45), el
                # contador local quedó atrás: avanzamos para que el reintento use un número
                # nuevo y no se trabe en bucle. En cualquier otro rechazo de recepción el
                # documento NO quedó recibido, así que el número sigue libre para reusarse.
                if es_error_secuencial_registrado(error_detalles):
                    if 'secuencial_num' in locals() and secuencial_num and punto_emision.ultimo_secuencial < secuencial_num:
                        punto_emision.ultimo_secuencial = secuencial_num
                        punto_emision.save(update_fields=['ultimo_secuencial'])
                        punto_emision.refresh_from_db()

                # Reseteamos la clave para que el reintento regenere el XML (con número
                # nuevo si avanzamos, o con el mismo número si fue un rechazo limpio).
                comprobante.clave_acceso = None
                comprobante.save()
                notificar_monitor(comprobante, "Rechazo SRI")
                return False

        # 4. SOLICITAR AUTORIZACIÓN (DESACOPLADO)
        # Ya no bloqueamos el worker esperando al SRI. Encolamos una tarea aparte que
        # consulta la autorización y se auto-reprograma mientras el SRI siga "en proceso".
        # Apenas el SRI responde, esa tarea empuja el estado por WebSocket (tiempo real).
        if comprobante.estado == 'RECIBIDO':
            # Primer chequeo rápido (~2s) para que la autorización llegue casi al instante.
            consultar_autorizacion_sri.apply_async(args=[str(comprobante.id)], countdown=2)
            return True

    except Exception as exc:
        if 'comprobante' in locals():
            comprobante.estado = 'ERROR'
            comprobante.mensajes_error = str(exc)
            comprobante.save()
            notificar_monitor(comprobante, f"Error: {exc}")
        return False


# Backoff de reprogramación de la consulta de autorización (segundos por intento).
# Primer chequeo muy rápido y luego creciente: casi en tiempo real cuando el SRI
# responde pronto, y tolerante cuando el SRI está lento, sin bloquear ningún worker.
BACKOFF_AUTORIZACION = [2, 3, 5, 5, 8, 8, 10, 15, 15, 20, 30, 30, 40, 60]
MAX_INTENTOS_AUTORIZACION = len(BACKOFF_AUTORIZACION)


@shared_task
def consultar_autorizacion_sri(comprobante_id, intento=1):
    """
    Consulta la autorización de un comprobante YA RECIBIDO por el SRI.

    Hace UNA consulta y, si el SRI sigue "en proceso" o no responde, se auto-reprograma
    con backoff creciente (vía Redis, sin bloquear el worker). Apenas el SRI resuelve,
    empuja el estado por WebSocket. El contador del secuencial ya fue confirmado al
    momento de RECIBIR el documento, así que aquí solo se finaliza (número de factura,
    RIDE y email) o se marca el rechazo.
    """
    def reprogramar(comprobante, mensaje):
        """Reencola la consulta con backoff; si se agotan los intentos, deja el
        comprobante en RECIBIDO con nota (sigue en el SRI, recuperable al reintentar)."""
        if intento < MAX_INTENTOS_AUTORIZACION:
            notificar_monitor(comprobante, f"{mensaje} ({intento}/{MAX_INTENTOS_AUTORIZACION})")
            consultar_autorizacion_sri.apply_async(
                args=[str(comprobante_id), intento + 1],
                countdown=BACKOFF_AUTORIZACION[intento - 1],
            )
            return None
        # El documento sigue RECIBIDO en el SRI (no es rechazo). Lo dejamos así, con nota,
        # para que un 'Reintentar' vuelva a consultar y lo recupere cuando el SRI finalice.
        comprobante.mensajes_error = (
            "El SRI aún no finaliza la autorización. El documento fue recibido y sigue en "
            "proceso; use 'Reintentar' para volver a consultar su estado."
        )
        comprobante.save(update_fields=['mensajes_error'])
        notificar_monitor(comprobante, "SRI en proceso (reintentar)")
        return False

    try:
        comprobante = ComprobanteElectronico.objects.get(pk=comprobante_id)
    except ComprobanteElectronico.DoesNotExist:
        return False

    try:
        # Si ya se resolvió por otra vía, no hacemos nada.
        if comprobante.estado == 'AUTORIZADO':
            return True
        if not comprobante.clave_acceso:
            # Sin clave no hay nada que consultar (se reseteó para reemisión).
            return False

        venta = comprobante.venta
        config = SRIConfig.objects.first()
        punto_emision = comprobante.punto_emision or PuntoEmision.objects.filter(activo=True).first()
        clave_acceso = comprobante.clave_acceso
        try:
            secuencial_num = int(clave_acceso[30:39])
        except Exception:
            secuencial_num = None

        ambiente = config.ambiente
        url_autorizacion = config.wsdl_autorizacion_pruebas if ambiente == 1 else config.wsdl_autorizacion_produccion

        try:
            client_autorizacion = Client(url_autorizacion)
            respuesta_aut = client_autorizacion.service.autorizacionComprobante(clave_acceso)
        except Exception as e:
            logger.error(f"Falla red autorización (intento {intento}): {e}")
            return reprogramar(comprobante, "Reintentando conexión SRI")

        tiene_aut = (
            hasattr(respuesta_aut, 'autorizaciones')
            and respuesta_aut.autorizaciones
            and respuesta_aut.autorizaciones.autorizacion
        )
        if not tiene_aut:
            # El SRI todavía no tiene resultado: reconsultar.
            return reprogramar(comprobante, "Esperando SRI")

        autorizacion = respuesta_aut.autorizaciones.autorizacion[0]
        estado_sri = autorizacion.estado

        if estado_sri in ['AUTORIZADA', 'AUTORIZADO']:
            comprobante.estado = 'AUTORIZADO'
            comprobante.numero_autorizacion = autorizacion.numeroAutorizacion
            comprobante.fecha_autorizacion = autorizacion.fechaAutorizacion
            comprobante.xml_autorizado = autorizacion.comprobante  # XML oficial autorizado
            comprobante.mensajes_error = None
            comprobante.save()

            # El contador ya se confirmó en RECIBIDA; aquí solo aseguramos el número y
            # asignamos el número de factura fiscal a la venta.
            if secuencial_num and punto_emision:
                if punto_emision.ultimo_secuencial < secuencial_num:
                    punto_emision.ultimo_secuencial = secuencial_num
                    punto_emision.save(update_fields=['ultimo_secuencial'])
                venta.numero_factura = f"{punto_emision.establecimiento}-{punto_emision.punto_emision}-{secuencial_num:09d}"
                venta.save(update_fields=['numero_factura'])

            # Generar RIDE
            try:
                from .services.ride_generator import RIDEGenerator
                ride_gen = RIDEGenerator(comprobante)
                pdf_buffer = ride_gen.generar_pdf()
                filename = f"RIDE_{comprobante.clave_acceso}.pdf"
                comprobante.pdf_ride.save(filename, ContentFile(pdf_buffer.getvalue()), save=True)
            except Exception as e:
                logger.error(f"Error generando RIDE: {e}")

            # Enviar por email (Resend API)
            try:
                from .services.resend_service import ResendInvoicingService
                ResendInvoicingService.enviar_comprobante(comprobante)
            except Exception as e:
                logger.error(f"Error al disparar envío por Resend: {e}")

            notificar_monitor(comprobante, "¡Autorizado y Enviado!")
            return True

        elif estado_sri in ['EN PROCESO', 'PENDIENTE'] or not estado_sri:
            return reprogramar(comprobante, "SRI procesando")

        else:
            # RECHAZADA / NO AUTORIZADA: el documento SÍ fue recibido, el secuencial ya se
            # consumió. Reseteamos la clave para que un reintento emita una factura NUEVA
            # corregida con el SIGUIENTE número (no se reutiliza el rechazado).
            error_detalles = extraer_errores_sri(respuesta_aut)
            comprobante.estado = 'RECHAZADO'
            comprobante.mensajes_error = f"SRI {estado_sri}: {error_detalles}"
            comprobante.clave_acceso = None
            comprobante.save()
            notificar_monitor(comprobante, "SRI Rechazado")
            return False

    except Exception as exc:
        logger.error(f"Error en consultar_autorizacion_sri: {exc}")
        try:
            comprobante.estado = 'ERROR'
            comprobante.mensajes_error = str(exc)
            comprobante.save()
            notificar_monitor(comprobante, f"Error: {exc}")
        except Exception:
            pass
        return False
