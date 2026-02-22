from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from apps.sales_management.models import Venta
from .services import APIVendoService
from .models import SRIConfig, SRILog
from django.contrib import messages
from django.utils.decorators import method_decorator
from functools import wraps

# Decorador simple para reusar el concepto de custom_admin
def auth_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # En CommerceBox el login está en /login/
            return redirect('/login/')
        return view_func(request, *args, **kwargs)
    return wrapper

@method_decorator(auth_required, name='dispatch')
class SriDashboardView(View):
    def get(self, request):
        config = SRIConfig.get_config()
        # Obtener ventas recientes
        ventas_recientes = Venta.objects.filter(estado='COMPLETADA').order_by('-fecha_venta')[:20]
        logs_recientes = SRILog.objects.select_related('venta').all().order_by('-fecha_envio')[:20]
        
        context = {
            'config': config,
            'ventas_recientes': ventas_recientes,
            'logs_recientes': logs_recientes,
        }
        return render(request, 'sri/dashboard.html', context)

@method_decorator(auth_required, name='dispatch')
class SriTestSendView(View):
    def post(self, request):
        import json
        try:
            data = json.loads(request.body)
            venta_id = data.get('venta_id')
        except:
            venta_id = request.POST.get('venta_id')

        try:
            venta = Venta.objects.get(id=venta_id)
            success, message = APIVendoService.enviar_factura_sri(venta)
            return JsonResponse({'success': success, 'message': message})
        except Venta.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Venta no encontrada'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

@method_decorator(auth_required, name='dispatch')
class SriConfigUpdateView(View):
    def post(self, request):
        token = request.POST.get('api_token')
        is_test_mode = request.POST.get('is_test_mode') == 'on'
        url = request.POST.get('api_url')
        
        config = SRIConfig.get_config()
        if not config:
            config = SRIConfig()
        
        config.api_token = token
        config.is_test_mode = is_test_mode
        if url:
            config.api_url = url
        config.save()
        
        messages.success(request, "✅ Configuración SRI actualizada correctamente.")
        return redirect('sri:dashboard')

@method_decorator(auth_required, name='dispatch')
class SriRetryView(View):
    """API para reintentar el envío de una venta específica al SRI"""
    def post(self, request, pk):
        try:
            venta = Venta.objects.get(id=pk)
            # El servicio ya tiene lógica de reintentos internos
            success, message = APIVendoService.enviar_factura_sri(venta)
            
            return JsonResponse({
                'success': success,
                'message': message,
                'sri_success': success,
                'sri_message': message
            })
        except Venta.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Venta no encontrada'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
