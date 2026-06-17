import logging
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.graphics.barcode import code128
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from apps.system_configuration.models import ConfiguracionSistema
from decimal import Decimal

logger = logging.getLogger(__name__)

class RIDEGenerator:
    """
    Servicio para generar el RIDE (Representación Impresa de Documento Electrónico)
    en formato PDF para facturas del SRI Ecuador.
    """

    def __init__(self, comprobante):
        self.comprobante = comprobante
        self.venta = comprobante.venta
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(name='Small', fontSize=8, leading=10))
        self.styles.add(ParagraphStyle(name='Mini', fontSize=7, leading=8))
        self.styles.add(ParagraphStyle(name='BoldSmall', fontSize=8, leading=10, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='TitleSmall', fontSize=10, leading=12, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='BoldLarge', fontSize=12, leading=14, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='Center', alignment=1))

    def generar_pdf(self):
        """Genera el contenido del PDF y lo devuelve en BytesIO"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        elements = []
        from apps.electronic_invoicing.models import SRIConfig
        sys_config = ConfiguracionSistema.get_config()
        sri_config = SRIConfig.objects.first()
        
        nombre_marca = sys_config.nombre_empresa
        razon_social = sri_config.razon_social if (sri_config and sri_config.razon_social) else sys_config.nombre_empresa
        
        direccion_real = sys_config.direccion_empresa or (sri_config.direccion_matriz if sri_config else "N/A")
        telefono_real = sys_config.telefono_empresa or "S/N"
        
        ruc_emisor = sri_config.ruc if (sri_config and sri_config.ruc) else sys_config.ruc_empresa
        obligado = "SI" if (sri_config and sri_config.obligado_contabilidad) else "NO"

        COLOR_PRIMARIO = colors.HexColor("#1A237E")
        COLOR_ACENTO = colors.HexColor("#2E7D32")
        
        info_emisor_cells = []
        
        if sys_config.logo_empresa:
            try:
                logo_path = sys_config.logo_empresa.path
                if os.path.exists(logo_path):
                    logo_img = Image(logo_path, width=6*cm, height=3.5*cm, kind='proportional')
                    info_emisor_cells.append([logo_img])
                    info_emisor_cells.append([Spacer(1, 0.3*cm)])
            except Exception as e:
                logger.error(f"Error cargando logo en RIDE: {e}")

        style_nombre = ParagraphStyle('Marca', parent=self.styles['TitleSmall'], fontSize=16, textColor=COLOR_PRIMARIO, spaceAfter=5)
        style_contacto = ParagraphStyle('Contacto', parent=self.styles['Small'], fontSize=9, leading=11)
        
        info_emisor_cells.extend([
            [Paragraph(f"<b>{nombre_marca.upper()}</b>", style_nombre)],
            [Paragraph(f"<b>{razon_social}</b>", self.styles['Small'])],
            [Paragraph(f"<b>Dirección:</b> {direccion_real}", style_contacto)],
            [Paragraph(f"<b>Teléfono:</b> {telefono_real}", style_contacto)],
            [Paragraph(f"<b>Obligado a llevar Contabilidad:</b> {obligado}", self.styles['Small'])],
        ])

        if sri_config:
            if sri_config.contribuyente_especial:
                info_emisor_cells.append([Paragraph(f"<b>Contribuyente Especial Nro:</b> {sri_config.contribuyente_especial}", self.styles['Small'])])
            if sri_config.agente_retencion:
                info_emisor_cells.append([Paragraph(f"<b>Agente de Retención Resolución Nro:</b> {sri_config.agente_retencion}", self.styles['Small'])])
            if sri_config.regimen_rimpe:
                info_emisor_cells.append([Paragraph("<b>CONTRIBUYENTE RÉGIMEN RIMPE</b>", self.styles['Small'])])
        
        emisor_table = Table(info_emisor_cells, colWidths=[doc.width/2.1])
        emisor_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))

        datos_fiscales = [
            [Paragraph(f"<b>R.U.C.:</b> {ruc_emisor}", self.styles['Normal'])],
            [Paragraph("<b>FACTURA</b>", self.styles['BoldLarge'])],
            [Paragraph(f"No. {self.venta.numero_factura or self.venta.numero_venta}", self.styles['Normal'])],
            [Paragraph(f"<b>NÚMERO DE AUTORIZACIÓN:</b>", self.styles['Small'])],
            [Paragraph(f"{self.comprobante.clave_acceso or 'PENDIENTE'}", ParagraphStyle('Clave', parent=self.styles['Small'], fontSize=8))],
            [Paragraph(f"<b>FECHA Y HORA DE AUTORIZACIÓN:</b>", self.styles['Small'])],
            [Paragraph(f"{timezone.localtime(self.comprobante.fecha_autorizacion).strftime('%Y-%m-%d %H:%M:%S') if self.comprobante.fecha_autorizacion else 'PENDIENTE'}", self.styles['Small'])],
            [Paragraph(f"<b>AMBIENTE:</b> {'PRODUCCIÓN' if self.comprobante.ambiente == 2 else 'PRUEBAS'}", self.styles['Small'])],
            [Paragraph(f"<b>EMISIÓN:</b> NORMAL", self.styles['Small'])],
            [Paragraph("<b>CLAVE DE ACCESO:</b>", self.styles['Small'])],
            [Paragraph(f"{self.comprobante.clave_acceso or 'PENDIENTE'}", ParagraphStyle('Clave', parent=self.styles['Small'], fontSize=7))],
        ]
        
        fiscal_table = Table(datos_fiscales, colWidths=[doc.width/2.1])
        fiscal_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 2, COLOR_PRIMARIO),
            ('PADDING', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))

        header_table = Table([[emisor_table, fiscal_table]], colWidths=[doc.width/2, doc.width/2])
        elements.append(header_table)
        elements.append(Spacer(1, 0.8*cm))

        cliente = self.venta.cliente
        cliente_data = [
            [f"Razón Social / Nombres y Apellidos: {cliente.nombre_completo() if cliente else 'CONSUMIDOR FINAL'}", f"Identificación: {cliente.numero_documento if cliente else '9999999999999'}"],
            [f"Fecha Emisión: {timezone.localtime(self.venta.fecha_venta).strftime('%d/%m/%Y')}", f"Guía Remisión: "]
        ]
        cliente_table = Table(cliente_data, colWidths=[doc.width*0.7, doc.width*0.3])
        cliente_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(cliente_table)
        elements.append(Spacer(1, 0.5*cm))

        data = [["Cod. Principal", "Cant", "Descripción", "Precio Unitario", "Descuento", "Precio Total"]]
        for det in self.venta.detalles.all():
            data.append([
                det.producto.codigo_barras or "N/A",
                f"{det.cantidad_unidades:.2f}",
                det.producto.nombre,
                f"{det.precio_unitario:.2f}",
                f"{det.descuento_monto:.2f}",
                f"{det.total:.2f}"
            ])

        t = Table(data, colWidths=[2.5*cm, 1.5*cm, 8*cm, 2.5*cm, 2*cm, 2.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARIO),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (2,1), (2,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.5*cm))

        info_adicional_data = [
            [Paragraph("<b>Información Adicional</b>", self.styles['BoldSmall'])],
            [Paragraph(f"Email Cliente: {cliente.email if cliente else 'N/A'}", self.styles['Small'])],
            [Paragraph(f"Dirección Cliente: {cliente.direccion if cliente else 'N/A'}", self.styles['Small'])],
            [Paragraph(f"Vendedor: {self.venta.vendedor.get_full_name() if self.venta.vendedor else 'Sistema'}", self.styles['Small'])],
        ]
        info_adicional_table = Table(info_adicional_data, colWidths=[doc.width*0.5])
        info_adicional_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('PADDING', (0,0), (-1,-1), 5),
            ('BACKGROUND', (0,0), (0,0), colors.lightgrey),
        ]))

        subtotal_15 = Decimal('0.00')
        subtotal_0 = Decimal('0.00')
        for det in self.venta.detalles.all():
            if det.aplica_iva:
                subtotal_15 += det.subtotal
            else:
                subtotal_0 += det.subtotal
        
        total_iva = self.venta.impuestos
        total_factura = self.venta.total
        
        totales_data = [
            ["SUBTOTAL 15%", f"{subtotal_15:.2f}"],
            ["SUBTOTAL 0%", f"{subtotal_0:.2f}"],
            ["SUBTOTAL SIN IMPUESTOS", f"{self.venta.subtotal:.2f}"],
            ["TOTAL Descuento", f"{self.venta.descuento:.2f}"],
            ["IVA 15%", f"{total_iva:.2f}"],
            [Paragraph("<b>VALOR TOTAL</b>", self.styles['BoldSmall']), f"<b>{total_factura:.2f}</b>"]
        ]
        
        totales_table = Table(totales_data, colWidths=[doc.width*0.3, doc.width*0.2])
        totales_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('BACKGROUND', (0,-1), (-1,-1), COLOR_PRIMARIO),
            ('TEXTCOLOR', (0,-1), (-1,-1), colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 9),
        ]))

        footer_table = Table([[info_adicional_table, totales_table]], colWidths=[doc.width*0.5, doc.width*0.5])
        footer_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        elements.append(footer_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer
