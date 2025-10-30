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
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import (
    ConfiguracionSistema, ParametroSistema, RegistroBackup,
    LogConfiguracion, HealthCheck, get_parametro, set_parametro
)
from .forms import (
    ConfiguracionSistemaForm, ParametroSistemaForm, EjecutarBackupForm,
    LogConfiguracionFiltroForm, BackupFiltroForm
)
import logging
logger = logging.getLogger(__name__)
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
    """Crear nuevo parámetro - ACTUALIZADO para trabajar con modal"""
    
    if request.method == 'POST':
        try:
            # Obtener datos directamente del POST (sin formulario Django)
            modulo = request.POST.get('modulo')
            clave = request.POST.get('clave')
            nombre = request.POST.get('nombre', '')
            descripcion = request.POST.get('descripcion', '')
            tipo_dato = request.POST.get('tipo_dato')
            valor = request.POST.get('valor')
            valor_default = request.POST.get('valor_default', '')
            grupo = request.POST.get('grupo', '')
            orden = request.POST.get('orden', 0)
            activo = request.POST.get('activo') == 'on'
            editable = request.POST.get('editable') == 'on'
            requerido = request.POST.get('requerido') == 'on'
            
            # Validar que no exista
            if ParametroSistema.objects.filter(modulo=modulo, clave=clave).exists():
                messages.error(request, f'❌ Ya existe un parámetro con la clave {clave} en el módulo {modulo}')
                return redirect('system_configuration:parametros_lista')
            
            # Crear parámetro
            parametro = ParametroSistema.objects.create(
                modulo=modulo,
                clave=clave,
                nombre=nombre,
                descripcion=descripcion,
                tipo_dato=tipo_dato,
                valor=valor,
                valor_default=valor_default,
                grupo=grupo,
                orden=orden,
                activo=activo,
                editable=editable,
                requerido=requerido,
                actualizado_por=request.user
            )
            
            # Registrar en log
            registrar_cambio_configuracion(
                tabla='ParametroSistema',
                registro_id=parametro.id,
                tipo_cambio='CREACION',
                usuario=request.user,
                descripcion=f"Creación de parámetro {parametro.modulo}.{parametro.clave}"
            )
            
            messages.success(request, f'✅ Parámetro {parametro.clave} creado exitosamente')
            return redirect('system_configuration:parametros_lista')
            
        except Exception as e:
            messages.error(request, f'❌ Error al crear parámetro: {str(e)}')
            return redirect('system_configuration:parametros_lista')
    
    # Si es GET, redirigir a la lista (el modal se maneja en la plantilla)
    return redirect('system_configuration:parametros_lista')

@login_required
@user_passes_test(es_administrador)
def parametro_editar(request, parametro_id):
    """Editar parámetro existente - ACTUALIZADO para trabajar con modal"""
    
    parametro = get_object_or_404(ParametroSistema, id=parametro_id)
    
    if request.method == 'POST':
        try:
            # Guardar valores anteriores para auditoría
            valor_anterior = parametro.valor
            
            # Actualizar datos directamente (sin formulario Django)
            parametro.modulo = request.POST.get('modulo', parametro.modulo)
            parametro.clave = request.POST.get('clave', parametro.clave)
            parametro.nombre = request.POST.get('nombre', '')
            parametro.descripcion = request.POST.get('descripcion', '')
            parametro.tipo_dato = request.POST.get('tipo_dato', parametro.tipo_dato)
            parametro.valor = request.POST.get('valor', parametro.valor)
            parametro.valor_default = request.POST.get('valor_default', '')
            parametro.grupo = request.POST.get('grupo', '')
            parametro.orden = int(request.POST.get('orden', 0))
            parametro.activo = request.POST.get('activo') == 'on'
            parametro.editable = request.POST.get('editable') == 'on'
            parametro.requerido = request.POST.get('requerido') == 'on'
            parametro.actualizado_por = request.user
            
            parametro.save()
            
            # Registrar cambio si el valor cambió
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
            
            messages.success(request, f'✅ Parámetro {parametro.clave} actualizado exitosamente')
            return redirect('system_configuration:parametros_lista')
            
        except Exception as e:
            messages.error(request, f'❌ Error al actualizar parámetro: {str(e)}')
            return redirect('system_configuration:parametros_lista')
    
    # Si es GET, redirigir a la lista (el modal carga datos via AJAX)
    return redirect('system_configuration:parametros_lista')

