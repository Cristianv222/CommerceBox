# apps/sales_management/invoicing/invoice_service.py

from django.template.loader import render_to_string
from decimal import Decimal
import json


class InvoiceService:
    """
    Servicio para generar facturas
    ✅ ACTUALIZADO: Usa configuración desde system_configuration
    """
    
    @staticmethod
    def generar_factura_html(venta):
        """
        Genera el HTML de la factura
        
        Args:
            venta: Venta
        
        Returns:
            str: HTML de la factura
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
            'config': config,  # ✅ Pasar config completo al template
        }
        
        return render_to_string('sales/factura_template.html', context)
    
    @staticmethod
    def generar_numero_factura(venta):
        """
        Genera número de factura según normativa
        
        Args:
            venta: Venta
        
        Returns:
            str: Número de factura
        """
        # ✅ Obtener configuración del sistema
        from apps.system_configuration.models import ConfiguracionSistema
        config = ConfiguracionSistema.get_config()
        
        # Formato: 001-001-000000001
        # [Establecimiento]-[Punto Emisión]-[Secuencial]
        
        establecimiento = '001'
        punto_emision = '001'
        
        # Obtener último secuencial
        from apps.sales_management.models import Venta
        
        # ✅ Usar prefijo configurado
        prefijo = f'{establecimiento}-{punto_emision}-'
        
        ultima_con_factura = Venta.objects.filter(
            numero_factura__startswith=prefijo
        ).order_by('-numero_factura').first()
        
        if ultima_con_factura:
            try:
                ultimo_secuencial = int(ultima_con_factura.numero_factura.split('-')[-1])
                siguiente = ultimo_secuencial + 1
            except:
                siguiente = 1
        else:
            siguiente = 1
        
        return f"{establecimiento}-{punto_emision}-{siguiente:09d}"
    
    @staticmethod
    def validar_datos_facturacion(venta):
        """
        Valida que la venta tenga todos los datos necesarios para facturar
        
        Args:
            venta: Venta
        
        Returns:
            dict: {'valido': bool, 'errores': list}
        """
        errores = []
        
        # Validar cliente
        if not venta.cliente:
            errores.append("Se requiere un cliente para facturar")
        else:
            if not venta.cliente.numero_documento:
                errores.append("El cliente debe tener número de documento")
            if not venta.cliente.nombres or not venta.cliente.apellidos:
                errores.append("El cliente debe tener nombres completos")
        
        # Validar detalles
        if not venta.detalles.exists():
            errores.append("La venta no tiene detalles")
        
        # Validar montos
        if venta.total <= 0:
            errores.append("El total de la venta debe ser mayor a cero")
        
        return {
            'valido': len(errores) == 0,
            'errores': errores
        }
    
    # ESPACIO RESERVADO PARA INTEGRACIÓN DE FACTURACIÓN ELECTRÓNICA
    # ============================================================
    
    @staticmethod
    def enviar_factura_electronica(venta):
        """
        PLACEHOLDER: Envía factura al SRI o sistema de facturación electrónica
        
        Este método será implementado cuando se integre el servicio
        de facturación electrónica (ej: SRI Ecuador, SUNAT Perú, etc.)
        
        Args:
            venta: Venta a facturar
        
        Returns:
            dict: Resultado del envío
        """
        # ✅ Obtener configuración del sistema
        from apps.system_configuration.models import ConfiguracionSistema
        config = ConfiguracionSistema.get_config()
        
        # TODO: Implementar integración con servicio de facturación
        # Aquí se usaría config.ruc_empresa, config.nombre_empresa, etc.
        
        return {
            'exito': False,
            'mensaje': 'Facturación electrónica no configurada',
            'clave_acceso': None,
            'xml': None,
            'pdf_url': None,
            'empresa_ruc': config.ruc_empresa,  # ✅ Información de la empresa
            'empresa_nombre': config.nombre_empresa,
        }
    
    @staticmethod
    def consultar_estado_factura(clave_acceso):
        """
        PLACEHOLDER: Consulta estado de factura en el SRI
        
        Args:
            clave_acceso: Clave de acceso de la factura
        
        Returns:
            dict: Estado de la factura
        """
        # TODO: Implementar consulta al SRI
        
        return {
            'estado': 'PENDIENTE',
            'mensaje': 'Consulta no disponible'
        }
    
    @staticmethod
    def generar_datos_factura_electronica(venta):
        """
        ✅ NUEVO: Genera los datos necesarios para facturación electrónica
        
        Args:
            venta: Venta a facturar
        
        Returns:
            dict: Datos estructurados para facturación electrónica
        """
        from apps.system_configuration.models import ConfiguracionSistema
        config = ConfiguracionSistema.get_config()
        
        # Estructura básica para facturación electrónica
        datos = {
            'empresa': {
                'ruc': config.ruc_empresa,
                'razon_social': config.nombre_empresa,
                'nombre_comercial': config.nombre_empresa,
                'direccion': config.direccion_empresa,
                'telefono': config.telefono_empresa,
                'email': config.email_empresa,
            },
            'cliente': {
                'identificacion': venta.cliente.numero_documento if venta.cliente else '9999999999999',
                'razon_social': venta.cliente.nombre_completo() if venta.cliente else 'CONSUMIDOR FINAL',
                'direccion': venta.cliente.direccion if venta.cliente and hasattr(venta.cliente, 'direccion') else '',
                'email': venta.cliente.email if venta.cliente and hasattr(venta.cliente, 'email') else '',
                'telefono': venta.cliente.telefono if venta.cliente and hasattr(venta.cliente, 'telefono') else '',
            },
            'factura': {
                'numero': venta.numero_factura,
                'fecha_emision': venta.fecha_venta.isoformat(),
                'moneda': config.moneda,
                'tipo_identificacion_comprador': 'RUC' if venta.cliente and len(venta.cliente.numero_documento) == 13 else 'CEDULA',
            },
            'detalles': [],
            'totales': {
                'subtotal_sin_impuestos': float(venta.subtotal),
                'subtotal_0': 0.00,  # Productos sin IVA
                'subtotal_iva': float(venta.subtotal),  # Productos con IVA
                'descuento': float(venta.descuento),
                'iva': float(venta.impuestos),
                'propina': 0.00,
                'total': float(venta.total),
            },
            'pagos': []
        }
        
        # Agregar detalles
        for detalle in venta.detalles.all():
            item = {
                'codigo_principal': detalle.producto.codigo_barras or str(detalle.producto.id)[:10],
                'codigo_auxiliar': str(detalle.producto.id)[:10],
                'descripcion': detalle.producto.nombre,
                'cantidad': float(detalle.peso_vendido if detalle.producto.es_quintal() else detalle.cantidad_unidades),
                'precio_unitario': float(detalle.precio_unitario),
                'descuento': float(detalle.descuento if hasattr(detalle, 'descuento') else 0),
                'precio_total_sin_impuesto': float(detalle.subtotal - (detalle.descuento if hasattr(detalle, 'descuento') else 0)),
                'impuestos': []
            }
            
            # Agregar IVA si aplica
            if config.iva_activo and detalle.producto.aplica_impuestos:
                item['impuestos'].append({
                    'codigo': '2',  # Código IVA
                    'codigo_porcentaje': '2',  # IVA 12% o 15% según país
                    'base_imponible': float(detalle.subtotal),
                    'valor': float(detalle.subtotal * (config.porcentaje_iva / 100)),
                    'tarifa': float(config.porcentaje_iva),
                })
            
            datos['detalles'].append(item)
        
        # Agregar formas de pago
        for pago in venta.pagos.all():
            datos['pagos'].append({
                'forma_pago': pago.forma_pago,
                'total': float(pago.monto),
                'plazo': 0 if pago.forma_pago != 'CREDITO' else config.dias_credito_default,
                'unidad_tiempo': 'dias'
            })
        
        return datos