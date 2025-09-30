# apps/inventory_management/models.py

from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from django.db.models import Manager, Sum, Q, F
from decimal import Decimal
import uuid


# ============================================================================
# MODELOS BASE COMPARTIDOS (Para ambos tipos de inventario)
# ============================================================================

class Categoria(models.Model):
    """
    Categorías de productos (aplica para quintales y productos normales)
    Ejemplos: Granos, Enlatados, Lácteos, Limpieza
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    
    # Configuración comercial
    margen_ganancia_sugerido = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.00,
        help_text="Porcentaje de margen sugerido (%)"
    )
    descuento_maximo_permitido = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Descuento máximo permitido (%)"
    )
    
    # Control
    activa = models.BooleanField(default=True)
    orden = models.IntegerField(default=0, help_text="Orden de visualización")
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['orden', 'nombre']
        db_table = 'inv_categoria'
    
    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    """
    Proveedores de productos (quintales y normales)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Información comercial
    nombre_comercial = models.CharField(max_length=200)
    razon_social = models.CharField(max_length=200, blank=True)
    ruc_nit = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^\d{10,20}$', 'RUC/NIT inválido')]
    )
    
    # Contacto
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    
    # Información comercial
    dias_credito = models.IntegerField(default=0, help_text="Días de crédito otorgados")
    limite_credito = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Límite de crédito ($)"
    )
    
    # Control
    activo = models.BooleanField(default=True)
    
    # Auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre_comercial']
        db_table = 'inv_proveedor'
    
    def __str__(self):
        return self.nombre_comercial


