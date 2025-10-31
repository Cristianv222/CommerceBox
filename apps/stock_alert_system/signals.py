# apps/stock_alert_system/signals.py

"""
Signals para actualizar automáticamente el sistema de alertas
Escucha cambios en inventario y ventas
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction
from .models import AlertaStock

# ============================================================================
# SIGNALS PARA QUINTALES
# ============================================================================

@receiver(post_save, sender='inventory_management.Quintal')
def quintal_actualizar_estado(sender, instance, created, **kwargs):
    """
    Después de guardar un quintal (crear o actualizar):
    - Recalcular estado del producto
    """
    from .status_calculator import StatusCalculator
    
    # Recalcular estado del producto
    transaction.on_commit(
        lambda: StatusCalculator.calcular_estado(instance.producto)
    )


@receiver(post_save, sender='inventory_management.MovimientoQuintal')
def movimiento_quintal_actualizar_estado(sender, instance, created, **kwargs):
    """
    Después de un movimiento de quintal:
    - Recalcular estado del producto
    - Verificar si el quintal individual necesita alerta
    """
    from .status_calculator import StatusCalculator
    
    if created:
        quintal = instance.quintal
        
        # Recalcular estado del producto
        transaction.on_commit(
            lambda: StatusCalculator.calcular_estado(quintal.producto)
        )


# ============================================================================
# SIGNALS PARA PRODUCTOS NORMALES
# ============================================================================

@receiver(post_save, sender='inventory_management.ProductoNormal')
def producto_normal_actualizar_estado(sender, instance, created, **kwargs):
    """
    Después de guardar producto normal:
    - Recalcular estado
    """
    from .status_calculator import StatusCalculator
    
    transaction.on_commit(
        lambda: StatusCalculator.calcular_estado(instance.producto)
    )


@receiver(post_save, sender='inventory_management.MovimientoInventario')
def movimiento_inventario_actualizar_estado(sender, instance, created, **kwargs):
    """
    Después de un movimiento de inventario:
    - Recalcular estado del producto
    """
    from .status_calculator import StatusCalculator
    
    if created:
        producto_normal = instance.producto_normal
        
        transaction.on_commit(
            lambda: StatusCalculator.calcular_estado(producto_normal.producto)
        )


# ============================================================================
# SIGNALS PARA VENTAS
# ============================================================================

@receiver(post_save, sender='sales_management.DetalleVenta')
def venta_actualizar_estado(sender, instance, created, **kwargs):
    """
    Después de crear un detalle de venta:
    - Recalcular estado del producto vendido
    """
    from .status_calculator import StatusCalculator
    
    if created:
        transaction.on_commit(
            lambda: StatusCalculator.calcular_estado(instance.producto)
        )


@receiver(post_save, sender='sales_management.Venta')
def venta_anulada_actualizar_estado(sender, instance, **kwargs):
    """
    Si una venta se anula:
    - Recalcular estado de todos los productos de la venta
    """
    from .status_calculator import StatusCalculator
    
    if instance.estado == 'ANULADA':
        # Recalcular para cada producto de la venta
        for detalle in instance.detalles.all():
            transaction.on_commit(
                lambda producto=detalle.producto: StatusCalculator.calcular_estado(producto)
            )


# ============================================================================
# SIGNALS PARA PRODUCTO MAESTRO
# ============================================================================

@receiver(post_save, sender='inventory_management.Producto')
def producto_crear_estado_inicial(sender, instance, created, **kwargs):
    """
    Cuando se crea un producto:
    - Crear su EstadoStock inicial
    """
    from .models import EstadoStock
    
    if created:
        # Crear estado de stock inicial
        EstadoStock.objects.get_or_create(
            producto=instance,
            defaults={
                'tipo_inventario': instance.tipo_inventario,
                'estado_semaforo': 'AGOTADO',  # Inicialmente agotado hasta que se agregue stock
                'requiere_atencion': False
            }
        )


# ============================================================================
# SIGNALS PARA AUTO-RESOLVER ALERTAS
# ============================================================================

@receiver(post_save, sender='stock_alert_system.EstadoStock')
def estado_stock_resolver_alertas(sender, instance, **kwargs):
    """
    Cuando cambia el estado de stock:
    - Resolver alertas automáticamente si mejora el estado
    """
    from .status_calculator import AlertaManager
    
    # Ejecutar en background para no bloquear
    transaction.on_commit(
        lambda: AlertaManager.resolver_alertas_automaticamente()
    )


# ============================================================================
# INICIALIZACIÓN AL ARRANCAR LA APP
# ============================================================================

def inicializar_estados_stock():
    """
    Función para inicializar estados de stock para todos los productos
    Se ejecuta al cargar la app
    """
    from .models import EstadoStock, ConfiguracionAlerta
    from apps.inventory_management.models import Producto
    from .status_calculator import StatusCalculator
    
    # Asegurar que existe la configuración
    ConfiguracionAlerta.get_configuracion()
    
    # Crear EstadoStock para productos que no lo tengan
    productos_sin_estado = Producto.objects.filter(
        activo=True,
        estado_stock__isnull=True
    )
    
    for producto in productos_sin_estado:
        EstadoStock.objects.get_or_create(
            producto=producto,
            defaults={
                'tipo_inventario': producto.tipo_inventario,
                'estado_semaforo': 'NORMAL'
            }
        )
    
    print(f"✅ Sistema de alertas inicializado. Productos procesados: {productos_sin_estado.count()}")


# ============================================================================
# SIGNAL PARA COMPRAS (Cuando se recibe inventario)
# ============================================================================

@receiver(post_save, sender='inventory_management.Compra')
def compra_recibida_actualizar_estados(sender, instance, **kwargs):
    """
    Cuando una compra se marca como RECIBIDA:
    - Recalcular estados de todos los productos de la compra
    """
    from .status_calculator import StatusCalculator
    
    if instance.estado == 'RECIBIDA':
        # Obtener productos únicos de la compra
        productos = set()
        for detalle in instance.detalles.all():
            productos.add(detalle.producto)
        
        # Recalcular cada producto
        for producto in productos:
            transaction.on_commit(
                lambda p=producto: StatusCalculator.calcular_estado(p)
            )
# Al final del archivo apps/stock_alert_system/signals.py


@receiver(post_save, sender=AlertaStock)
def crear_notificacion_desde_alerta(sender, instance, created, **kwargs):
    """
    Cuando se crea una nueva alerta, automáticamente crear notificación
    """
    if created and not instance.resuelta:
        from apps.notifications.services.notification_service import NotificationService
        
        try:
            NotificationService.crear_notificacion_desde_alerta(instance)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al crear notificación desde alerta: {str(e)}")