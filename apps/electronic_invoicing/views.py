from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from .models import ComprobanteElectronico
from .services.ride_generator import RIDEGenerator
from django.core.files.base import ContentFile
import logging
from lxml import etree

logger = logging.getLogger(__name__)

def _prettify_xml(xml_str: str) -> str:
    """Formatea XML con indentación legible."""
    try:
        root = etree.fromstring(xml_str.encode('utf-8'))
        return etree.tostring(root, pretty_print=True, encoding='unicode', xml_declaration=False)
    except Exception:
        return xml_str

@login_required
def descargar_xml_sri(request, pk):
    """Sirve el XML del comprobante como descarga (prioriza autorizado > firmado > generado)"""
    comprobante = get_object_or_404(ComprobanteElectronico, pk=pk)
    xml_content = comprobante.xml_autorizado or comprobante.xml_firmado or comprobante.xml_generado
    if not xml_content:
        raise Http404("No hay contenido XML disponible para este comprobante.")
    response = HttpResponse(xml_content, content_type='application/xml')
    filename = f"{comprobante.clave_acceso}.xml" if comprobante.clave_acceso else f"comprobante_{comprobante.venta.numero_venta}.xml"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def ver_xml_sri(request, pk):
    """Muestra el XML del comprobante en el navegador (inline, legible)"""
    comprobante = get_object_or_404(ComprobanteElectronico, pk=pk)
    # Prioridad: Autorizado > Firmado > Generado
    xml_label = 'AUTORIZADO'
    xml_content = comprobante.xml_autorizado
    if not xml_content:
        xml_label = 'FIRMADO'
        xml_content = comprobante.xml_firmado
    if not xml_content:
        xml_label = 'GENERADO (sin firma)'
        xml_content = comprobante.xml_generado
    
    if not xml_content:
        return HttpResponse(
            "<h3 style='font-family:sans-serif'>❌ No hay XML disponible aún para este comprobante.</h3>",
            status=404
        )
    
    pretty_xml = _prettify_xml(xml_content)
    
    return render(request, 'electronic_invoicing/visor_xml.html', {
        'comprobante': comprobante,
        'xml_content': pretty_xml,
        'xml_label': xml_label,
    })

@login_required
def api_xml_sri(request, pk):
    """API JSON que retorna el XML y metadata del comprobante para uso AJAX"""
    comprobante = get_object_or_404(ComprobanteElectronico, pk=pk)
    xml_label = 'AUTORIZADO'
    xml_content = comprobante.xml_autorizado
    if not xml_content:
        xml_label = 'FIRMADO'
        xml_content = comprobante.xml_firmado
    if not xml_content:
        xml_label = 'GENERADO (sin firma)'
        xml_content = comprobante.xml_generado

    return JsonResponse({
        'tiene_xml': bool(xml_content),
        'xml_label': xml_label,
        'xml_content': _prettify_xml(xml_content) if xml_content else None,
        'estado': comprobante.estado,
        'clave_acceso': comprobante.clave_acceso,
        'mensajes_error': comprobante.mensajes_error,
    })

@login_required
def descargar_pdf_sri(request, pk):
    """Sirve el PDF/RIDE del comprobante (lo genera si no existe)"""
    comprobante = get_object_or_404(ComprobanteElectronico, pk=pk)
    if comprobante.pdf_ride:
        try:
            response = HttpResponse(comprobante.pdf_ride.read(), content_type='application/pdf')
            filename = comprobante.pdf_ride.name.split('/')[-1]
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
        except Exception as e:
            logger.warning(f"Archivo PDF no encontrado en disco para {comprobante.id}, regenerando... Error: {e}")
    try:
        generator = RIDEGenerator(comprobante)
        pdf_buffer = generator.generar_pdf()
        if comprobante.estado == 'AUTORIZADO' and not comprobante.pdf_ride:
            filename = f"RIDE_{comprobante.clave_acceso or comprobante.venta.numero_venta}.pdf"
            comprobante.pdf_ride.save(filename, ContentFile(pdf_buffer.getvalue()), save=True)
            pdf_buffer.seek(0)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f"RIDE_{comprobante.clave_acceso or comprobante.venta.numero_venta}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Error crítico generando PDF para {comprobante.id}: {e}")
        return HttpResponse(f"Error creando el documento RIDE: {str(e)}", status=500)

@login_required
def actualizar_secuencial_sri(request):
    """API endpoint to update the next sequential number for a Punto de Emision"""
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            punto_id = data.get('id')
            nuevo_valor = int(data.get('ultimo_secuencial'))
            
            from .models import PuntoEmision
            punto = get_object_or_404(PuntoEmision, pk=punto_id)
            
            # El SRI usa 9 dígitos.
            if 0 <= nuevo_valor <= 999999999:
                punto.ultimo_secuencial = nuevo_valor
                punto.save()
                return JsonResponse({'status': 'success', 'message': f'Secuencial actualizado a {nuevo_valor:09d}'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Valor fuera de rango (0-999,999,999)'}, status=400)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            return JsonResponse({'status': 'error', 'message': f'Datos inválidos: {str(e)}'}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