class UnidadMedida(models.Model):
    """
    Unidades de medida para quintales (kg, lb, arroba, quintal)
    Sistema de conversión automática
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    nombre = models.CharField(max_length=50, unique=True)
    abreviatura = models.CharField(max_length=10)
    
    # Factor de conversión (base: kilogramo = 1.0)
    factor_conversion_kg = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        help_text="Factor de conversión a kilogramos (kg como base)"
    )
    
    # Configuración
    es_sistema_metrico = models.BooleanField(default=True)
    orden_display = models.IntegerField(default=0)
    activa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Unidad de Medida'
        verbose_name_plural = 'Unidades de Medida'
        ordering = ['orden_display', 'nombre']
        db_table = 'inv_unidad_medida'
    
    def __str__(self):
        return f"{self.nombre} ({self.abreviatura})"
    
    def convertir_a(self, cantidad, unidad_destino):
        """
        Convierte una cantidad de esta unidad a otra unidad
        
        Ejemplo:
            libra = UnidadMedida.objects.get(abreviatura='lb')
            kg = UnidadMedida.objects.get(abreviatura='kg')
            libra.convertir_a(10, kg)  # Convierte 10 lb a kg
        """
        cantidad_en_kg = cantidad * self.factor_conversion_kg
        return cantidad_en_kg / unidad_destino.factor_conversion_kg


# ============================================================================
# PRODUCTO MAESTRO (Unifica quintales y productos normales)
# ============================================================================

class Producto(models.Model):
    """
    Catálogo maestro de productos
    Puede ser tipo QUINTAL (a granel) o NORMAL (unidades)
    """
    
    TIPO_INVENTARIO_CHOICES = [
        ('QUINTAL', 'Quintal - A granel (se vende por peso)'),
        ('NORMAL', 'Normal - Unidades completas'),
    ]
    
    # Identificadores
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_barras = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Código de barras o código interno (CBX-PRD-XXXX)"
    )
    
    # Información básica
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    
    # Relaciones
    categoria = models.ForeignKey(
        'Categoria',
        on_delete=models.PROTECT,
        related_name='productos'
    )
    proveedor = models.ForeignKey(
        'Proveedor',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='productos'
    )
    
    # ⚖️ TIPO DE INVENTARIO (Lo que diferencia el comportamiento)
    tipo_inventario = models.CharField(
        max_length=20,
        choices=TIPO_INVENTARIO_CHOICES,
        default='NORMAL',
        db_index=True
    )
    
    # ==========================================
    # CAMPOS PARA QUINTALES (tipo_inventario='QUINTAL')
    # ==========================================
    unidad_medida_base = models.ForeignKey(
        'UnidadMedida',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Unidad base para quintales (kg, lb, etc)"
    )
    precio_por_unidad_peso = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio por unidad de peso (ej: $2.50/lb)"
    )
    peso_base_quintal = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Peso estándar de un quintal (ej: 100 lb)"
    )
    
    # ==========================================
    # CAMPOS PARA PRODUCTOS NORMALES (tipo_inventario='NORMAL')
    # ==========================================
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio por unidad completa"
    )
    
    # Imagen
    imagen = models.ImageField(
        upload_to='productos/',
        null=True,
        blank=True
    )
    
    # Control
    activo = models.BooleanField(default=True)
    
    # Auditoría
    usuario_registro = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='productos_registrados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
        db_table = 'inv_producto'
        indexes = [
            models.Index(fields=['codigo_barras']),
            models.Index(fields=['tipo_inventario', 'activo']),
            models.Index(fields=['categoria', 'activo']),
        ]
    
    def __str__(self):
        tipo_icon = "🌾" if self.tipo_inventario == 'QUINTAL' else "📦"
        return f"{tipo_icon} {self.nombre} ({self.codigo_barras})"
    
    def es_quintal(self):
        """Verifica si es producto a granel"""
        return self.tipo_inventario == 'QUINTAL'
    
    def es_normal(self):
        """Verifica si es producto normal"""
        return self.tipo_inventario == 'NORMAL'
    
    def get_precio_venta(self):
        """Retorna el precio según el tipo"""
        if self.es_quintal():
            return self.precio_por_unidad_peso
        return self.precio_unitario


# ============================================================================
# MANAGERS PERSONALIZADOS
# ============================================================================

class QuintalManager(Manager):
    """Manager personalizado para Quintales con métodos útiles"""
    
    def disponibles(self):
        """Retorna solo quintales disponibles con peso > 0"""
        return self.filter(
            estado='DISPONIBLE',
            peso_actual__gt=0
        )
    
    def por_producto(self, producto):
        """Quintales de un producto específico"""
        return self.filter(producto=producto)
    
    def fifo(self, producto):
        """Quintales ordenados por FIFO (más antiguos primero)"""
        return self.disponibles().filter(
            producto=producto
        ).order_by('fecha_recepcion')
    
    def peso_total_disponible(self, producto):
        """Calcula el peso total disponible de un producto"""
        return self.disponibles().filter(
            producto=producto
        ).aggregate(
            total=Sum('peso_actual')
        )['total'] or Decimal('0')
    
    def proximos_a_vencer(self, dias=7):
        """Quintales que vencen en X días"""
        from datetime import timedelta
        fecha_limite = timezone.now().date() + timedelta(days=dias)
        return self.disponibles().filter(
            fecha_vencimiento__lte=fecha_limite
        )
    
    def criticos(self, porcentaje=10):
        """Quintales con menos del X% de peso restante"""
        return self.disponibles().filter(
            peso_actual__lte=F('peso_inicial') * (porcentaje / 100)
        )


class ProductoNormalManager(Manager):
    """Manager personalizado para Productos Normales"""
    
    def con_stock(self):
        """Productos con stock disponible"""
        return self.filter(stock_actual__gt=0)
    
    def sin_stock(self):
        """Productos agotados"""
        return self.filter(stock_actual=0)
    
    def stock_critico(self):
        """Productos con stock crítico (stock <= stock_minimo)"""
        return self.filter(stock_actual__lte=F('stock_minimo'))
    
    def stock_bajo(self):
        """Productos con stock bajo (stock <= stock_minimo × 2)"""
        return self.filter(
            stock_actual__gt=F('stock_minimo'),
            stock_actual__lte=F('stock_minimo') * 2
        )
    
    def necesitan_reorden(self):
        """Productos que necesitan reposición"""
        return self.stock_critico()
    
    def valor_total_inventario(self):
        """Calcula el valor total del inventario"""
        return self.aggregate(
            valor_total=Sum(F('stock_actual') * F('costo_unitario'))
        )['valor_total'] or Decimal('0')


# ============================================================================
# MODELOS PARA INVENTARIO DE QUINTALES (A Granel)
# ============================================================================

class Quintal(models.Model):
    """
    Cada quintal/saco físico individual que entra al inventario
    Sistema FIFO: Se vende del más antiguo primero
    Trazabilidad completa: De dónde viene, cuánto queda
    """
    
    ESTADO_CHOICES = [
        ('DISPONIBLE', '🟢 Disponible - Tiene peso disponible'),
        ('AGOTADO', '⚫ Agotado - Peso en cero'),
        ('DAÑADO', '🔴 Dañado - Producto no vendible'),
    ]
    
    # Identificadores
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_unico = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Código único del quintal (ej: CBX-QNT-00001)"
    )
    
    # Relaciones
    producto = models.ForeignKey(
        'Producto',
        on_delete=models.PROTECT,
        limit_choices_to={'tipo_inventario': 'QUINTAL'},
        related_name='quintales'
    )
    proveedor = models.ForeignKey(
        'Proveedor',
        on_delete=models.PROTECT
    )
    
    # ⚖️ CONTROL DE PESO (Núcleo del sistema)
    peso_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text="Peso al recibir el quintal (en unidad base del producto)"
    )
    peso_actual = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.000'))],
        help_text="Peso disponible actual (va disminuyendo con ventas)"
    )
    unidad_medida = models.ForeignKey(
        'UnidadMedida',
        on_delete=models.PROTECT
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='DISPONIBLE',
        db_index=True
    )
    
    # 💰 COSTOS (Para cálculo de rentabilidad)
    costo_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Costo total de compra de este quintal"
    )
    costo_por_unidad = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Costo por unidad de peso (calculado: costo_total / peso_inicial)"
    )
    
    # 📅 TRAZABILIDAD
    fecha_recepcion = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Fecha de ingreso al inventario (importante para FIFO)"
    )
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento del producto"
    )
    lote_proveedor = models.CharField(
        max_length=50,
        blank=True,
        help_text="Número de lote del proveedor"
    )
    numero_factura_compra = models.CharField(
        max_length=50,
        blank=True
    )
    origen = models.CharField(
        max_length=200,
        blank=True,
        help_text="Origen del producto (ej: Productor local, Importado de USA)"
    )
    
    # Auditoría
    usuario_registro = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='quintales_registrados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Manager personalizado
    objects = QuintalManager()
    
    class Meta:
        verbose_name = 'Quintal'
        verbose_name_plural = 'Quintales'
        ordering = ['fecha_recepcion']  # FIFO: Primero el más antiguo
        db_table = 'inv_quintal'
        indexes = [
            models.Index(fields=['codigo_unico']),
            models.Index(fields=['producto', 'estado', 'fecha_recepcion']),
            models.Index(fields=['estado', 'peso_actual']),
        ]
    
    def __str__(self):
        return f"{self.codigo_unico} - {self.producto.nombre} ({self.peso_actual}/{self.peso_inicial} {self.unidad_medida.abreviatura})"
    
    def porcentaje_restante(self):
        """Calcula el porcentaje de peso restante"""
        if self.peso_inicial > 0:
            return (self.peso_actual / self.peso_inicial) * 100
        return 0
    
    def peso_vendido(self):
        """Calcula cuánto peso se ha vendido"""
        return self.peso_inicial - self.peso_actual
    
    def esta_critico(self, umbral_critico=10):
        """Verifica si el quintal está en estado crítico (menos del X% restante)"""
        return self.porcentaje_restante() <= umbral_critico
    
    def save(self, *args, **kwargs):
        # Calcular costo por unidad automáticamente si no existe
        if not self.costo_por_unidad and self.peso_inicial > 0:
            self.costo_por_unidad = self.costo_total / self.peso_inicial
        
        # Actualizar estado automáticamente según peso
        if self.peso_actual <= 0:
            self.estado = 'AGOTADO'
            self.peso_actual = Decimal('0.000')
        
        super().save(*args, **kwargs)


class MovimientoQuintal(models.Model):
    """
    Registro de auditoría de cada movimiento de peso en un quintal
    Permite trazabilidad completa: Qué pasó, cuándo, quién, cuánto
    """
    
    TIPO_MOVIMIENTO_CHOICES = [
        ('ENTRADA', '📥 Entrada inicial (recepción)'),
        ('VENTA', '🛒 Salida por venta'),
        ('AJUSTE_POSITIVO', '➕ Ajuste positivo (corrección suma)'),
        ('AJUSTE_NEGATIVO', '➖ Ajuste negativo (corrección resta)'),
        ('MERMA', '💔 Merma/Pérdida'),
        ('DEVOLUCION', '↩️ Devolución de cliente'),
    ]
    
    # Identificadores
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación al quintal
    quintal = models.ForeignKey(
        'Quintal',
        on_delete=models.CASCADE,
        related_name='movimientos'
    )
    
    # Tipo de movimiento
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES,
        db_index=True
    )
    
    # ⚖️ PESOS (El corazón de la auditoría)
    peso_movimiento = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Cantidad del movimiento (+ entrada, - salida)"
    )
    peso_antes = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Peso del quintal ANTES del movimiento"
    )
    peso_despues = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Peso del quintal DESPUÉS del movimiento"
    )
    unidad_medida = models.ForeignKey(
        'UnidadMedida',
        on_delete=models.PROTECT
    )
    
    # Referencias (si aplica)
    venta = models.ForeignKey(
        'sales_management.Venta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Venta asociada si el movimiento es por venta"
    )
    
    # Auditoría
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT
    )
    fecha_movimiento = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Movimiento de Quintal'
        verbose_name_plural = 'Movimientos de Quintales'
        ordering = ['-fecha_movimiento']
        db_table = 'inv_movimiento_quintal'
        indexes = [
            models.Index(fields=['quintal', '-fecha_movimiento']),
            models.Index(fields=['tipo_movimiento', '-fecha_movimiento']),
        ]
    
    def __str__(self):
        signo = "+" if self.peso_movimiento >= 0 else ""
        return f"{self.get_tipo_movimiento_display()} - {signo}{self.peso_movimiento} {self.unidad_medida.abreviatura}"


# ============================================================================
# MODELOS PARA INVENTARIO NORMAL (Unidades Completas)
# ============================================================================

class ProductoNormal(models.Model):
    """
    Inventario tradicional por unidades
    Un solo registro por producto (a diferencia de quintales que son múltiples)
    """
    
    # Identificadores
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación al producto maestro (OneToOne porque es un solo registro)
    producto = models.OneToOneField(
        'Producto',
        on_delete=models.PROTECT,
        limit_choices_to={'tipo_inventario': 'NORMAL'},
        related_name='inventario_normal'
    )
    
    # 📊 STOCK (Núcleo del sistema)
    stock_actual = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Unidades disponibles en inventario"
    )
    stock_minimo = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0)],
        help_text="Alerta cuando el stock baja de este valor (🟡 Amarillo)"
    )
    stock_maximo = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Stock máximo recomendado"
    )
    
    # 💰 COSTOS
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Costo promedio ponderado por unidad"
    )
    
    # 📦 INFORMACIÓN ADICIONAL
    lote = models.CharField(
        max_length=50,
        blank=True,
        help_text="Número de lote actual"
    )
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True
    )
    ubicacion_almacen = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ubicación física (ej: Pasillo 3, Estante B, Nivel 2)"
    )
    
    # Auditoría
    fecha_ultima_entrada = models.DateTimeField(null=True, blank=True)
    fecha_ultima_salida = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Manager personalizado
    objects = ProductoNormalManager()
    
    class Meta:
        verbose_name = 'Producto Normal'
        verbose_name_plural = 'Productos Normales'
        db_table = 'inv_producto_normal'
        indexes = [
            models.Index(fields=['stock_actual']),
            models.Index(fields=['producto', 'stock_actual']),
        ]
    
    def __str__(self):
        return f"{self.producto.nombre} - Stock: {self.stock_actual} unidades"
    
    def valor_inventario(self):
        """Calcula el valor total del inventario (stock × costo)"""
        return self.stock_actual * self.costo_unitario
    
    def estado_stock(self):
        """
        Retorna el estado del stock para sistema de semáforos
        🟢 NORMAL: stock > stock_minimo × 2
        🟡 BAJO: stock entre stock_minimo y stock_minimo × 2
        🔴 CRITICO: stock <= stock_minimo
        ⚫ AGOTADO: stock = 0
        """
        if self.stock_actual == 0:
            return 'AGOTADO'
        elif self.stock_actual <= self.stock_minimo:
            return 'CRITICO'
        elif self.stock_actual <= (self.stock_minimo * 2):
            return 'BAJO'
        else:
            return 'NORMAL'
    
    def necesita_reorden(self):
        """Verifica si necesita reposición"""
        return self.stock_actual <= self.stock_minimo
    
    def porcentaje_stock(self):
        """Calcula % de stock vs máximo"""
        if self.stock_maximo and self.stock_maximo > 0:
            return (self.stock_actual / self.stock_maximo) * 100
        return 0


class MovimientoInventario(models.Model):
    """
    Registro de auditoría de movimientos de inventario de productos normales
    Cada entrada o salida queda registrada para trazabilidad
    """
    
    TIPO_MOVIMIENTO_CHOICES = [
        ('ENTRADA_COMPRA', '📥 Entrada por compra'),
        ('ENTRADA_DEVOLUCION', '↩️ Entrada por devolución de cliente'),
        ('ENTRADA_AJUSTE', '➕ Entrada por ajuste de inventario'),
        ('SALIDA_VENTA', '🛒 Salida por venta'),
        ('SALIDA_DEVOLUCION', '↪️ Salida por devolución a proveedor'),
        ('SALIDA_MERMA', '💔 Salida por merma/daño'),
        ('SALIDA_AJUSTE', '➖ Salida por ajuste de inventario'),
    ]
    
    # Identificadores
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación
    producto_normal = models.ForeignKey(
        'ProductoNormal',
        on_delete=models.CASCADE,
        related_name='movimientos'
    )
    
    # Tipo de movimiento
    tipo_movimiento = models.CharField(
        max_length=30,
        choices=TIPO_MOVIMIENTO_CHOICES,
        db_index=True
    )
    
    # 📊 CANTIDADES (+ entrada, - salida)
    cantidad = models.IntegerField(
        help_text="Cantidad de unidades (positivo = entrada, negativo = salida)"
    )
    stock_antes = models.IntegerField(
        help_text="Stock ANTES del movimiento"
    )
    stock_despues = models.IntegerField(
        help_text="Stock DESPUÉS del movimiento"
    )
    
    # 💰 COSTOS
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Costo unitario al momento del movimiento"
    )
    costo_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="cantidad × costo_unitario"
    )
    
    # Referencias (si aplica)
    venta = models.ForeignKey(
        'sales_management.Venta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    compra = models.ForeignKey(
        'inventory_management.Compra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Referencia a compra (si se implementa módulo de compras)"
    )
    
    # Auditoría
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT
    )
    fecha_movimiento = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha_movimiento']
        db_table = 'inv_movimiento_inventario'
        indexes = [
            models.Index(fields=['producto_normal', '-fecha_movimiento']),
            models.Index(fields=['tipo_movimiento', '-fecha_movimiento']),
            models.Index(fields=['usuario', '-fecha_movimiento']),
        ]
    
    def __str__(self):
        signo = "+" if self.cantidad >= 0 else ""
        return f"{self.get_tipo_movimiento_display()} - {signo}{self.cantidad} unidades"
    
    def es_entrada(self):
        """Verifica si es movimiento de entrada"""
        return self.cantidad > 0
    
    def es_salida(self):
        """Verifica si es movimiento de salida"""
        return self.cantidad < 0


# ============================================================================
# MODELO DE COMPRAS (Opcional - Para registro de compras a proveedores)
# ============================================================================

class Compra(models.Model):
    """
    Registro de compras a proveedores
    Puede incluir quintales y productos normales en la misma compra
    """
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de recibir'),
        ('RECIBIDA', 'Recibida completamente'),
        ('PARCIAL', 'Recibida parcialmente'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    # Identificadores
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_compra = models.CharField(
        max_length=20,
        unique=True,
        help_text="Número interno de compra (ej: COM-2025-00001)"
    )
    
    # Relación
    proveedor = models.ForeignKey(
        'Proveedor',
        on_delete=models.PROTECT,
        related_name='compras'
    )
    
    # Información de la compra
    numero_factura = models.CharField(max_length=50, blank=True)
    fecha_compra = models.DateField(default=timezone.now)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    
    # 💰 TOTALES
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    impuestos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        db_index=True
    )
    
    # Auditoría
    usuario_registro = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='compras_registradas'
    )
    usuario_recepcion = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='compras_recibidas'
    )
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-fecha_compra']
        db_table = 'inv_compra'
        indexes = [
            models.Index(fields=['numero_compra']),
            models.Index(fields=['proveedor', '-fecha_compra']),
            models.Index(fields=['estado', '-fecha_compra']),
        ]
    
    def __str__(self):
        return f"{self.numero_compra} - {self.proveedor.nombre_comercial} - ${self.total}"
    
    def calcular_totales(self):
        """Recalcula los totales de la compra basado en los detalles"""
        from django.db.models import Sum
        self.subtotal = self.detalles.aggregate(
            total=Sum('subtotal')
        )['total'] or Decimal('0')
        self.total = self.subtotal - self.descuento + self.impuestos
        self.save()


class DetalleCompra(models.Model):
    """
    Detalle de cada producto en una compra
    Puede ser quintal o producto normal
    """
    
    # Identificadores
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relaciones
    compra = models.ForeignKey(
        'Compra',
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        'Producto',
        on_delete=models.PROTECT
    )
    
    # Para QUINTALES
    peso_comprado = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Peso comprado si es quintal"
    )
    unidad_medida = models.ForeignKey(
        'UnidadMedida',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    # Para PRODUCTOS NORMALES
    cantidad_unidades = models.IntegerField(
        null=True,
        blank=True,
        help_text="Cantidad de unidades si es producto normal"
    )
    
    # 💰 PRECIOS
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Costo por unidad de peso o por unidad completa"
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    # Referencias creadas al recibir
    quintal_creado = models.ForeignKey(
        'Quintal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Quintal creado al recibir esta compra"
    )
    
    # Control
    recibido = models.BooleanField(
        default=False,
        help_text="Indica si este detalle ya fue recibido en inventario"
    )
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalles de Compra'
        db_table = 'inv_detalle_compra'
    
    def __str__(self):
        if self.producto.es_quintal():
            return f"{self.producto.nombre} - {self.peso_comprado} {self.unidad_medida.abreviatura}"
        return f"{self.producto.nombre} - {self.cantidad_unidades} unidades"
    
    def save(self, *args, **kwargs):
        # Calcular subtotal según tipo de producto
        if self.producto.es_quintal() and self.peso_comprado:
            self.subtotal = self.peso_comprado * self.costo_unitario
        elif self.producto.es_normal() and self.cantidad_unidades:
            self.subtotal = self.cantidad_unidades * self.costo_unitario
        super().save(*args, **kwargs)


# ============================================================================
# MODELOS PARA CONVERSIÓN DE UNIDADES (Helper)
# ============================================================================

class ConversionUnidad(models.Model):
    """
    Tabla de conversiones predefinidas para facilitar cálculos
    Ejemplos: 1 quintal = 100 libras, 1 arroba = 25 libras
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Unidades
    unidad_origen = models.ForeignKey(
        'UnidadMedida',
        on_delete=models.CASCADE,
        related_name='conversiones_origen'
    )
    unidad_destino = models.ForeignKey(
        'UnidadMedida',
        on_delete=models.CASCADE,
        related_name='conversiones_destino'
    )
    
    # Factor de conversión directo
    factor_conversion = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        help_text="Factor para convertir origen a destino"
    )
    
    # Información adicional
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Ej: 1 quintal = 100 libras"
    )
    
    class Meta:
        verbose_name = 'Conversión de Unidad'
        verbose_name_plural = 'Conversiones de Unidades'
        unique_together = ['unidad_origen', 'unidad_destino']
        db_table = 'inv_conversion_unidad'
    
    def __str__(self):
        return f"1 {self.unidad_origen.abreviatura} = {self.factor_conversion} {self.unidad_destino.abreviatura}"