@login_required
@user_passes_test(es_administrador)
def parametro_eliminar(request, parametro_id):
    """Eliminar parámetro - ACTUALIZADO para trabajar con modal"""
    
    parametro = get_object_or_404(ParametroSistema, id=parametro_id)
    
    if request.method == 'POST':
        try:
            clave = parametro.clave
            modulo = parametro.modulo
            
            # Registrar eliminación
            registrar_cambio_configuracion(
                tabla='ParametroSistema',
                registro_id=parametro.id,
                tipo_cambio='ELIMINACION',
                usuario=request.user,
                descripcion=f"Eliminación de parámetro {modulo}.{clave}"
            )
            
            parametro.delete()
            
            messages.success(request, f'✅ Parámetro {clave} eliminado exitosamente')
            return redirect('system_configuration:parametros_lista')
            
        except Exception as e:
            messages.error(request, f'❌ Error al eliminar parámetro: {str(e)}')
            return redirect('system_configuration:parametros_lista')
    
    # Si es GET, redirigir a la lista (el modal muestra la info directamente)
    return redirect('system_configuration:parametros_lista')
@login_required
@user_passes_test(es_administrador)
def parametro_detalle_json(request, parametro_id):
    """
    API para obtener datos de un parámetro en formato JSON
    Usado por el modal de edición para cargar datos via AJAX
    """
    try:
        parametro = get_object_or_404(ParametroSistema, id=parametro_id)
        
        data = {
            'id': str(parametro.id),
            'modulo': parametro.modulo,
            'clave': parametro.clave,
            'nombre': parametro.nombre or '',
            'descripcion': parametro.descripcion or '',
            'tipo_dato': parametro.tipo_dato,
            'valor': parametro.valor,
            'valor_default': parametro.valor_default or '',
            'grupo': parametro.grupo or '',
            'orden': parametro.orden,
            'activo': parametro.activo,
            'editable': parametro.editable,
            'requerido': parametro.requerido,
        }
        
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)

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


