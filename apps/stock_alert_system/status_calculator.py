# apps/stock_alert_system/status_calculator.py

"""
Servicio para calcular estados de stock y generar alertas
Este es el CEREBRO del sistema de alertas
"""

from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, F, Q
from datetime import timedelta


class StatusCalculator:
    """
    Calculador de estados de stock
    Determina el semáforo (🟢🟡🔴⚫) para cada producto
    """
    
    @classmethod
    def calcular_estado(cls, producto):
        """
        Calcula el estado actual de un producto
        
        Args:
            producto: Instancia de Producto (inventory_management.Producto)
        
        Returns:
            EstadoStock: Instancia actualizada
        """
        from .models import EstadoStock, ConfiguracionAlerta
        from apps.inventory_management.models import Quintal, ProductoNormal
        
        # Obtener configuración
        config = ConfiguracionAlerta.get_configuracion()
        
        if not config.alertas_activas:
            return None
        
        # Obtener o crear EstadoStock
        estado_stock, created = EstadoStock.objects.get_or_create(
            producto=producto,
            defaults={
                'tipo_inventario': producto.tipo_inventario,
                'estado_semaforo': 'NORMAL'
            }
        )
        
        # Guardar estado anterior para detectar cambios
        estado_anterior = estado_stock.estado_semaforo
        
        # Calcular según tipo de inventario
        if producto.tipo_inventario == 'QUINTAL':
            cls._calcular_estado_quintal(producto, estado_stock, config)
        else:  # NORMAL
            cls._calcular_estado_normal(producto, estado_stock, config)
        
        # Actualizar fecha de último cálculo
        estado_stock.fecha_ultimo_calculo = timezone.now()
        
        # Si cambió el estado, registrar fecha de cambio
        if estado_anterior != estado_stock.estado_semaforo:
            estado_stock.fecha_cambio_estado = timezone.now()
            
            # Registrar en historial
            cls._registrar_cambio_historial(
                producto=producto,
                estado_stock=estado_stock,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_stock.estado_semaforo
            )
            
            # Generar alerta si es necesario
            cls._generar_alerta_si_necesario(producto, estado_stock, estado_anterior)
        
        estado_stock.save()
        
        return estado_stock
    
    @classmethod
    def _calcular_estado_quintal(cls, producto, estado_stock, config):
        """
        Calcula el estado para productos tipo QUINTAL
        """
        from apps.inventory_management.models import Quintal
        
        # Obtener quintales disponibles
        quintales = Quintal.objects.filter(
            producto=producto,
            estado='DISPONIBLE'
        )
        
        # Calcular totales
        totales = quintales.aggregate(
            peso_total=Sum('peso_actual'),
            peso_inicial_total=Sum('peso_inicial'),
            cantidad=Sum(1)
        )
        
        peso_total = totales['peso_total'] or Decimal('0')
        peso_inicial_total = totales['peso_inicial_total'] or Decimal('0')
        total_quintales = totales['cantidad'] or 0
        
        # Actualizar datos en estado_stock
        estado_stock.total_quintales = total_quintales
        estado_stock.peso_total_disponible = peso_total
        estado_stock.peso_total_inicial = peso_inicial_total
        
        # Calcular porcentaje disponible
        if peso_inicial_total > 0:
            porcentaje = (peso_total / peso_inicial_total) * 100
        else:
            porcentaje = Decimal('0')
        
        estado_stock.porcentaje_disponible = porcentaje
        
        # Calcular valor de inventario
        valor = quintales.aggregate(
            valor_total=Sum(F('peso_actual') * F('costo_por_unidad'))
        )['valor_total'] or Decimal('0')
        estado_stock.valor_inventario = valor
        
        # Determinar estado del semáforo
        if peso_total <= 0:
            estado_stock.estado_semaforo = 'AGOTADO'
            estado_stock.requiere_atencion = True
        elif porcentaje <= config.umbral_quintal_critico:
            estado_stock.estado_semaforo = 'CRITICO'
            estado_stock.requiere_atencion = True
        elif porcentaje <= config.umbral_quintal_bajo:
            estado_stock.estado_semaforo = 'BAJO'
            estado_stock.requiere_atencion = False
        else:
            estado_stock.estado_semaforo = 'NORMAL'
            estado_stock.requiere_atencion = False
    
    @classmethod
    def _calcular_estado_normal(cls, producto, estado_stock, config):
        """
        Calcula el estado para productos tipo NORMAL
        """
        from apps.inventory_management.models import ProductoNormal
        
        try:
            inventario = ProductoNormal.objects.get(producto=producto)
            
            # Actualizar datos
            estado_stock.stock_actual = inventario.stock_actual
            estado_stock.stock_minimo = inventario.stock_minimo
            estado_stock.stock_maximo = inventario.stock_maximo
            
            # Calcular valor de inventario
            estado_stock.valor_inventario = inventario.stock_actual * inventario.costo_unitario
            
            # Determinar estado del semáforo
            if inventario.stock_actual == 0:
                estado_stock.estado_semaforo = 'AGOTADO'
                estado_stock.requiere_atencion = True
            elif inventario.stock_actual <= inventario.stock_minimo:
                estado_stock.estado_semaforo = 'CRITICO'
                estado_stock.requiere_atencion = True
            elif inventario.stock_actual <= (inventario.stock_minimo * config.multiplicador_stock_bajo):
                estado_stock.estado_semaforo = 'BAJO'
                estado_stock.requiere_atencion = False
            else:
                estado_stock.estado_semaforo = 'NORMAL'
                estado_stock.requiere_atencion = False
        
        except ProductoNormal.DoesNotExist:
            # Si no existe inventario, considerarlo agotado
            estado_stock.stock_actual = 0
            estado_stock.stock_minimo = 0
            estado_stock.stock_maximo = None
            estado_stock.valor_inventario = Decimal('0')
            estado_stock.estado_semaforo = 'AGOTADO'
            estado_stock.requiere_atencion = True
    
    @classmethod
    def _registrar_cambio_historial(cls, producto, estado_stock, estado_anterior, estado_nuevo):
        """
        Registra cambio de estado en el historial
        """
        from .models import HistorialEstado
        
        # Determinar stock según tipo
        if producto.tipo_inventario == 'QUINTAL':
            stock_anterior = estado_stock.peso_total_disponible
            stock_nuevo = estado_stock.peso_total_disponible
        else:
            stock_anterior = estado_stock.stock_actual
            stock_nuevo = estado_stock.stock_actual
        
        HistorialEstado.objects.create(
            producto=producto,
            estado_stock=estado_stock,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            tipo_inventario=producto.tipo_inventario,
            stock_anterior=stock_anterior,
            stock_nuevo=stock_nuevo,
            motivo_cambio='CALCULO_AUTOMATICO'
        )
    
    @classmethod
    def _generar_alerta_si_necesario(cls, producto, estado_stock, estado_anterior):
        """
        Genera alerta si el estado amerita atención
        """
        from .models import Alerta
        
        # Solo generar alerta si empeora el estado
        estados_orden = ['NORMAL', 'BAJO', 'CRITICO', 'AGOTADO']
        
        try:
            indice_anterior = estados_orden.index(estado_anterior)
            indice_nuevo = estados_orden.index(estado_stock.estado_semaforo)
        except ValueError:
            return
        
        # Si el nuevo estado es peor que el anterior
        if indice_nuevo > indice_anterior:
            # Determinar tipo de alerta
            if estado_stock.estado_semaforo == 'AGOTADO':
                tipo_alerta = 'STOCK_AGOTADO'
                prioridad = 'CRITICA'
                titulo = f"⚫ Stock AGOTADO: {producto.nombre}"
                mensaje = f"El producto {producto.nombre} se ha AGOTADO completamente."
            elif estado_stock.estado_semaforo == 'CRITICO':
                tipo_alerta = 'STOCK_CRITICO'
                prioridad = 'ALTA'
                titulo = f"🔴 Stock CRÍTICO: {producto.nombre}"
                
                if producto.tipo_inventario == 'QUINTAL':
                    mensaje = (
                        f"Stock crítico para {producto.nombre}. "
                        f"Solo queda {estado_stock.porcentaje_disponible:.1f}% del peso inicial. "
                        f"Peso disponible: {estado_stock.peso_total_disponible} {producto.unidad_medida_base.abreviatura}"
                    )
                else:
                    mensaje = (
                        f"Stock crítico para {producto.nombre}. "
                        f"Solo quedan {estado_stock.stock_actual} unidades "
                        f"(Mínimo: {estado_stock.stock_minimo})"
                    )
            elif estado_stock.estado_semaforo == 'BAJO':
                tipo_alerta = 'STOCK_BAJO'
                prioridad = 'MEDIA'
                titulo = f"🟡 Stock BAJO: {producto.nombre}"
                
                if producto.tipo_inventario == 'QUINTAL':
                    mensaje = (
                        f"Stock bajo para {producto.nombre}. "
                        f"Queda {estado_stock.porcentaje_disponible:.1f}% del peso inicial. "
                        f"Considere reabastecer pronto."
                    )
                else:
                    mensaje = (
                        f"Stock bajo para {producto.nombre}. "
                        f"Quedan {estado_stock.stock_actual} unidades. "
                        f"Considere reabastecer."
                    )
            else:
                return  # No generar alerta para estado NORMAL
            
            # Verificar si ya existe una alerta activa del mismo tipo
            alerta_existente = Alerta.objects.filter(
                producto=producto,
                tipo_alerta=tipo_alerta,
                estado='ACTIVA'
            ).exists()
            
            if not alerta_existente:
                alerta = Alerta.objects.create(
                    producto=producto,
                    estado_stock=estado_stock,
                    tipo_alerta=tipo_alerta,
                    prioridad=prioridad,
                    titulo=titulo,
                    mensaje=mensaje,
                    datos_adicionales={
                        'estado_anterior': estado_anterior,
                        'estado_nuevo': estado_stock.estado_semaforo,
                        'stock_actual': float(estado_stock.stock_actual if producto.tipo_inventario == 'NORMAL' else estado_stock.peso_total_disponible),
                        'fecha_deteccion': timezone.now().isoformat()
                    }
                )
                
                # Enviar notificación
                try:
                    from apps.notifications.services.notification_service import NotificationService
                    NotificationService.crear_notificacion_desde_alerta(alerta)
                except Exception as n_error:
                    print(f"Error al enviar notificación para alerta {alerta.id}: {str(n_error)}")
    
    @classmethod
    def calcular_todos_los_productos(cls):
        """
        Recalcula el estado de TODOS los productos del sistema
        Útil para comando batch o inicialización
        """
        from apps.inventory_management.models import Producto
        
        productos = Producto.objects.filter(activo=True)
        total = productos.count()
        procesados = 0
        errores = 0
        
        for producto in productos:
            try:
                cls.calcular_estado(producto)
                procesados += 1
            except Exception as e:
                print(f"Error procesando {producto.nombre}: {str(e)}")
                errores += 1
        
        return {
            'total': total,
            'procesados': procesados,
            'errores': errores
        }
    
    @classmethod
    def verificar_quintales_individuales(cls):
        """
        Verifica quintales individuales que están críticos
        Genera alertas específicas por quintal
        """
        from apps.inventory_management.models import Quintal
        from .models import Alerta, ConfiguracionAlerta
        
        config = ConfiguracionAlerta.get_configuracion()
        
        if not config.alertas_activas:
            return
        
        # Buscar quintales críticos
        quintales_criticos = Quintal.objects.filter(
            estado='DISPONIBLE',
            peso_actual__gt=0
        ).annotate(
            porcentaje=F('peso_actual') * 100.0 / F('peso_inicial')
        ).filter(
            porcentaje__lte=config.umbral_quintal_critico
        )
        
        for quintal in quintales_criticos:
            # Verificar si ya existe alerta
            alerta_existente = Alerta.objects.filter(
                quintal=quintal,
                tipo_alerta='QUINTAL_CRITICO',
                resuelta=False
            ).exists()
            
            if not alerta_existente:
                porcentaje = quintal.porcentaje_restante()
                
                alerta = Alerta.objects.create(
                    producto=quintal.producto,
                    quintal=quintal,
                    tipo_alerta='QUINTAL_CRITICO',
                    prioridad='ALTA',
                    titulo=f"🌾🔴 Quintal Crítico: {quintal.codigo_quintal}",
                    mensaje=(
                        f"El quintal {quintal.codigo_quintal} de {quintal.producto.nombre} "
                        f"tiene solo {porcentaje:.1f}% restante. "
                        f"Peso actual: {quintal.peso_actual} {quintal.unidad_medida.abreviatura}"
                    ),
                    datos_adicionales={
                        'codigo_quintal': quintal.codigo_quintal,
                        'porcentaje_restante': float(porcentaje),
                        'peso_actual': float(quintal.peso_actual),
                        'peso_inicial': float(quintal.peso_inicial)
                    }
                )
                
                # Enviar notificación
                try:
                    from apps.notifications.services.notification_service import NotificationService
                    NotificationService.crear_notificacion_desde_alerta(alerta)
                except Exception as n_error:
                    print(f"Error al enviar notificación para alerta quintal {alerta.id}: {str(n_error)}")
    
    @classmethod
    def verificar_proximos_vencer(cls):
        """
        Verifica productos próximos a vencer
        Genera alertas de vencimiento
        """
        from apps.inventory_management.models import Quintal
        from .models import Alerta, ConfiguracionAlerta
        
        config = ConfiguracionAlerta.get_configuracion()
        
        if not config.alertas_activas:
            return
        
        # Calcular fecha límite
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=config.dias_alerta_vencimiento)
        
        # Buscar quintales próximos a vencer
        quintales_por_vencer = Quintal.objects.filter(
            estado='DISPONIBLE',
            fecha_vencimiento__isnull=False,
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=fecha_limite
        )
        
        for quintal in quintales_por_vencer:
            # Verificar si ya existe alerta
            alerta_existente = Alerta.objects.filter(
                quintal=quintal,
                tipo_alerta='VENCIMIENTO_PROXIMO',
                resuelta=False
            ).exists()
            
            if not alerta_existente:
                dias_restantes = (quintal.fecha_vencimiento - hoy).days
                
                alerta = Alerta.objects.create(
                    producto=quintal.producto,
                    quintal=quintal,
                    tipo_alerta='VENCIMIENTO_PROXIMO',
                    prioridad='ALTA' if dias_restantes <= 3 else 'MEDIA',
                    titulo=f"⏰ Próximo a Vencer: {quintal.codigo_quintal}",
                    mensaje=(
                        f"El quintal {quintal.codigo_quintal} de {quintal.producto.nombre} "
                        f"vence en {dias_restantes} día(s) ({quintal.fecha_vencimiento.strftime('%d/%m/%Y')}). "
                        f"Peso disponible: {quintal.peso_actual} {quintal.unidad_medida.abreviatura}"
                    ),
                    datos_adicionales={
                        'codigo_quintal': quintal.codigo_quintal,
                        'fecha_vencimiento': quintal.fecha_vencimiento.isoformat(),
                        'dias_restantes': dias_restantes,
                        'peso_disponible': float(quintal.peso_actual)
                    }
                )

                # Enviar notificación
                try:
                    from apps.notifications.services.notification_service import NotificationService
                    NotificationService.crear_notificacion_desde_alerta(alerta)
                except Exception as n_error:
                    print(f"Error al enviar notificación para alerta vencimiento {alerta.id}: {str(n_error)}")


