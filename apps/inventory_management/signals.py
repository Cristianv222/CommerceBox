# apps/inventory_management/signals.py

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from .models import (
    Quintal, MovimientoQuintal, ProductoNormal,
    MovimientoInventario, Producto, DetalleCompra
)


# ============================================================================
# SEÑALES PARA QUINTALES
# ============================================================================

@receiver(pre_save, sender=Quintal)
def quintal_pre_save(sender, instance, **kwargs):
    """
    Antes de guardar un quintal:
    1. Calcular costo_por_unidad automáticamente
    2. Actualizar estado según peso_actual
    3. Validar que peso_actual no sea negativo
    """
    # 1. Calcular costo por unidad si no existe
    if instance.peso_inicial and instance.peso_inicial > 0:
        if not instance.costo_por_unidad or instance.costo_por_unidad == 0:
            instance.costo_por_unidad = instance.costo_total / instance.peso_inicial
    
    # 2. Validar que peso_actual no sea negativo
    if instance.peso_actual < 0:
        instance.peso_actual = Decimal('0.000')
    
    # 3. Actualizar estado automáticamente
    if instance.peso_actual <= 0:
        instance.estado = 'AGOTADO'
        instance.peso_actual = Decimal('0.000')
    elif instance.estado == 'AGOTADO' and instance.peso_actual > 0:
        instance.estado = 'DISPONIBLE'


@receiver(post_save, sender=Quintal)
def quintal_post_save(sender, instance, created, **kwargs):
    """
    Después de crear un quintal:
    - Registrar movimiento inicial de ENTRADA automáticamente
    """
    if created:
        # Crear movimiento de entrada inicial
        MovimientoQuintal.objects.create(
            quintal=instance,
            tipo_movimiento='ENTRADA',
            peso_movimiento=instance.peso_inicial,
            peso_antes=Decimal('0.000'),
            peso_despues=instance.peso_inicial,
            unidad_medida=instance.unidad_medida,
            usuario=instance.usuario_registro,
            observaciones=f"Entrada inicial - Recepción de quintal desde {instance.proveedor.nombre_comercial}"
        )


# ============================================================================
# SEÑALES PARA PRODUCTOS NORMALES
# ============================================================================

@receiver(post_save, sender=ProductoNormal)
def producto_normal_post_save(sender, instance, created, **kwargs):
    """
    Después de crear o actualizar producto normal:
    1. Si es nuevo con stock inicial, registrar movimiento
    2. Validar que stock_actual no sea negativo
    """
    if created and instance.stock_actual > 0:
        # Buscar usuario del sistema (admin)
        from apps.authentication.models import Usuario
        usuario_sistema = Usuario.objects.filter(
            rol__codigo='ADMIN'
        ).first()
        
        if usuario_sistema:
            MovimientoInventario.objects.create(
                producto_normal=instance,
                tipo_movimiento='ENTRADA_AJUSTE',
                cantidad=instance.stock_actual,
                stock_antes=0,
                stock_despues=instance.stock_actual,
                costo_unitario=instance.costo_unitario,
                costo_total=instance.stock_actual * instance.costo_unitario,
                usuario=usuario_sistema,
                observaciones="Stock inicial al crear producto"
            )


@receiver(pre_save, sender=ProductoNormal)
def producto_normal_pre_save(sender, instance, **kwargs):
    """
    Antes de guardar producto normal:
    - Validar que stock no sea negativo
    """
    if instance.stock_actual < 0:
        instance.stock_actual = 0


# ============================================================================
# SEÑALES PARA PRODUCTOS (Maestro)
# ============================================================================

@receiver(post_save, sender=Producto)
def producto_post_save(sender, instance, created, **kwargs):
    """
    Después de crear un producto:
    1. Si es tipo NORMAL, crear su ProductoNormal asociado
    2. Generar código de barras si no existe
    """
    if created:
        # Si es producto normal y no tiene inventario, crearlo
        if instance.tipo_inventario == 'NORMAL':
            ProductoNormal.objects.get_or_create(
                producto=instance,
                defaults={
                    'stock_actual': 0,
                    'stock_minimo': 10,
                    'costo_unitario': instance.precio_unitario or Decimal('0')
                }
            )


@receiver(pre_save, sender=Producto)
def producto_pre_save(sender, instance, **kwargs):
    """
    Antes de guardar producto:
    1. Generar código de barras si está vacío
    2. Validar campos según tipo de inventario
    """
    # Generar código de barras si está vacío
    if not instance.codigo_barras:
        from .utils.barcode_generator import BarcodeGenerator
        instance.codigo_barras = BarcodeGenerator.generar_codigo_producto(
            categoria=instance.categoria,
            tipo_inventario=instance.tipo_inventario
        )


# ============================================================================
# SEÑALES PARA COMPRAS
# ============================================================================

@receiver(post_save, sender=DetalleCompra)
def detalle_compra_post_save(sender, instance, created, **kwargs):
    """
    Después de guardar un detalle de compra:
    - Recalcular totales de la compra
    """
    if instance.compra:
        instance.compra.calcular_totales()


@receiver(post_delete, sender=DetalleCompra)
def detalle_compra_post_delete(sender, instance, **kwargs):
    """
    Después de eliminar un detalle:
    - Recalcular totales de la compra
    """
    if instance.compra:
        instance.compra.calcular_totales()


# ============================================================================
# SEÑALES PARA ALERTAS DE STOCK
# ============================================================================

@receiver(post_save, sender=MovimientoQuintal)
def verificar_alerta_quintal(sender, instance, created, **kwargs):
    """
    Después de un movimiento de quintal:
    - Verificar si el quintal está en estado crítico
    - Generar alerta si es necesario
    """
    if created and instance.tipo_movimiento == 'VENTA':
        quintal = instance.quintal
        porcentaje = quintal.porcentaje_restante()
        
        # Si el quintal tiene menos del 10% restante
        if porcentaje <= 10 and porcentaje > 0:
            # Aquí se podría crear una notificación
            # Por ahora solo un log
            print(f"⚠️ ALERTA: Quintal {quintal.codigo_unico} está en {porcentaje:.1f}% restante")


@receiver(post_save, sender=MovimientoInventario)
def verificar_alerta_stock_normal(sender, instance, created, **kwargs):
    """
    Después de un movimiento de inventario:
    - Verificar si el stock está crítico
    - Generar alerta si es necesario
    """
    if created and instance.tipo_movimiento == 'SALIDA_VENTA':
        producto_normal = instance.producto_normal
        
        # Si el stock está en nivel crítico
        if producto_normal.necesita_reorden():
            print(f"⚠️ ALERTA: {producto_normal.producto.nombre} necesita reorden. Stock: {producto_normal.stock_actual}")


# ============================================================================
# SEÑAL PARA ACTUALIZAR FECHA DE VENCIMIENTO
# ============================================================================

@receiver(pre_save, sender=Quintal)
def verificar_vencimiento_quintal(sender, instance, **kwargs):
    """
    Antes de guardar quintal:
    - Verificar si está vencido y cambiar estado
    """
    if instance.fecha_vencimiento:
        if instance.fecha_vencimiento < timezone.now().date():
            if instance.estado != 'DAÑADO':
                instance.estado = 'DAÑADO'
                print(f"⚠️ Quintal {instance.codigo_unico} marcado como DAÑADO por vencimiento")