@ensure_csrf_cookie
@login_required
@require_http_methods(["POST"])
def backup_ejecutar(request):
    """
    Vista para ejecutar un backup manual del sistema
    """
    form = EjecutarBackupForm(request.POST)
    
    if form.is_valid():
        try:
            tipo_backup = form.cleaned_data['tipo_backup']
            incluir_media = form.cleaned_data.get('incluir_media', False)
            comprimir = form.cleaned_data.get('comprimir', True)
            
            usuario = request.user
            
            # Crear nombre de archivo
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            extension = '.sql.gz' if comprimir else '.sql'
            nombre_archivo = f'backup_manual_{timestamp}{extension}'
            
            # Crear registro de backup
            backup = RegistroBackup.objects.create(
                nombre_archivo=nombre_archivo,
                tipo_backup=tipo_backup,
                estado='EN_PROCESO',
                usuario=usuario,
                fecha_inicio=timezone.now()
            )
            
            try:
                import subprocess
                import os
                from django.conf import settings
                
                # Crear directorio de backups si no existe
                backup_dir = os.path.join(settings.BASE_DIR, 'backups')
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(backup_dir, nombre_archivo)
                
                # Obtener configuración de la base de datos
                db_config = settings.DATABASES['default']
                db_name = db_config['NAME']
                db_user = db_config['USER']
                db_password = db_config['PASSWORD']
                db_host = db_config['HOST']
                db_port = db_config.get('PORT', '5432')
                
                # Construir comando pg_dump
                env = os.environ.copy()
                env['PGPASSWORD'] = db_password
                
                pg_dump_cmd = [
                    'pg_dump',
                    '-U', db_user,
                    '-h', db_host,
                    '-p', db_port,
                    '-F', 'c',  # Formato custom (comprimido)
                    '--no-owner',
                    '--no-acl',
                    db_name
                ]
                
                # Ejecutar backup
                if comprimir:
                    # Usar formato custom comprimido de PostgreSQL
                    with open(backup_path, 'wb') as f:
                        result = subprocess.run(
                            pg_dump_cmd,
                            env=env,
                            stdout=f,
                            stderr=subprocess.PIPE,
                            check=True
                        )
                else:
                    # Formato SQL plano
                    pg_dump_cmd[pg_dump_cmd.index('-F')] = '-F'
                    pg_dump_cmd[pg_dump_cmd.index('c')] = 'p'  # Plain format
                    
                    with open(backup_path, 'w') as f:
                        result = subprocess.run(
                            pg_dump_cmd,
                            env=env,
                            stdout=f,
                            stderr=subprocess.PIPE,
                            check=True,
                            text=True
                        )
                
                # Si incluir_media, agregar archivos media
                if incluir_media:
                    import tarfile
                    
                    # Crear archivo tar con backup + media
                    tar_path = backup_path.replace(extension, '.tar.gz')
                    
                    with tarfile.open(tar_path, 'w:gz') as tar:
                        # Agregar dump de BD
                        tar.add(backup_path, arcname=nombre_archivo)
                        
                        # Agregar directorio media
                        media_root = settings.MEDIA_ROOT
                        if os.path.exists(media_root):
                            tar.add(media_root, arcname='media')
                    
                    # Eliminar el dump original y usar el tar
                    os.remove(backup_path)
                    backup_path = tar_path
                    backup.nombre_archivo = os.path.basename(tar_path)
                
                # Calcular tamaño del archivo
                backup.tamaño_bytes = os.path.getsize(backup_path)
                backup.ruta_archivo = backup_path
                
                # Actualizar registro como exitoso
                backup.estado = 'EXITOSO'
                backup.fecha_fin = timezone.now()
                backup.save()
                
                messages.success(request, f'✅ Backup ejecutado exitosamente: {backup.nombre_archivo}')
                logger.info(f"Backup manual ejecutado exitosamente por {usuario.username}: {backup.nombre_archivo}")
                
            except subprocess.CalledProcessError as e:
                # Error en pg_dump
                error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
                
                backup.estado = 'FALLIDO'
                backup.mensaje_error = f"Error en pg_dump: {error_msg}"
                backup.fecha_fin = timezone.now()
                backup.save()
                
                messages.error(request, f'❌ Error al ejecutar backup: {error_msg}')
                logger.error(f"Error en pg_dump: {error_msg}")
                
            except Exception as e:
                # Otros errores
                backup.estado = 'FALLIDO'
                backup.mensaje_error = str(e)
                backup.fecha_fin = timezone.now()
                backup.save()
                
                messages.error(request, f'❌ Error al ejecutar backup: {str(e)}')
                logger.error(f"Error al ejecutar backup manual: {str(e)}", exc_info=True)
                
        except Exception as e:
            messages.error(request, f'❌ Error al procesar la solicitud: {str(e)}')
            logger.error(f"Error en backup_ejecutar: {str(e)}", exc_info=True)
    
    else:
        messages.error(request, '❌ Formulario inválido. Verifica los datos ingresados.')
        logger.warning(f"Formulario de backup inválido: {form.errors}")
    
    # Redirigir de vuelta a la lista de backups
    return redirect('system_configuration:backups_lista')

@ensure_csrf_cookie
@login_required
def backup_descargar(request, backup_id):
    """
    Vista para descargar un archivo de backup
    """
    try:
        backup = get_object_or_404(RegistroBackup, id=backup_id)
        
        # Verificar que el backup fue exitoso
        if backup.estado != 'EXITOSO':
            messages.error(request, '❌ Solo se pueden descargar backups exitosos')
            return redirect('system_configuration:backups_lista')
        
        # Verificar que el archivo existe
        if not backup.ruta_archivo or not os.path.exists(backup.ruta_archivo):
            messages.error(request, '❌ El archivo de backup no existe')
            logger.error(f"Archivo de backup no encontrado: {backup.ruta_archivo}")
            return redirect('system_configuration:backups_lista')
        
        # Abrir el archivo y enviarlo como respuesta
        try:
            file = open(backup.ruta_archivo, 'rb')
            response = FileResponse(file, as_attachment=True, filename=backup.nombre_archivo)
            
            # Establecer el tipo de contenido
            if backup.nombre_archivo.endswith('.gz'):
                response['Content-Type'] = 'application/gzip'
            else:
                response['Content-Type'] = 'application/sql'
            
            logger.info(f"Backup descargado por {request.user.username}: {backup.nombre_archivo}")
            return response
            
        except Exception as e:
            messages.error(request, f'❌ Error al leer el archivo: {str(e)}')
            logger.error(f"Error al descargar backup: {str(e)}")
            return redirect('system_configuration:backups_lista')
        
    except Exception as e:
        messages.error(request, f'❌ Error al descargar backup: {str(e)}')
        logger.error(f"Error en backup_descargar: {str(e)}")
        return redirect('system_configuration:backups_lista')