class AlertaManager:
    """
    Manager para gestión de alertas
    """
    
    @staticmethod
    def resolver_alertas_automaticamente():
        """
        Resuelve alertas que ya no son relevantes
        (ej: stock ya fue repuesto)
        """
        from .models import Alerta, EstadoStock
        from apps.inventory_management.models import Quintal
        
        # Resolver alertas de stock crítico/bajo si el estado mejoró
        alertas_stock = Alerta.objects.filter(
            estado='ACTIVA',
            tipo_alerta__in=['STOCK_CRITICO', 'STOCK_BAJO', 'STOCK_AGOTADO']
        )
        
        for alerta in alertas_stock:
            try:
                estado_actual = EstadoStock.objects.get(producto=alerta.producto)
                
                # Si el estado mejoró, resolver la alerta
                if alerta.tipo_alerta == 'STOCK_AGOTADO' and estado_actual.estado_semaforo != 'AGOTADO':
                    alerta.estado = 'RESUELTA'
                    alerta.notas_resolucion = "Stock repuesto automáticamente"
                    alerta.fecha_resuelta = timezone.now()
                    alerta.save()
                
                elif alerta.tipo_alerta == 'STOCK_CRITICO' and estado_actual.estado_semaforo in ['NORMAL', 'BAJO']:
                    alerta.estado = 'RESUELTA'
                    alerta.notas_resolucion = "Stock mejoró automáticamente"
                    alerta.fecha_resuelta = timezone.now()
                    alerta.save()
                
                elif alerta.tipo_alerta == 'STOCK_BAJO' and estado_actual.estado_semaforo == 'NORMAL':
                    alerta.estado = 'RESUELTA'
                    alerta.notas_resolucion = "Stock normalizado"
                    alerta.fecha_resuelta = timezone.now()
                    alerta.save()
            
            except EstadoStock.DoesNotExist:
                pass
        
        # Resolver alertas de quintales críticos si mejoraron
        alertas_quintales = Alerta.objects.filter(
            resuelta=False,
            tipo_alerta='QUINTAL_CRITICO',
            quintal__isnull=False
        )
        
        for alerta in alertas_quintales:
            quintal = alerta.quintal
            if quintal.estado == 'AGOTADO' or quintal.porcentaje_restante() > 15:
                alerta.estado = 'RESUELTA'
                alerta.notas_resolucion = "Quintal agotado o peso mejorado"
                alerta.fecha_resolucion = timezone.now()
                alerta.save()
        
        # Resolver alertas de vencimiento si ya venció o se agotó
        alertas_vencimiento = Alerta.objects.filter(
            resuelta=False,
            tipo_alerta='VENCIMIENTO_PROXIMO',
            quintal__isnull=False
        )
        
        for alerta in alertas_vencimiento:
            quintal = alerta.quintal
            if quintal.estado == 'AGOTADO' or quintal.peso_actual == 0:
                alerta.estado = 'RESUELTA'
                alerta.notas_resolucion = "Quintal vendido/agotado"
                alerta.fecha_resolucion = timezone.now()
                alerta.save()
    
    @staticmethod
    def limpiar_alertas_antiguas(dias=30):
        """
        Limpia alertas resueltas antiguas
        """
        from .models import Alerta
        
        fecha_limite = timezone.now() - timedelta(days=dias)
        
        alertas_antiguas = Alerta.objects.filter(
            estado__in=['RESUELTA', 'IGNORADA'],
            fecha_resolucion__lt=fecha_limite
        )
        
        cantidad = alertas_antiguas.count()
        alertas_antiguas.delete()
        
        return cantidad