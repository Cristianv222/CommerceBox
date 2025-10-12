# apps/notifications/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notificacion, PreferenciasNotificacion

# TODO: Implementar vistas según necesidades del proyecto

@login_required
def lista_notificaciones(request):
    """
    Lista de notificaciones del usuario
    """
    notificaciones = Notificacion.objects.filter(
        usuario=request.user
    ).order_by('-fecha_creacion')
    
    return render(request, 'notifications/lista.html', {
        'notificaciones': notificaciones
    })

@login_required
def marcar_leida(request, id):
    """
    Marca una notificación como leída
    """
    notificacion = get_object_or_404(Notificacion, id=id, usuario=request.user)
    notificacion.marcar_leida()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    
    return redirect('notifications:lista')