@ensure_csrf_cookie
@login_required
@require_http_methods(["POST"])
def backup_restaurar(request, backup_id):
    """
    Vista para restaurar un backup
    """
    try:
        backup = get_object_or_404(RegistroBackup, id=backup_id)
        
        # Verificar que el backup fue exitoso
        if backup.estado != 'EXITOSO':
            messages.error(request, '❌ Solo se pueden restaurar backups exitosos')
            return redirect('system_configuration:backups_lista')
        
        # Verificar que el archivo existe
        if not backup.ruta_archivo or not os.path.exists(backup.ruta_archivo):
            messages.error(request, '❌ El archivo de backup no existe')
            return redirect('system_configuration:backups_lista')
        
        try:
            import subprocess
            from django.conf import settings
            
            # Obtener configuración de la base de datos
            db_config = settings.DATABASES['default']
            db_name = db_config['NAME']
            db_user = db_config['USER']
            db_password = db_config['PASSWORD']
            db_host = db_config['HOST']
            db_port = db_config.get('PORT', '5432')
            
            # Preparar el entorno
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password
            
            # Comando pg_restore
            pg_restore_cmd = [
                'pg_restore',
                '-U', db_user,
                '-h', db_host,
                '-p', db_port,
                '-d', db_name,
                '--clean',  # Limpiar objetos existentes
                '--if-exists',  # Solo si existen
                '--no-owner',
                '--no-acl',
                backup.ruta_archivo
            ]
            
            # Ejecutar restauración
            result = subprocess.run(
                pg_restore_cmd,
                env=env,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                check=True
            )
            
            # Registrar restauración exitosa
            backup.restaurado = True
            backup.fecha_restauracion = timezone.now()
            backup.save()
            
            messages.success(request, f'✅ Backup restaurado exitosamente: {backup.nombre_archivo}')
            logger.info(f"Backup restaurado por {request.user.username}: {backup.nombre_archivo}")
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
            messages.error(request, f'❌ Error al restaurar backup: {error_msg}')
            logger.error(f"Error en pg_restore: {error_msg}")
            
        except Exception as e:
            messages.error(request, f'❌ Error al restaurar backup: {str(e)}')
            logger.error(f"Error al restaurar backup: {str(e)}", exc_info=True)
        
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
        logger.error(f"Error en backup_restaurar: {str(e)}")
    
    return redirect('system_configuration:backups_lista')
# ============================================================================
# LOGS DE CONFIGURACIÓN
# ============================================================================

@login_required
@user_passes_test(es_administrador)
def logs_configuracion(request):
    """Vista de logs de cambios de configuración"""
    
    logs = LogConfiguracion.objects.select_related('usuario').order_by('-fecha_cambio')
    
    # Aplicar filtros
    form = LogConfiguracionFiltroForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('fecha_inicio'):
            logs = logs.filter(fecha_cambio__gte=form.cleaned_data['fecha_inicio'])
        if form.cleaned_data.get('fecha_fin'):
            fecha_fin = form.cleaned_data['fecha_fin']
            # Agregar 23:59:59 al día seleccionado para incluir todo el día
            fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)
            logs = logs.filter(fecha_cambio__lte=fecha_fin)
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


@login_required
@user_passes_test(es_administrador)
def log_detalle_json(request, log_id):
    """
    API para obtener detalles de un log en formato JSON
    """
    try:
        log = get_object_or_404(
            LogConfiguracion.objects.select_related('usuario'),
            pk=log_id
        )
        
        # Formatear valores largos
        valor_anterior = log.valor_anterior or ''
        valor_nuevo = log.valor_nuevo or ''
        
        # Si los valores son muy largos, truncarlos
        if len(valor_anterior) > 500:
            valor_anterior = valor_anterior[:500] + '... (truncado)'
        if len(valor_nuevo) > 500:
            valor_nuevo = valor_nuevo[:500] + '... (truncado)'
        
        return JsonResponse({
            'success': True,
            'log': {
                'id': str(log.id),
                'tabla': log.tabla,
                'registro_id': str(log.registro_id) if log.registro_id else '-',
                'tipo_cambio': log.tipo_cambio,
                'tipo_cambio_display': log.get_tipo_cambio_display(),
                'campo_modificado': log.campo_modificado or '-',
                'valor_anterior': valor_anterior or '-',
                'valor_nuevo': valor_nuevo or '-',
                'descripcion': log.descripcion or '-',
                'ip_address': log.ip_address or '-',
                'usuario': log.usuario.get_full_name() if log.usuario else 'Sistema',
                'fecha_cambio': log.fecha_cambio.strftime('%d/%m/%Y %H:%M:%S'),
            }
        })
        
    except Exception as e:
        logger.error(f"Error al obtener detalle del log: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error al cargar detalles del log'
        }, status=500)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@login_required
