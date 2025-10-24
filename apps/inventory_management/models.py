# apps/inventory_management/models.py

from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Manager, Sum, Q, F, Count
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


class Marca(models.Model):
    """
    Marcas de productos
    Ejemplos: Coca-Cola, Nestlé, Del Monte, Maggi, Colgate, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Información básica
    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre de la marca"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción de la marca y sus productos"
    )
    
    # Información adicional
    pais_origen = models.CharField(
        max_length=100,
        blank=True,
        help_text="País de origen de la marca"
    )
    fabricante = models.CharField(
        max_length=200,
        blank=True,
        help_text="Empresa fabricante o dueña de la marca"
    )
    logo = models.ImageField(
        upload_to='marcas/',
        null=True,
        blank=True,
        help_text="Logo de la marca"
    )
    sitio_web = models.URLField(
        blank=True,
        help_text="Sitio web oficial de la marca"
    )
    
    # Control
    activa = models.BooleanField(
        default=True,
        help_text="Marca activa en el sistema"
    )
    destacada = models.BooleanField(
        default=False,
        help_text="Marca destacada (para mostrar en reportes o destacados)"
    )
    orden = models.IntegerField(
        default=0,
        help_text="Orden de visualización"
    )
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['orden', 'nombre']
        db_table = 'inv_marca'
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['activa', 'orden']),
            models.Index(fields=['destacada', 'activa']),
        ]
    
    def __str__(self):
        return self.nombre
    
    def total_productos(self):
        """Retorna el total de productos activos de esta marca"""
        return self.productos.filter(activo=True).count()
    
    def productos_con_stock(self):
        """
        Retorna productos de esta marca que tienen stock disponible
        Considera tanto quintales como productos normales
        """
        return self.productos.filter(
            activo=True
        ).filter(
            Q(tipo_inventario='QUINTAL', quintales__estado='DISPONIBLE', quintales__peso_actual__gt=0) |
            Q(tipo_inventario='NORMAL', inventario_normal__stock_actual__gt=0)
        ).distinct()
    
    def valor_inventario_marca(self):
        """Calcula el valor total del inventario de esta marca"""
        # Valor de quintales de esta marca
        valor_quintales = Quintal.objects.filter(
            producto__marca=self,
            estado='DISPONIBLE'
        ).aggregate(
            total=Sum(F('peso_actual') * F('costo_por_unidad'))
        )['total'] or Decimal('0')
        
        # Valor de productos normales de esta marca
        valor_normales = ProductoNormal.objects.filter(
            producto__marca=self
        ).aggregate(
            total=Sum(F('stock_actual') * F('costo_unitario'))
        )['total'] or Decimal('0')
        
        return valor_quintales + valor_normales


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
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
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
    
    # ============================================================================
    # IDENTIFICADORES
    # ============================================================================
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_barras = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Código de barras o código interno (CBX-PRD-XXXX)"
    )
    
    # ============================================================================
    # INFORMACIÓN BÁSICA
    # ============================================================================
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    
    # ============================================================================
    # RELACIONES
    # ============================================================================
    categoria = models.ForeignKey(
        'Categoria',
        on_delete=models.PROTECT,
        related_name='productos'
    )
    marca = models.ForeignKey(
        'Marca',
        on_delete=models.PROTECT,
        related_name='productos',
        null=True,
        blank=True,
        help_text="Marca del producto"
    )
    
    # ============================================================================
    # TIPO DE INVENTARIO
    # ============================================================================
    tipo_inventario = models.CharField(
        max_length=20,
        choices=TIPO_INVENTARIO_CHOICES,
        default='NORMAL',
        db_index=True
    )
    
    # ============================================================================
    # CAMPOS PARA QUINTALES (A GRANEL)
    # ============================================================================
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
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio por unidad de peso (ej: $2.50/lb) - Para quintales"
    )
    peso_base_quintal = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Peso estándar de un quintal (ej: 100 lb)"
    )
    
    # ============================================================================
    # CAMPOS PARA PRODUCTOS NORMALES (UNIDADES)
    # ============================================================================
    precio_venta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio de venta por unidad - Para productos normales (SIN IVA)"
    )
    
    # ============================================================================
    # IMPUESTOS (IVA) - ✅ CAMPO NUEVO Y CRÍTICO
    # ============================================================================
    aplica_impuestos = models.BooleanField(
        default=True,
        help_text="¿Este producto grava IVA? El porcentaje se obtiene de Configuración del Sistema"
    )
    
    # ============================================================================
    # IMAGEN
    # ============================================================================
    imagen = models.ImageField(
        upload_to='productos/',
        null=True,
        blank=True
    )
    
    # ============================================================================
    # CONTROL
    # ============================================================================
    activo = models.BooleanField(default=True)
    
    # ============================================================================
    # AUDITORÍA
    # ============================================================================
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
            models.Index(fields=['marca', 'activo']),
            models.Index(fields=['aplica_impuestos', 'activo']),
        ]
    
    def __str__(self):
        tipo_icon = "🌾" if self.tipo_inventario == 'QUINTAL' else "📦"
        marca_texto = f" - {self.marca.nombre}" if self.marca else ""
        return f"{tipo_icon} {self.nombre}{marca_texto} ({self.codigo_barras})"
    
    # ============================================================================
    # MÉTODOS DE UTILIDAD BÁSICOS
    # ============================================================================
    
    def es_quintal(self):
        """Verifica si es producto a granel"""
        return self.tipo_inventario == 'QUINTAL'
    
    def es_normal(self):
        """Verifica si es producto normal"""
        return self.tipo_inventario == 'NORMAL'
    
    def get_precio_base(self):
        """
        Retorna el precio base según el tipo (SIN IVA)
        - Quintales: precio por unidad de peso
        - Normales: precio de venta por unidad
        """
        if self.es_quintal():
            return self.precio_por_unidad_peso or Decimal('0')
        return self.precio_venta or Decimal('0')
    
    # ============================================================================
    # MÉTODOS PARA MANEJO DE IVA - ✅ NUEVO
    # ============================================================================
    
    def obtener_porcentaje_iva(self):
        """
        Obtiene el porcentaje de IVA desde configuración del sistema
        SOLO si este producto aplica impuestos
        
        Returns:
            Decimal: Porcentaje de IVA (ej: 15.00) o 0 si no aplica
        """
        if not self.aplica_impuestos:
            return Decimal('0')
        
        try:
            from apps.system_configuration.models import ConfiguracionSistema
            
            config = ConfiguracionSistema.objects.first()
            if config and config.iva_activo:
                return config.porcentaje_iva
        except Exception as e:
            print(f"⚠️ Error al obtener IVA desde configuración: {e}")
        
        return Decimal('0')
    
    def calcular_precio_con_iva(self, cantidad_peso=None):
        """
        Calcula el precio con IVA incluido
        
        Args:
            cantidad_peso (Decimal, optional): Para quintales, la cantidad de peso a calcular
        
        Returns:
            Decimal: Precio con IVA incluido
        """
        precio_base = self.get_precio_base()
        
        # Si es quintal y se especifica cantidad, calcular sobre esa cantidad
        if self.es_quintal() and cantidad_peso:
            precio_base = precio_base * Decimal(str(cantidad_peso))
        
        porcentaje_iva = self.obtener_porcentaje_iva()
        
        if porcentaje_iva > 0:
            iva_decimal = porcentaje_iva / Decimal('100')
            precio_con_iva = precio_base * (Decimal('1') + iva_decimal)
            return precio_con_iva.quantize(Decimal('0.01'))
        
        return precio_base.quantize(Decimal('0.01'))
    
    def calcular_monto_iva(self, cantidad_peso=None):
        """
        Calcula solo el monto del IVA
        
        Args:
            cantidad_peso (Decimal, optional): Para quintales, la cantidad de peso a calcular
        
        Returns:
            Decimal: Monto del IVA
        """
        precio_base = self.get_precio_base()
        
        # Si es quintal y se especifica cantidad, calcular sobre esa cantidad
        if self.es_quintal() and cantidad_peso:
            precio_base = precio_base * Decimal(str(cantidad_peso))
        
        porcentaje_iva = self.obtener_porcentaje_iva()
        
        if porcentaje_iva > 0:
            iva_decimal = porcentaje_iva / Decimal('100')
            monto_iva = precio_base * iva_decimal
            return monto_iva.quantize(Decimal('0.01'))
        
        return Decimal('0.00')
    
    def get_info_precio_completa(self, cantidad_peso=None):
        """
        Retorna información completa sobre precios e impuestos
        Útil para serializers, API y punto de venta
        
        Args:
            cantidad_peso (Decimal, optional): Para quintales, la cantidad de peso a calcular
        
        Returns:
            dict: Información completa de precios
        """
        precio_base = self.get_precio_base()
        
        # Si es quintal y se especifica cantidad
        if self.es_quintal() and cantidad_peso:
            precio_total_base = precio_base * Decimal(str(cantidad_peso))
        else:
            precio_total_base = precio_base
        
        porcentaje_iva = self.obtener_porcentaje_iva()
        monto_iva = self.calcular_monto_iva(cantidad_peso)
        precio_con_iva = self.calcular_precio_con_iva(cantidad_peso)
        
        return {
            'tipo_producto': self.tipo_inventario,
            'aplica_impuestos': self.aplica_impuestos,
            'porcentaje_iva': float(porcentaje_iva),
            'precio_base_unitario': float(precio_base),
            'precio_base_total': float(precio_total_base),
            'monto_iva': float(monto_iva),
            'precio_final_con_iva': float(precio_con_iva),
            'cantidad_peso': float(cantidad_peso) if cantidad_peso else None,
            'unidad_medida': self.unidad_medida_base.abreviatura if self.unidad_medida_base else 'unidad'
        }
    
    # ============================================================================
    # MÉTODOS ADICIONALES ÚTILES
    # ============================================================================
    
    def get_precio_venta(self):
        """
        Retorna el precio de venta (SIN IVA) según el tipo
        Mantiene compatibilidad con código existente
        """
        return self.get_precio_base()
    
    def get_precio_venta_display(self):
        """
        Retorna el precio de venta formateado para mostrar
        """
        precio = self.get_precio_base()
        if self.es_quintal():
            unidad = self.unidad_medida_base.abreviatura if self.unidad_medida_base else 'kg'
            return f"${precio:.2f}/{unidad}"
        return f"${precio:.2f}"
    
    # ============================================================================
    # VALIDACIÓN DEL MODELO
    # ============================================================================
    
    def clean(self):
        """
        Validación del modelo
        """
        if self.tipo_inventario == 'QUINTAL':
            if not self.unidad_medida_base:
                raise ValidationError({
                    'unidad_medida_base': 'Los productos tipo QUINTAL requieren una unidad de medida'
                })
            if not self.precio_por_unidad_peso:
                raise ValidationError({
                    'precio_por_unidad_peso': 'Los productos tipo QUINTAL requieren un precio por unidad de peso'
                })
        
        if self.tipo_inventario == 'NORMAL':
            if not self.precio_venta:
                raise ValidationError({
                    'precio_venta': 'Los productos tipo NORMAL requieren un precio de venta'
                })
    
    def save(self, *args, **kwargs):
        """
        Sobrescribir save para generar código de barras si no existe
        """
        if not self.codigo_barras:
            # Generar código único
            import random
            import string
            codigo = ''.join(random.choices(string.digits, k=8))
            self.codigo_barras = f"CBX{codigo}"
            
            # Verificar que sea único
            while Producto.objects.filter(codigo_barras=self.codigo_barras).exists():
                codigo = ''.join(random.choices(string.digits, k=8))
                self.codigo_barras = f"CBX{codigo}"
        
        # Validar antes de guardar
        self.clean()
        
        super().save(*args, **kwargs)


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
        ).order_by('fecha_ingreso')
    
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
        ('RESERVADO', '🟡 Reservado - En proceso de venta'),
        ('AGOTADO', '⚫ Agotado - Peso en cero'),
    ]
    
    # Identificadores
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_quintal = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Código único del quintal (ej: QNT-00001)"
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
        on_delete=models.PROTECT,
        related_name='quintales'
    )
    compra = models.ForeignKey(
        'Compra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quintales',
        help_text="Compra asociada a este quintal"
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
    fecha_ingreso = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Fecha de ingreso al inventario (importante para FIFO)"
    )
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento del producto"
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
        ordering = ['fecha_ingreso']  # FIFO: Primero el más antiguo
        db_table = 'inv_quintal'
        indexes = [
            models.Index(fields=['codigo_quintal']),
            models.Index(fields=['producto', 'estado', 'fecha_ingreso']),
            models.Index(fields=['estado', 'peso_actual']),
            models.Index(fields=['fecha_vencimiento']),
        ]
    
    def __str__(self):
        return f"{self.codigo_quintal} - {self.producto.nombre} ({self.peso_actual}/{self.peso_inicial} {self.unidad_medida.abreviatura})"
    
    def porcentaje_restante(self):
        """Calcula el porcentaje de peso restante"""
        if self.peso_inicial > 0:
            return float((self.peso_actual / self.peso_inicial) * 100)
        return 0.0
    
    def peso_vendido(self):
        """Calcula cuánto peso se ha vendido"""
        return self.peso_inicial - self.peso_actual
    
    def esta_critico(self, umbral_critico=10):
        """Verifica si el quintal está en estado crítico (menos del X% restante)"""
        return self.porcentaje_restante() <= umbral_critico
    
    def dias_almacenamiento(self):
        """Calcula días desde el ingreso"""
        return (timezone.now() - self.fecha_ingreso).days
    
    def dias_para_vencer(self):
        """Calcula días restantes para vencimiento"""
        if self.fecha_vencimiento:
            delta = self.fecha_vencimiento - timezone.now().date()
            return delta.days
        return None


class MovimientoQuintal(models.Model):
    """
    Registro de auditoría de cada movimiento de peso en un quintal
    Permite trazabilidad completa: Qué pasó, cuándo, quién, cuánto
    """
    
    TIPO_MOVIMIENTO_CHOICES = [
        ('ENTRADA', '📥 Entrada inicial (recepción)'),
        ('SALIDA', '📤 Salida por venta'),
        ('AJUSTE_ENTRADA', '➕ Ajuste positivo (corrección suma)'),
        ('AJUSTE_SALIDA', '➖ Ajuste negativo (corrección resta)'),
        ('MERMA', '💔 Merma/Pérdida'),
        ('ENTRADA_DEVOLUCION', '↩️ Entrada por devolución'),
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
    
    def dias_para_vencer(self):
        """Calcula días restantes para vencimiento"""
        if self.fecha_vencimiento:
            delta = self.fecha_vencimiento - timezone.now().date()
            return delta.days
        return None


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
        help_text="Referencia a compra"
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
# MODELO DE COMPRAS
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
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    # Auditoría
    usuario_registro = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='compras_registradas'
    )
    usuario_recepcion = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_recibidas'
    )
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


class DetalleCompra(models.Model):
    """
    Detalle de productos en una compra
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
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
        help_text="Peso comprado (para quintales)"
    )
    unidad_medida = models.ForeignKey(
        'UnidadMedida',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    # Para NORMALES
    cantidad_unidades = models.IntegerField(
        null=True,
        blank=True,
        help_text="Cantidad de unidades (para productos normales)"
    )
    
    # Costos
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Costo unitario o por unidad de peso"
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Subtotal de esta línea"
    )
    
    class Meta:
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalles de Compra'
        db_table = 'inv_detalle_compra'
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.subtotal}"


