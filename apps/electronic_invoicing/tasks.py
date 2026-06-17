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
            
            # Obtener el secuencial antes de incrementar
            secuencial_num = punto_emision.ultimo_secuencial + 1
            
            generator = XMLGeneratorSRI(config, punto_emision)
            xml_bruto, clave_acceso = generator.generar_xml_factura(venta)
            
            # Incrementar secuencial
            from django.db.models import F
            punto_emision.ultimo_secuencial = F('ultimo_secuencial') + 1
            punto_emision.save(update_fields=['ultimo_secuencial'])
            punto_emision.refresh_from_db()

            comprobante.clave_acceso = clave_acceso
            comprobante.xml_generado = xml_bruto.decode('utf-8')
            
            # Guardar el número de factura secuencial real en la venta
            venta.numero_factura = f"{punto_emision.establecimiento}-{punto_emision.punto_emision}-{secuencial_num:09d}"
            venta.save(update_fields=['numero_factura'])
            
            # 2. FIRMAR XML
            certificado = CertificadoDigital.objects.filter(activo=True).first()
            if not certificado:
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
            
            # Si ya existe la clave de acceso, asegurar que la venta tenga el número de factura
            if not venta.numero_factura:
                try:
                    if len(clave_acceso) >= 39:
                        venta.numero_factura = f"{clave_acceso[24:27]}-{clave_acceso[27:30]}-{clave_acceso[30:39]}"
                        venta.save(update_fields=['numero_factura'])
                except Exception as e:
                    logger.error(f"Error parsing clave_acceso for numero_factura: {e}")

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
                notificar_monitor(comprobante, "Recibido por SRI")
            else:
                comprobante.estado = 'RECHAZADO'
                error_detalles = extraer_errores_sri(respuesta_recepcion)
                comprobante.mensajes_error = f"Recepción SRI ({respuesta_recepcion.estado}): {error_detalles}"
                
                comprobante.save()
                notificar_monitor(comprobante, "Rechazo SRI")
                return False

        # 4. SOLICITAR AUTORIZACIÓN (Short Polling)
        if comprobante.estado == 'RECIBIDO':
            ambiente = config.ambiente
            url_autorizacion = config.wsdl_autorizacion_pruebas if ambiente == 1 else config.wsdl_autorizacion_produccion
            client_autorizacion = Client(url_autorizacion)
            import time
            max_intentos = 10
            delay_segundos = 5
            
            for intento_actual in range(1, max_intentos + 1):
                time.sleep(delay_segundos)
                
                try:
                    respuesta_aut = client_autorizacion.service.autorizacionComprobante(clave_acceso)
                    
                    if hasattr(respuesta_aut, 'autorizaciones') and respuesta_aut.autorizaciones and respuesta_aut.autorizaciones.autorizacion:
                        autorizacion = respuesta_aut.autorizaciones.autorizacion[0]
                        estado_sri = autorizacion.estado
                        
                        if estado_sri in ['AUTORIZADA', 'AUTORIZADO']:
                            comprobante.estado = 'AUTORIZADO'
                            comprobante.numero_autorizacion = autorizacion.numeroAutorizacion
                            comprobante.fecha_autorizacion = autorizacion.fechaAutorizacion
                            comprobante.xml_autorizado = autorizacion.comprobante  # Guardamos el XML oficial autorizado
                            comprobante.mensajes_error = None
                            comprobante.save()
                            
                            # Generar RIDE
                            try:
                                from .services.ride_generator import RIDEGenerator
                                ride_gen = RIDEGenerator(comprobante)
                                pdf_buffer = ride_gen.generar_pdf()
                                filename = f"RIDE_{comprobante.clave_acceso}.pdf"
                                comprobante.pdf_ride.save(filename, ContentFile(pdf_buffer.getvalue()), save=True)
                            except Exception as e:
                                logger.error(f"Error generando RIDE: {e}")

                            # ENVIAR POR EMAIL (Resend API)
                            try:
                                from .services.resend_service import ResendInvoicingService
                                ResendInvoicingService.enviar_comprobante(comprobante)
                            except Exception as e:
                                logger.error(f"Error al disparar envío por Resend: {e}")

                            notificar_monitor(comprobante, "¡Autorizado y Enviado!")
                            return True
                        
                        elif estado_sri in ['EN PROCESO', 'PENDIENTE'] or not estado_sri:
                            if intento_actual < max_intentos:
                                notificar_monitor(comprobante, f"SRI procesando ({intento_actual}/{max_intentos})")
                                continue
                            else:
                                comprobante.estado = 'ERROR'
                                comprobante.mensajes_error = "SRI indicó que sigue en proceso y nunca finalizó el comprobante."
                                comprobante.save()
                                notificar_monitor(comprobante, "SRI colapsado")
                                return False
                        else:
                            # RECHAZADA o NO AUTORIZADA
                            error_detalles = extraer_errores_sri(respuesta_aut)
                            comprobante.estado = 'RECHAZADO'
                            comprobante.mensajes_error = f"SRI {estado_sri}: {error_detalles}"
                            comprobante.save()
                            notificar_monitor(comprobante, "SRI Rechazado")
                            return False
                    else:
                        if intento_actual < max_intentos:
                            notificar_monitor(comprobante, f"Esperando SRI ({intento_actual}/{max_intentos})")
                            continue
                        else:
                            # Silencio total del SRI
                            comprobante.estado = 'RECHAZADO'
                            comprobante.mensajes_error = "Rechazo Silencioso del SRI. El documento no coincide con los estándares semánticos o RUC/Firma/Clave de Acceso irregulares."
                            comprobante.save()
                            notificar_monitor(comprobante, "SRI Rechazo Silencioso")
                            return False

                except Exception as e:
                    logger.error(f"Falla red autorización: {e}")
                    if intento_actual < max_intentos:
                        continue
                    else:
                        comprobante.estado = 'ERROR'
                        comprobante.mensajes_error = "Error red SRI."
                        comprobante.save()
                        return False

    except Exception as exc:
        if 'comprobante' in locals():
            comprobante.estado = 'ERROR'
            comprobante.mensajes_error = str(exc)
            comprobante.save()
            notificar_monitor(comprobante, f"Error: {exc}")
        return False
