import os
from lxml import etree
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from ..utils import obtener_codigo_sri_identificacion, generar_clave_acceso

class XMLGeneratorSRI:
    """Servicio para generar archivos XML bajo el estándar del SRI Ecuador (v1.1.0)"""

    def __init__(self, config, punto_emision):
        self.config = config
        self.punto_emision = punto_emision

    def generar_xml_factura(self, venta):
        """Genera el XML para una factura específica"""
        
        punto_emision = self.punto_emision
        secuencial_num = punto_emision.ultimo_secuencial + 1
        secuencial_str = f"{secuencial_num:09d}"
        
        
        # 1. Generar la Clave de Acceso
        # IMPORTANTE: Convertir a la hora local de Ecuador para evitar errores de fecha futura
        hoy = timezone.localtime(venta.fecha_venta)
        clave_acceso = generar_clave_acceso(
            fecha=hoy,
            tipo_comprobante='01', # 01 es Factura
            ruc=self.config.ruc,
            ambiente=self.config.ambiente,
            serie=f"{punto_emision.establecimiento}{punto_emision.punto_emision}",
            secuencial=secuencial_str,
            codigo_numerico='12345678', # Código numérico sugerido
            tipo_emision='1' # 1 es Emisión Normal
        )

        ns_map = {
            'ds': "http://www.w3.org/2000/09/xmldsig#",
            'xades': "http://uri.etsi.org/01903/v1.3.2#"
        }
        root = etree.Element("factura", id="comprobante", version="1.1.0", nsmap=ns_map)
        
        # --- infoTributaria ---
        info_tributaria = etree.SubElement(root, "infoTributaria")
        
        # Validar RUC antes de continuar
        empresa_ruc = str(self.config.ruc).strip()
        if not empresa_ruc or len(empresa_ruc) != 13:
            error_msg = f"Error: RUC de la empresa inválido o vacío ('{empresa_ruc}'). Por favor, corríjalo en la Configuración SRI."
            raise ValueError(error_msg)

        etree.SubElement(info_tributaria, "ambiente").text = str(self.config.ambiente)
        etree.SubElement(info_tributaria, "tipoEmision").text = "1"
        etree.SubElement(info_tributaria, "razonSocial").text = str(self.config.razon_social)
        etree.SubElement(info_tributaria, "nombreComercial").text = str(self.config.nombre_comercial or self.config.razon_social)
        etree.SubElement(info_tributaria, "ruc").text = empresa_ruc
        etree.SubElement(info_tributaria, "claveAcceso").text = str(clave_acceso)
        etree.SubElement(info_tributaria, "codDoc").text = "01"
        etree.SubElement(info_tributaria, "estab").text = str(punto_emision.establecimiento)
        etree.SubElement(info_tributaria, "ptoEmi").text = str(punto_emision.punto_emision)
        etree.SubElement(info_tributaria, "secuencial").text = str(secuencial_str)
        etree.SubElement(info_tributaria, "dirMatriz").text = str(self.config.direccion_matriz)

        # --- infoFactura ---
        info_factura = etree.SubElement(root, "infoFactura")
        etree.SubElement(info_factura, "fechaEmision").text = hoy.strftime('%d/%m/%Y')
        etree.SubElement(info_factura, "dirEstablecimiento").text = str(self.punto_emision.direccion_establecimiento or self.config.direccion_matriz)
        etree.SubElement(info_factura, "obligadoContabilidad").text = 'SI' if self.config.obligado_contabilidad else 'NO'
        
        # Datos del Comprador
        if venta.cliente:
            tipo_ident = obtener_codigo_sri_identificacion(venta.cliente.tipo_documento, venta.cliente.numero_documento)
            identificacion = venta.cliente.numero_documento
            razon_social_comprador = f"{venta.cliente.nombres} {venta.cliente.apellidos}"
        else:
            # Consumidor Final
            tipo_ident = "07"
            identificacion = "9999999999999"
            razon_social_comprador = "CONSUMIDOR FINAL"

        etree.SubElement(info_factura, "tipoIdentificacionComprador").text = tipo_ident
        etree.SubElement(info_factura, "razonSocialComprador").text = razon_social_comprador[:300]
        etree.SubElement(info_factura, "identificacionComprador").text = identificacion
        etree.SubElement(info_factura, "totalSinImpuestos").text = f"{venta.subtotal:.2f}"
        etree.SubElement(info_factura, "totalDescuento").text = f"{venta.descuento:.2f}"

        # Totales Impuestos
        total_con_impuestos = etree.SubElement(info_factura, "totalConImpuestos")
        
        # Tarifa Estándar (15%)
        base_iva_15 = venta.get_base_iva_standard()
        if base_iva_15 > 0:
            total_impuesto_15 = etree.SubElement(total_con_impuestos, "totalImpuesto")
            etree.SubElement(total_impuesto_15, "codigo").text = "2" # 2 = IVA
            etree.SubElement(total_impuesto_15, "codigoPorcentaje").text = "4" # 4 = 15%
            etree.SubElement(total_impuesto_15, "baseImponible").text = f"{base_iva_15:.2f}"
            etree.SubElement(total_impuesto_15, "valor").text = f"{venta.get_total_iva_standard():.2f}"
            
        # Tarifa 0%
        base_iva_0 = venta.get_base_iva_0()
        if base_iva_0 > 0:
            total_impuesto_0 = etree.SubElement(total_con_impuestos, "totalImpuesto")
            etree.SubElement(total_impuesto_0, "codigo").text = "2" # 2 = IVA
            etree.SubElement(total_impuesto_0, "codigoPorcentaje").text = "0" # 0 = 0%
            etree.SubElement(total_impuesto_0, "baseImponible").text = f"{base_iva_0:.2f}"
            etree.SubElement(total_impuesto_0, "valor").text = "0.00"

        etree.SubElement(info_factura, "propina").text = "0.00"
        etree.SubElement(info_factura, "importeTotal").text = f"{venta.total:.2f}"
        etree.SubElement(info_factura, "moneda").text = "DOLAR"

        # --- pagos ---
        pagos = etree.SubElement(info_factura, "pagos")
        pago = etree.SubElement(pagos, "pago")
        etree.SubElement(pago, "formaPago").text = "01" # 01 = Sin utilización sistema financiero (Efectivo)
        etree.SubElement(pago, "total").text = f"{venta.total:.2f}"

        # --- detalles ---
        detalles_xml = etree.SubElement(root, "detalles")
        for detalle in venta.detalles.all():
            det_xml = etree.SubElement(detalles_xml, "detalle")
            
            # Identificadores del producto
            codigo_principal = str(detalle.producto.codigo_barras[:25] if detalle.producto.codigo_barras else "COD-001")
            etree.SubElement(det_xml, "codigoPrincipal").text = codigo_principal
            etree.SubElement(det_xml, "descripcion").text = str(detalle.producto.nombre[:300])
            
            cantidad = detalle.peso_vendido if detalle.producto.es_quintal() else detalle.cantidad_unidades
            etree.SubElement(det_xml, "cantidad").text = f"{cantidad:.2f}"
            
            # El precio unitario debe ser el desglosado (sin IVA)
            tarifa_item = 15 if detalle.aplica_iva else 0
            codigo_punto_item = "4" if detalle.aplica_iva else "0"
            
            factor_iva = Decimal('1.15') if detalle.aplica_iva else Decimal('1.00')
            
            # Usar el precio correcto dependiendo del tipo de producto
            precio_venta = detalle.precio_por_unidad_peso if detalle.producto.es_quintal() else detalle.precio_unitario
            precio_venta = precio_venta or Decimal('0.00')
            precio_unitario_sin_iva = precio_venta / factor_iva
            
            etree.SubElement(det_xml, "precioUnitario").text = f"{precio_unitario_sin_iva:.6f}"
            etree.SubElement(det_xml, "descuento").text = f"{detalle.descuento_monto:.2f}"
            etree.SubElement(det_xml, "precioTotalSinImpuesto").text = f"{detalle.subtotal:.2f}"
            
            # Impuestos por item
            impuestos_xml = etree.SubElement(det_xml, "impuestos")
            impuesto_xml = etree.SubElement(impuestos_xml, "impuesto")
            etree.SubElement(impuesto_xml, "codigo").text = "2"
            etree.SubElement(impuesto_xml, "codigoPorcentaje").text = codigo_punto_item
            etree.SubElement(impuesto_xml, "tarifa").text = str(tarifa_item)
            etree.SubElement(impuesto_xml, "baseImponible").text = f"{detalle.subtotal:.2f}"
            etree.SubElement(impuesto_xml, "valor").text = f"{detalle.monto_iva:.2f}"

        # Guardar XML (Sin firma todavía) - IMPORTANTE: pretty_print=False para no romper la firma
        res = etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=False)
        return res, clave_acceso