# ============================================================================
# SEÑALES (Signals) - Automatización de procesos
# ============================================================================

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Quintal)
def quintal_pre_save(sender, instance, **kwargs):
    """
    Antes de guardar un quintal:
    - Calcular costo_por_unidad si no existe
    - Actualizar estado según peso_actual
    """
    if instance.peso_inicial and not instance.costo_por_unidad:
        instance.costo_por_unidad = instance.costo_total / instance.peso_inicial
    
    if instance.peso_actual <= 0:
        instance.estado = 'AGOTADO'
        instance.peso_actual = Decimal('0.000')


@receiver(post_save, sender=Quintal)
def quintal_post_save(sender, instance, created, **kwargs):
    """
    Después de crear un quintal:
    - Registrar movimiento inicial de entrada
    """
    if created:
        MovimientoQuintal.objects.create(
            quintal=instance,
            tipo_movimiento='ENTRADA',
            peso_movimiento=instance.peso_inicial,
            peso_antes=Decimal('0.000'),
            peso_despues=instance.peso_inicial,
            unidad_medida=instance.unidad_medida,
            usuario=instance.usuario_registro,
            observaciones=f"Entrada inicial - Compra a {instance.proveedor.nombre_comercial}"
        )


@receiver(post_save, sender=ProductoNormal)
def producto_normal_post_save(sender, instance, created, **kwargs):
    """
    Después de crear un producto normal:
    - Registrar movimiento inicial si tiene stock
    """
    if created and instance.stock_actual > 0:
        from apps.authentication.models import Usuario
        # Buscar usuario admin o sistema
        usuario_sistema = Usuario.objects.filter(
            rol='ADMIN'
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


# ============================================================================
# MÉTODOS DE CLASE ÚTILES
# ============================================================================

# Agregar método a Producto para obtener stock total
def get_stock_total(self):
    """
    Retorna el stock total según el tipo de producto
    - QUINTAL: Peso total disponible en todos los quintales
    - NORMAL: Stock actual en unidades
    """
    if self.es_quintal():
        peso_total = Quintal.objects.peso_total_disponible(self)
        return f"{peso_total} {self.unidad_medida_base.abreviatura}"
    else:
        try:
            return f"{self.inventario_normal.stock_actual} unidades"
        except ProductoNormal.DoesNotExist:
            return "0 unidades"

Producto.get_stock_total = get_stock_total


# Agregar método para verificar disponibilidad
def tiene_stock_disponible(self, cantidad_solicitada=None):
    """
    Verifica si hay stock disponible
    
    Args:
        cantidad_solicitada: Para quintales (peso), para normales (unidades)
    
    Returns:
        bool: True si hay stock disponible
    """
    if self.es_quintal():
        if cantidad_solicitada:
            peso_disponible = Quintal.objects.peso_total_disponible(self)
            return peso_disponible >= Decimal(str(cantidad_solicitada))
        return Quintal.objects.disponibles().filter(producto=self).exists()
    else:
        try:
            if cantidad_solicitada:
                return self.inventario_normal.stock_actual >= cantidad_solicitada
            return self.inventario_normal.stock_actual > 0
        except ProductoNormal.DoesNotExist:
            return False

Producto.tiene_stock_disponible = tiene_stock_disponible


# ============================================================================
# MÉTODOS PARA REPORTES Y ESTADÍSTICAS
# ============================================================================

class EstadisticasInventario:
    """Clase helper para generar estadísticas del inventario"""
    
    @staticmethod
    def resumen_general():
        """Genera un resumen general del inventario"""
        total_productos = Producto.objects.filter(activo=True).count()
        total_quintales = Quintal.objects.disponibles().count()
        total_productos_normales = ProductoNormal.objects.con_stock().count()
        
        valor_quintales = Quintal.objects.disponibles().aggregate(
            total=Sum(F('peso_actual') * F('costo_por_unidad'))
        )['total'] or Decimal('0')
        
        valor_normales = ProductoNormal.objects.valor_total_inventario()
        
        return {
            'total_productos': total_productos,
            'total_quintales_disponibles': total_quintales,
            'total_productos_normales_con_stock': total_productos_normales,
            'valor_inventario_quintales': valor_quintales,
            'valor_inventario_normales': valor_normales,
            'valor_total_inventario': valor_quintales + valor_normales,
        }
    
    @staticmethod
    def productos_criticos():
        """Lista productos que necesitan atención"""
        quintales_criticos = Quintal.objects.criticos(porcentaje=10)
        productos_normales_criticos = ProductoNormal.objects.stock_critico()
        
        return {
            'quintales_criticos': quintales_criticos,
            'productos_normales_criticos': productos_normales_criticos,
        }
    
    @staticmethod
    def proximos_vencer(dias=7):
        """Productos próximos a vencer"""
        return Quintal.objects.proximos_a_vencer(dias=dias)