@user_passes_test(es_administrador)
def health_check_dashboard(request):
    """Dashboard de health checks del sistema"""
    
    # Último health check
    ultimo_check = HealthCheck.objects.order_by('-fecha_check').first()
    
    # Si no existe ningún check, ejecutar uno ahora
    if not ultimo_check:
        try:
            from django.core.management import call_command
            call_command('system_health_check')
            ultimo_check = HealthCheck.objects.order_by('-fecha_check').first()
        except Exception as e:
            logger.error(f"Error al ejecutar health check inicial: {str(e)}")
    
    # Histórico de health checks (últimos 30 días)
    checks_historico = HealthCheck.objects.filter(
        fecha_check__gte=timezone.now() - timedelta(days=30)
    ).order_by('-fecha_check')
    
    # Estadísticas del sistema actuales
    estadisticas = _obtener_estadisticas_sistema()
    
    # Estadísticas generales
    total_checks = checks_historico.count()
    checks_saludables = checks_historico.filter(estado_general='SALUDABLE').count()
    checks_criticos = checks_historico.filter(estado_general='CRITICO').count()
    
    context = {
        'ultimo_check': ultimo_check,
        'historial': checks_historico[:20],  # Últimos 20 para el historial
        'total_checks': total_checks,
        'checks_saludables': checks_saludables,
        'checks_criticos': checks_criticos,
        'estadisticas': estadisticas,
    }
    
    return render(request, 'system_configuration/health_check_dashboard.html', context)


@login_required
@user_passes_test(es_administrador)
@require_http_methods(["POST"])
def health_check_ejecutar(request):
    """Ejecutar health check manual"""
    try:
        from django.core.management import call_command
        call_command('system_health_check')
        
        messages.success(request, '✅ Health check ejecutado exitosamente')
        
        # Retornar JSON para AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
           request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'mensaje': 'Health check ejecutado correctamente'
            })
        
    except Exception as e:
        logger.error(f"Error al ejecutar health check: {str(e)}")
        messages.error(request, f'❌ Error al ejecutar health check: {str(e)}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
           request.content_type == 'application/json':
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return redirect('system_configuration:health_check_dashboard')


@login_required
@user_passes_test(es_administrador)
def health_check_api(request):
    """API para obtener el último health check (JSON)"""
    
    ultimo_check = HealthCheck.objects.order_by('-fecha_check').first()
    
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
            'uso_disco_porcentaje': float(ultimo_check.uso_disco_porcentaje or 0) if hasattr(ultimo_check, 'uso_disco_porcentaje') else None,
            'uso_cpu_porcentaje': float(ultimo_check.uso_cpu_porcentaje or 0) if hasattr(ultimo_check, 'uso_cpu_porcentaje') else None,
            'tiempo_respuesta_db_ms': ultimo_check.tiempo_respuesta_db_ms,
        },
        'errores': ultimo_check.errores,
        'advertencias': ultimo_check.advertencias,
    }
    
    return JsonResponse(data)


def _obtener_estadisticas_sistema():
    """Función auxiliar para obtener estadísticas actuales del sistema"""
    estadisticas = {
        'bd_disponible': False,
        'redis_disponible': False,
        'celery_disponible': False,
    }
    
    # Verificar base de datos
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            estadisticas['bd_disponible'] = True
    except Exception as e:
        logger.error(f"Error al verificar BD: {str(e)}")
    
    # Verificar Redis
    try:
        from django.core.cache import cache
        cache.set('health_check_test', 'ok', 10)
        if cache.get('health_check_test') == 'ok':
            estadisticas['redis_disponible'] = True
    except Exception as e:
        logger.error(f"Error al verificar Redis: {str(e)}")
    
    # Verificar Celery
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        if stats:
            estadisticas['celery_disponible'] = True
    except Exception as e:
        logger.warning(f"Celery no disponible: {str(e)}")
    
    return estadisticas




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