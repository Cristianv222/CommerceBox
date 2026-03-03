import requests
import logging
from django.conf import settings
from django.utils import timezone
from .models import SRIConfig, SRILog
from decimal import Decimal

logger = logging.getLogger(__name__)

class APIVendoService:
    """Servicio de integración con APIVendo para facturación electrónica del SRI"""
    
    # Mapeo de tipos de identificación SRI
    IDENTIFICATION_MAP = {
        'RUC': '04',
        'CEDULA': '05',
        'PASAPORTE': '06',
        'CONSUMIDOR_FINAL': '07',
        'ID_EXTERIOR': '08'
    }

    @staticmethod
    def map_identification_type(internal_type, doc_number):
        """Mapea el tipo de documento interno al código SRI"""
        if doc_number == '9999999999999' or doc_number == '9999999999':
            return '07'
        return APIVendoService.IDENTIFICATION_MAP.get(internal_type, '05')

    @classmethod
    def prepara_datos_factura(cls, venta, forzar_numero=None):
        """Prepara el JSON siguiendo la estructura de APIVendo"""
        from apps.system_configuration.models import ConfiguracionSistema
        config_sys = ConfiguracionSistema.get_config()
        
        cliente = venta.cliente
        
        # Determinar tipo de identificación y número
        if cliente:
            id_type = cls.map_identification_type(cliente.tipo_documento, cliente.numero_documento)
            id_number = cliente.numero_documento
            name = f"{cliente.nombres} {cliente.apellidos}" if not cliente.nombre_comercial else cliente.nombre_comercial
            address = cliente.direccion or "Quito, Ecuador"
            email = cliente.email or "sin-email@commercebox.com"
            phone = cliente.telefono or "0999999999"
        else:
            # Consumidor Final
            id_type = '07'
            id_number = '9999999999999'
            name = 'CONSUMIDOR FINAL'
            address = "Quito, Ecuador"
            email = "consumidorfinal@commercebox.com"
            phone = "0999999999"

        items = []
        for detalle in venta.detalles.all():
            quantity = float(detalle.cantidad_unidades or detalle.peso_vendido or 1)
            unit_price = float(detalle.precio_unitario or detalle.precio_por_unidad_peso or 0)
            discount = float(detalle.descuento_monto or 0)
            subtotal = (quantity * unit_price) - discount
            
            # Preparar impuestos para el item
            taxes = []
            if config_sys.iva_activo and detalle.producto.aplica_impuestos:
                iva_rate = float(config_sys.porcentaje_iva)
                taxes.append({
                    "code": "2",  # Código SRI para IVA
                    "percentage_code": "2",  # Código para la tarifa (2 es 12% o la vigente)
                    "rate": iva_rate,
                    "base": round(subtotal, 2),
                    "value": round(subtotal * (iva_rate / 100), 2)
                })

            item_data = {
                "main_code": detalle.producto.codigo_barras or f"PROD-{detalle.producto.id}"[:25],
                "auxiliary_code": "",
                "description": detalle.producto.nombre[:300],
                "quantity": quantity,
                "unit_price": unit_price,
                "discount": discount,
                "taxes": taxes
            }
            items.append(item_data)

        # Usar el número forzado o el de la venta
        invoice_full_number = forzar_numero or venta.numero_factura or ""
        
        # Desglosar establecimiento, punto de emisión y secuencial si existe el formato
        establishment = "001"
        emission_point = "001"
        sequential = ""
        
        if invoice_full_number and "-" in invoice_full_number:
            parts = invoice_full_number.split("-")
            if len(parts) == 3:
                establishment = parts[0]
                emission_point = parts[1]
                sequential = parts[2]

        # ✅ CRÍTICO: Convertir fecha de UTC a hora local de Ecuador antes de formatear.
        # Con USE_TZ=True Django guarda en UTC. Si son las 23:30 en Ecuador,
        # en UTC es el 04:30 del día siguiente → el SRI rechaza la factura como extemporánea.
        from django.utils.timezone import localtime
        fecha_emision_local = localtime(venta.fecha_venta)
        
        payload = {
            "issue_date": fecha_emision_local.strftime('%Y-%m-%d'),
            "customer_identification_type": id_type,
            "customer_identification": id_number,
            "customer_name": name,
            "customer_address": address,
            "customer_email": email,
            "customer_phone": phone,
            "send_email": True,
            "items": items,
            "order_number": f"{venta.numero_venta}-{int(timezone.now().timestamp())}", # Hacerlo único por intento
            "establishment": establishment,
            "emission_point": emission_point,
            "sequential": sequential,
            "invoice_number": invoice_full_number,
            "total_without_taxes": float(venta.subtotal),
            "total_discount": float(venta.descuento),
            "total_tax": float(venta.impuestos),
            "total_amount": float(venta.total)
        }
        
        return payload

    @classmethod
    def enviar_factura_sri(cls, venta):
        """Envía la factura a APIVendo y registra el log con reintentos automáticos si está en procesamiento"""
        from apps.sales_management.invoicing.invoice_service import InvoiceService
        import time
        
        config = SRIConfig.get_config()
        if not config or not config.api_token:
            return False, "Configuración SRI no encontrada o sin token."

        max_intentos = 4
        ultimo_mensaje = ""
        
        # Guardar el número original por si acaso
        numero_original = venta.numero_factura

        for intento in range(1, max_intentos + 1):
            logger.info(f"🔄 Intento {intento} de envío SRI para venta {venta.numero_venta}")
            
            # Si el SRI dijo que está en procesamiento, forzamos un NUEVO número para "desatascar"
            # el proceso. El SRI no permite la misma clave si ya está en cola.
            if intento > 1 and ("PROCESAMIENTO" in ultimo_mensaje.upper() or "REGISTRADO" in ultimo_mensaje.upper()):
                logger.info(f"⚠️ Limpiando número {venta.numero_factura} para generar uno nuevo y evitar colisión.")
                venta.numero_factura = "" # Limpiar para que InvoiceService genere el siguiente real

            # Generar/Obtener número secuencial
            if not venta.numero_factura:
                nuevo_numero = InvoiceService.generar_numero_factura(venta)
            else:
                nuevo_numero = venta.numero_factura
            
            payload = cls.prepara_datos_factura(venta, forzar_numero=nuevo_numero)
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {config.api_token}"
            }

            log = SRILog.objects.create(
                venta=venta,
                request_data=payload,
                invoice_number_sri=nuevo_numero
            )

            try:
                response = requests.post(config.api_url, json=payload, headers=headers, timeout=25)
                log.status_code = response.status_code
                
                try:
                    response_json = response.json()
                except:
                    response_json = {"raw_response": response.text}
                    
                log.response_data = response_json
                
                if response.status_code in [201, 200]:
                    log.success = response_json.get('success', False)
                    log.message = response_json.get('message', '') or response_json.get('error', '')
                    
                    if 'invoice' in response_json:
                        invoice_data = response_json['invoice']
                        log.invoice_id_apivendo = invoice_data.get('id')
                        log.invoice_number_sri = invoice_data.get('number', nuevo_numero)
                        
                        if log.success:
                            venta.numero_factura = log.invoice_number_sri
                            venta.factura_electronica_enviada = True
                            venta.factura_electronica_clave = invoice_data.get('access_key', '')
                            venta.save()
                    
                    log.save()
                    
                    # Si tuvo éxito, salir del bucle
                    if log.success:
                        return True, log.message or (f"Enviada correctamente: {log.invoice_number_sri}")
                    
                    # Si el error es "EN PROCESAMIENTO", esperar y reintentar con OTRO NÚMERO
                    msg_error = (log.message or "").upper()
                    if "EN PROCESAMIENTO" in msg_error or "REGISTRADO" in msg_error or "CLAVE DE ACCESO" in msg_error:
                        logger.warning(f"⏳ SRI indica procesamiento/duplicado. Reintentando con nuevo secuencial ({intento}/{max_intentos})...")
                        ultimo_mensaje = log.message
                        time.sleep(intento * 3) # Espera progresiva
                        continue
                    else:
                        # Si es otro tipo de error (ej: datos mal formados), no reintentamos
                        return False, log.message or "SRI rechazó el documento"
                else:
                    log.success = False
                    log.message = response_json.get('message', '') or response_json.get('error', 'Error del servidor APIVendo')
                    log.status_code = response.status_code
                    log.save()
                    return False, log.message

            except Exception as e:
                error_msg = f"Error de conexión: {str(e)}"
                log.message = error_msg
                log.save()
                if intento < max_intentos:
                    time.sleep(3)
                    continue
                return False, error_msg

        return False, f"Se agotaron los {max_intentos} intentos. Último error SRI: {ultimo_mensaje}"
