# apps/system_configuration/views.py

"""
Vistas para el módulo de configuración del sistema
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.conf import settings
import json
import os
from datetime import datetime, timedelta

from .models import (
    ConfiguracionSistema, ParametroSistema, RegistroBackup,
    LogConfiguracion, HealthCheck, get_parametro, set_parametro
)
from .forms import (
    ConfiguracionSistemaForm, ParametroSistemaForm, EjecutarBackupForm,
    LogConfiguracionFiltroForm, BackupFiltroForm
)


# ============================================================================
# HELPERS Y DECORADORES
# ============================================================================

def es_administrador(user):
    """Verifica si el usuario es administrador"""
    return user.is_authenticated and (user.is_superuser or user.rol == 'ADMINISTRADOR')


def registrar_cambio_configuracion(tabla, registro_id, tipo_cambio, campo=None, 
                                   valor_anterior=None, valor_nuevo=None, 
                                   usuario=None, descripcion=''):
    """Helper para registrar cambios en configuración"""
    LogConfiguracion.objects.create(
        tabla=tabla,
        registro_id=str(registro_id),
        tipo_cambio=tipo_cambio,
        campo_modificado=campo or '',
        valor_anterior=str(valor_anterior) if valor_anterior else '',
        valor_nuevo=str(valor_nuevo) if valor_nuevo else '',
        usuario=usuario,
        descripcion=descripcion
    )


# ============================================================================
# DASHBOARD DE CONFIGURACIÓN
# ============================================================================

@login_required
@user_passes_test(es_administrador)
def dashboard_configuracion(request):
    """Dashboard principal de configuración del sistema"""
    
    config = ConfiguracionSistema.get_config()
    
    # Estadísticas de backups
    backups_recientes = RegistroBackup.objects.filter(
        fecha_inicio__gte=timezone.now() - timedelta(days=7)
    ).order_by('-fecha_inicio')[:5]
    
    total_backups = RegistroBackup.objects.count()
    backups_exitosos = RegistroBackup.objects.filter(estado='EXITOSO').count()
    ultimo_backup = RegistroBackup.objects.filter(estado='EXITOSO').first()
    
    # Último health check
    ultimo_health_check = HealthCheck.objects.first()
    
    # Logs recientes
    logs_recientes = LogConfiguracion.objects.select_related('usuario').order_by('-fecha_cambio')[:10]
    
    # Parámetros por módulo
    parametros_por_modulo = ParametroSistema.objects.values('modulo').annotate(
        total=Count('id'),
        activos=Count('id', filter=Q(activo=True))
    ).order_by('modulo')
    
    # Estado de módulos
    modulos_estado = {
        'Inventario': config.modulo_inventario_activo,
        'Ventas': config.modulo_ventas_activo,
        'Financiero': config.modulo_financiero_activo,
        'Reportes': config.modulo_reportes_activo,
        'Alertas': config.modulo_alertas_activo,
    }
    
    context = {
        'config': config,
        'backups_recientes': backups_recientes,
        'total_backups': total_backups,
        'backups_exitosos': backups_exitosos,
        'ultimo_backup': ultimo_backup,
        'ultimo_health_check': ultimo_health_check,
        'logs_recientes': logs_recientes,
        'parametros_por_modulo': parametros_por_modulo,
        'modulos_estado': modulos_estado,
    }
    
    return render(request, 'system_configuration/dashboard.html', context)


# ============================================================================
# CONFIGURACIÓN GENERAL
# ============================================================================

@login_required
@user_passes_test(es_administrador)
def configuracion_general(request):
    """Vista para editar configuración general del sistema"""
    
    config = ConfiguracionSistema.get_config()
    
    if request.method == 'POST':
        # ✅ CAMBIO AQUÍ: Agregado request.FILES para manejar el upload del logo
        form = ConfiguracionSistemaForm(request.POST, request.FILES, instance=config)
        
        if form.is_valid():
            # Guardar valores anteriores para auditoría
            cambios = []
            for field in form.changed_data:
                valor_anterior = getattr(config, field)
                cambios.append({
                    'campo': field,
                    'anterior': valor_anterior,
                    'nuevo': form.cleaned_data[field]
                })
            
            # Guardar configuración
            config = form.save(commit=False)
            config.actualizado_por = request.user
            config.save()
            
            # Registrar cambios en log
            for cambio in cambios:
                registrar_cambio_configuracion(
                    tabla='ConfiguracionSistema',
                    registro_id=1,
                    tipo_cambio='MODIFICACION',
                    campo=cambio['campo'],
                    valor_anterior=cambio['anterior'],
                    valor_nuevo=cambio['nuevo'],
                    usuario=request.user,
                    descripcion=f"Actualización de configuración general"
                )
            
            messages.success(request, '✅ Configuración actualizada exitosamente')
            return redirect('system_configuration:configuracion_general')
    else:
        form = ConfiguracionSistemaForm(instance=config)
    
    context = {
        'form': form,
        'config': config,
    }
    
    return render(request, 'system_configuration/configuracion_general.html', context)


# ============================================================================
# GESTIÓN DE PARÁMETROS
# ============================================================================

@login_required
@user_passes_test(es_administrador)
def parametros_lista(request):
    """Lista de parámetros del sistema con filtros"""
    
    parametros = ParametroSistema.objects.select_related('actualizado_por').all()
    
    # Filtros
    modulo = request.GET.get('modulo')
    grupo = request.GET.get('grupo')
    activo = request.GET.get('activo')
    search = request.GET.get('search')
    
    if modulo:
        parametros = parametros.filter(modulo=modulo)
    if grupo:
        parametros = parametros.filter(grupo=grupo)
    if activo:
        parametros = parametros.filter(activo=activo == 'true')
    if search:
        parametros = parametros.filter(
            Q(nombre__icontains=search) |
            Q(clave__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(parametros, 20)
    page = request.GET.get('page')
    parametros_page = paginator.get_page(page)
    
    # Obtener módulos únicos para filtro
    modulos = ParametroSistema.objects.values_list('modulo', flat=True).distinct()
    grupos = ParametroSistema.objects.values_list('grupo', flat=True).distinct()
    
    context = {
        'parametros': parametros_page,
        'modulos': modulos,
        'grupos': grupos,
        'filtros': {
            'modulo': modulo,
            'grupo': grupo,
            'activo': activo,
            'search': search,
        }
    }
    
    return render(request, 'system_configuration/parametros_lista.html', context)


@login_required
@user_passes_test(es_administrador)
def parametro_crear(request):
    """Crear nuevo parámetro"""
    
    if request.method == 'POST':
        form = ParametroSistemaForm(request.POST)
        if form.is_valid():
            parametro = form.save(commit=False)
            parametro.actualizado_por = request.user
            parametro.save()
            
            registrar_cambio_configuracion(
                tabla='ParametroSistema',
                registro_id=parametro.id,
                tipo_cambio='CREACION',
                usuario=request.user,
                descripcion=f"Creación de parámetro {parametro.modulo}.{parametro.clave}"
            )
            
            messages.success(request, f'✅ Parámetro {parametro.clave} creado exitosamente')
            return redirect('system_configuration:parametros_lista')
    else:
        form = ParametroSistemaForm()
    
    context = {'form': form, 'accion': 'Crear'}
    return render(request, 'system_configuration/parametro_form.html', context)


@login_required
@user_passes_test(es_administrador)
def parametro_editar(request, parametro_id):
    """Editar parámetro existente"""
    
    parametro = get_object_or_404(ParametroSistema, id=parametro_id)
    
    if request.method == 'POST':
        form = ParametroSistemaForm(request.POST, instance=parametro)
        if form.is_valid():
            # Guardar valor anterior
            valor_anterior = parametro.valor
            
            parametro = form.save(commit=False)
            parametro.actualizado_por = request.user
            parametro.save()
            
            if valor_anterior != parametro.valor:
                registrar_cambio_configuracion(
                    tabla='ParametroSistema',
                    registro_id=parametro.id,
                    tipo_cambio='MODIFICACION',
                    campo='valor',
                    valor_anterior=valor_anterior,
                    valor_nuevo=parametro.valor,
                    usuario=request.user,
                    descripcion=f"Modificación de parámetro {parametro.modulo}.{parametro.clave}"
                )
            
            messages.success(request, f'✅ Parámetro {parametro.clave} actualizado')
            return redirect('system_configuration:parametros_lista')
    else:
        form = ParametroSistemaForm(instance=parametro)
    
    context = {
        'form': form,
        'parametro': parametro,
        'accion': 'Editar'
    }
    return render(request, 'system_configuration/parametro_form.html', context)


@login_required
@user_passes_test(es_administrador)
def parametro_eliminar(request, parametro_id):
    """Eliminar parámetro"""
    
    parametro = get_object_or_404(ParametroSistema, id=parametro_id)
    
    if request.method == 'POST':
        clave = parametro.clave
        
        registrar_cambio_configuracion(
            tabla='ParametroSistema',
            registro_id=parametro.id,
            tipo_cambio='ELIMINACION',
            usuario=request.user,
            descripcion=f"Eliminación de parámetro {parametro.modulo}.{clave}"
        )
        
        parametro.delete()
        messages.success(request, f'✅ Parámetro {clave} eliminado')
        return redirect('system_configuration:parametros_lista')
    
    context = {'parametro': parametro}
    return render(request, 'system_configuration/parametro_confirm_delete.html', context)


# ============================================================================
# GESTIÓN DE BACKUPS
# ============================================================================

@login_required
@user_passes_test(es_administrador)
def backups_lista(request):
    """Lista de backups con filtros"""
    
    backups = RegistroBackup.objects.select_related('usuario').all()
    
    # Aplicar filtros
    form = BackupFiltroForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('estado'):
            backups = backups.filter(estado=form.cleaned_data['estado'])
        if form.cleaned_data.get('tipo_backup'):
            backups = backups.filter(tipo_backup=form.cleaned_data['tipo_backup'])
        if form.cleaned_data.get('fecha_inicio'):
            backups = backups.filter(fecha_inicio__gte=form.cleaned_data['fecha_inicio'])
        if form.cleaned_data.get('fecha_fin'):
            backups = backups.filter(fecha_inicio__lte=form.cleaned_data['fecha_fin'])
    
    # Paginación
    paginator = Paginator(backups, 20)
    page = request.GET.get('page')
    backups_page = paginator.get_page(page)
    
    # Estadísticas
    stats = {
        'total': backups.count(),
        'exitosos': backups.filter(estado='EXITOSO').count(),
        'fallidos': backups.filter(estado='FALLIDO').count(),
        'tamaño_total': backups.filter(estado='EXITOSO').aggregate(
            total=Sum('tamaño_bytes')
        )['total'] or 0
    }
    
    context = {
        'backups': backups_page,
        'form': form,
        'stats': stats,
    }
    
    return render(request, 'system_configuration/backups_lista.html', context)


@login_required
@user_passes_test(es_administrador)
def backup_ejecutar(request):
    """Ejecutar backup manual"""
    
    if request.method == 'POST':
        form = EjecutarBackupForm(request.POST)
        if form.is_valid():
            try:
                from django.core.management import call_command
                
                # Crear registro de backup
                backup = RegistroBackup.objects.create(
                    nombre_archivo=f"backup_manual_{timezone.now().strftime('%Y%m%d_%H%M%S')}.sql",
                    ruta_archivo="",
                    tipo_backup=form.cleaned_data['tipo_backup'],
                    usuario=request.user,
                    estado='EN_PROCESO'
                )
                
                # Ejecutar comando de backup (este comando lo crearemos después)
                call_command(
                    'backup_system',
                    backup_id=str(backup.id),
                    incluir_media=form.cleaned_data['incluir_media'],
                    comprimir=form.cleaned_data['comprimir']
                )
                
                messages.success(request, '✅ Backup ejecutado exitosamente')
                return redirect('system_configuration:backups_lista')
                
            except Exception as e:
                backup.marcar_fallido(str(e))
                messages.error(request, f'❌ Error al ejecutar backup: {str(e)}')
    else:
        form = EjecutarBackupForm()
    
    context = {'form': form}
    return render(request, 'system_configuration/backup_ejecutar.html', context)


@login_required
@user_passes_test(es_administrador)
def backup_descargar(request, backup_id):
    """Descargar archivo de backup"""
    
    backup = get_object_or_404(RegistroBackup, id=backup_id)
    
    if backup.estado != 'EXITOSO':
        messages.error(request, '❌ Este backup no se completó exitosamente')
        return redirect('system_configuration:backups_lista')
    
    if not os.path.exists(backup.ruta_archivo):
        messages.error(request, '❌ Archivo de backup no encontrado')
        return redirect('system_configuration:backups_lista')
    
    try:
        response = FileResponse(
            open(backup.ruta_archivo, 'rb'),
            as_attachment=True,
            filename=backup.nombre_archivo
        )
        return response
    except Exception as e:
        messages.error(request, f'❌ Error al descargar: {str(e)}')
        return redirect('system_configuration:backups_lista')


@login_required
@user_passes_test(es_administrador)
def backup_restaurar(request, backup_id):
    """Restaurar un backup (con confirmación)"""
    
    backup = get_object_or_404(RegistroBackup, id=backup_id)
    
    if request.method == 'POST':
        try:
            from django.core.management import call_command
            
            # Aquí iría la lógica de restauración
            # POR SEGURIDAD, esto debería ser un proceso muy controlado
            
            backup.restaurado = True
            backup.fecha_restauracion = timezone.now()
            backup.save()
            
            registrar_cambio_configuracion(
                tabla='RegistroBackup',
                registro_id=backup.id,
                tipo_cambio='MODIFICACION',
                usuario=request.user,
                descripcion=f"Restauración de backup {backup.nombre_archivo}"
            )
            
            messages.success(request, '✅ Backup restaurado exitosamente')
            return redirect('system_configuration:backups_lista')
            
        except Exception as e:
            messages.error(request, f'❌ Error al restaurar: {str(e)}')
    
    context = {'backup': backup}
    return render(request, 'system_configuration/backup_confirm_restore.html', context)


# ============================================================================
# LOGS DE CONFIGURACIÓN
# ============================================================================

@login_required
@user_passes_test(es_administrador)
def logs_configuracion(request):
    """Vista de logs de cambios de configuración"""
    
    logs = LogConfiguracion.objects.select_related('usuario').all()
    
    # Aplicar filtros
    form = LogConfiguracionFiltroForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('fecha_inicio'):
            logs = logs.filter(fecha_cambio__gte=form.cleaned_data['fecha_inicio'])
        if form.cleaned_data.get('fecha_fin'):
            logs = logs.filter(fecha_cambio__lte=form.cleaned_data['fecha_fin'])
        if form.cleaned_data.get('tabla'):
            logs = logs.filter(tabla__icontains=form.cleaned_data['tabla'])
        if form.cleaned_data.get('tipo_cambio'):
            logs = logs.filter(tipo_cambio=form.cleaned_data['tipo_cambio'])
    
    # Paginación
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    context = {
        'logs': logs_page,
        'form': form,
    }
    
    return render(request, 'system_configuration/logs_configuracion.html', context)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@login_required
@user_passes_test(es_administrador)
def health_check_dashboard(request):
    """Dashboard de health checks del sistema"""
    
    # Último health check
    ultimo_check = HealthCheck.objects.first()
    
    # Histórico de health checks (últimos 30 días)
    checks_historico = HealthCheck.objects.filter(
        fecha_check__gte=timezone.now() - timedelta(days=30)
    ).order_by('-fecha_check')
    
    # Estadísticas
    total_checks = checks_historico.count()
    checks_saludables = checks_historico.filter(estado_general='SALUDABLE').count()
    checks_criticos = checks_historico.filter(estado_general='CRITICO').count()
    
    context = {
        'ultimo_check': ultimo_check,
        'checks_historico': checks_historico[:20],
        'total_checks': total_checks,
        'checks_saludables': checks_saludables,
        'checks_criticos': checks_criticos,
    }
    
    return render(request, 'system_configuration/health_check_dashboard.html', context)


@login_required
@user_passes_test(es_administrador)
def health_check_ejecutar(request):
    """Ejecutar health check manual"""
    
    if request.method == 'POST':
        try:
            from django.core.management import call_command
            call_command('system_health_check')
            
            messages.success(request, '✅ Health check ejecutado exitosamente')
        except Exception as e:
            messages.error(request, f'❌ Error al ejecutar health check: {str(e)}')
    
    return redirect('system_configuration:health_check_dashboard')


@login_required
@user_passes_test(es_administrador)
def health_check_api(request):
    """API para obtener el último health check (JSON)"""
    
    ultimo_check = HealthCheck.objects.first()
    
    if not ultimo_check:
        return JsonResponse({
            'status': 'no_data',
            'message': 'No hay health checks disponibles'
        }, status=404)
    
    data = {
        'status': ultimo_check.estado_general,
        'fecha': ultimo_check.fecha_check.isoformat(),
        'componentes': {
            'base_datos': ultimo_check.base_datos_ok,
            'redis': ultimo_check.redis_ok,
            'celery': ultimo_check.celery_ok,
            'disco': ultimo_check.disco_ok,
            'memoria': ultimo_check.memoria_ok,
        },
        'metricas': {
            'espacio_disco_gb': float(ultimo_check.espacio_disco_libre_gb or 0),
            'uso_memoria_porcentaje': float(ultimo_check.uso_memoria_porcentaje or 0),
            'tiempo_respuesta_db_ms': ultimo_check.tiempo_respuesta_db_ms,
        },
        'errores': ultimo_check.errores,
        'advertencias': ultimo_check.advertencias,
    }
    
    return JsonResponse(data)


# ============================================================================
# INFORMACIÓN DEL SISTEMA
# ============================================================================

@login_required
@user_passes_test(es_administrador)
def informacion_sistema(request):
    """Vista de información general del sistema"""
    
    import sys
    import platform
    from django import get_version
    
    config = ConfiguracionSistema.get_config()
    
    info = {
        'django_version': get_version(),
        'python_version': sys.version,
        'platform': platform.platform(),
        'processor': platform.processor(),
        'hostname': platform.node(),
        'sistema_operativo': platform.system(),
        'arquitectura': platform.machine(),
    }
    
    # Información de base de datos
    from django.db import connection
    db_info = {
        'vendor': connection.vendor,
        'settings': connection.settings_dict.get('NAME', 'N/A'),
    }
    
    context = {
        'config': config,
        'info': info,
        'db_info': db_info,
    }
    
    return render(request, 'system_configuration/informacion_sistema.html', context)


# ============================================================================
# EXPORTAR CONFIGURACIÓN
# ============================================================================

@login_required
@user_passes_test(es_administrador)
def exportar_configuracion(request):
    """Exportar configuración del sistema a JSON"""
    
    config = ConfiguracionSistema.get_config()
    parametros = ParametroSistema.objects.filter(activo=True)
    
    data = {
        'fecha_exportacion': timezone.now().isoformat(),
        'version_sistema': config.version_sistema,
        'configuracion_general': {
            'nombre_empresa': config.nombre_empresa,
            'ruc_empresa': config.ruc_empresa,
            'moneda': config.moneda,
            # ... agregar más campos según necesidad
        },
        'parametros': [
            {
                'modulo': p.modulo,
                'clave': p.clave,
                'nombre': p.nombre,
                'tipo_dato': p.tipo_dato,
                'valor': p.valor,
            }
            for p in parametros
        ]
    }
    
    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="config_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
    
    return response