class ConversionUnidad(models.Model):
    """
    Tabla de conversión entre unidades de medida
    Facilita conversiones rápidas sin cálculos complejos
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
        unidad = self.unidad_medida_base.abreviatura if self.unidad_medida_base else 'kg'
        return f"{peso_total} {unidad}"
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
    
    @staticmethod
    def productos_por_marca():
        """Estadísticas de productos agrupados por marca"""
        return Marca.objects.filter(activa=True).annotate(
            total_productos=Count('productos', filter=Q(productos__activo=True)),
            productos_con_stock=Count(
                'productos',
                filter=Q(productos__activo=True) & (
                    Q(productos__tipo_inventario='QUINTAL', 
                      productos__quintales__estado='DISPONIBLE',
                      productos__quintales__peso_actual__gt=0) |
                    Q(productos__tipo_inventario='NORMAL',
                      productos__inventario_normal__stock_actual__gt=0)
                ),
                distinct=True
            )
        ).order_by('-total_productos')
    
    @staticmethod
    def marcas_mas_vendidas(fecha_inicio=None, fecha_fin=None):
        """Retorna las marcas más vendidas en un período"""
        try:
            from apps.sales_management.models import DetalleVenta
            
            filtros = {}
            if fecha_inicio:
                filtros['venta__fecha_venta__gte'] = fecha_inicio
            if fecha_fin:
                filtros['venta__fecha_venta__lte'] = fecha_fin
            
            return Marca.objects.filter(
                productos__detalles_venta__isnull=False,
                **filtros
            ).annotate(
                total_ventas=Count('productos__detalles_venta'),
                monto_total=Sum('productos__detalles_venta__subtotal')
            ).order_by('-monto_total')[:10]
        except:
            return Marca.objects.none()