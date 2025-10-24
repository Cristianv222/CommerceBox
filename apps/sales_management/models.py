# apps/sales_management/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, F, Q
from decimal import Decimal
import uuid


# ============================================================================
# CLIENTE
# ============================================================================

class Cliente(models.Model):
    """
    Clientes del sistema - pueden ser frecuentes o walk-in
    """
    TIPO_CLIENTE_CHOICES = [
        ('FRECUENTE', 'Cliente Frecuente'),
        ('OCASIONAL', 'Cliente Ocasional'),
        ('MAYORISTA', 'Cliente Mayorista'),
    ]
    
    TIPO_DOCUMENTO_CHOICES = [
        ('CEDULA', 'Cédula'),
        ('RUC', 'RUC'),
        ('PASAPORTE', 'Pasaporte'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES)
    numero_documento = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Información personal
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    nombre_comercial = models.CharField(
        max_length=200,
        blank=True,
        help_text="Para clientes mayoristas/empresas"
    )
    
    # Contacto
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    
    # Clasificación
    tipo_cliente = models.CharField(
        max_length=20,
        choices=TIPO_CLIENTE_CHOICES,
        default='OCASIONAL'
    )
    
    # Crédito (para clientes frecuentes/mayoristas)
    limite_credito = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Límite de crédito disponible"
    )
    credito_disponible = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    dias_credito = models.IntegerField(default=0)
    
    # Descuentos especiales
    descuento_general = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Descuento general en % para este cliente"
    )
    
    # Control
    activo = models.BooleanField(default=True)
    
    # Auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_ultima_compra = models.DateTimeField(null=True, blank=True)
    total_compras = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total acumulado de compras"
    )
    
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['apellidos', 'nombres']
        db_table = 'sales_cliente'
        indexes = [
            models.Index(fields=['numero_documento']),
            models.Index(fields=['tipo_cliente', 'activo']),
        ]
    
    def __str__(self):
        if self.nombre_comercial:
            return f"{self.nombre_comercial} ({self.numero_documento})"
        return f"{self.nombres} {self.apellidos} ({self.numero_documento})"
    
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"
    
    def tiene_credito_disponible(self, monto):
        """Verifica si tiene crédito suficiente"""
        return self.credito_disponible >= monto
    
    def actualizar_credito(self, monto):
        """Actualiza el crédito disponible"""
        self.credito_disponible -= monto
        self.save()


# ============================================================================
# VENTA (Núcleo del módulo)
# ============================================================================

class Venta(models.Model):
    """
    Registro de ventas - puede incluir quintales y productos normales
    ✅ CORREGIDO: Incluye manejo de IVA dinámico
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('COMPLETADA', 'Completada'),
        ('ANULADA', 'Anulada'),
    ]
    
    TIPO_VENTA_CHOICES = [
        ('CONTADO', 'Contado'),
        ('CREDITO', 'Crédito'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificadores
    numero_venta = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        editable=False,
        db_index=True,
        help_text="Número único de venta (VNT-2025-00001)"
    )
    numero_factura = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Número de factura física/electrónica"
    )
    
    # Relaciones
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='ventas',
        null=True,
        blank=True,
        help_text="Cliente (opcional para ventas al público)"
    )
    vendedor = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='ventas_realizadas'
    )
    
    # Fechas
    fecha_venta = models.DateTimeField(default=timezone.now, db_index=True)
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento si es crédito"
    )
    
    # Tipo de venta
    tipo_venta = models.CharField(
        max_length=20,
        choices=TIPO_VENTA_CHOICES,
        default='CONTADO'
    )
    
    # ✅ CORREGIDO: Montos con campo para porcentaje de IVA aplicado
    subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Suma de subtotales de detalles (SIN IVA, después de descuentos por item)"
    )
    descuento = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Descuento adicional a nivel de venta"
    )
    impuestos = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Monto total de IVA calculado"
    )
    total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Total final = subtotal - descuento + impuestos"
    )
    
    # ✅ NUEVO: Campo para registrar el % de IVA aplicado en esta venta
    porcentaje_iva_aplicado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Porcentaje de IVA aplicado al momento de la venta (%)"
    )
    
    # Pagos
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cambio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        db_index=True
    )
    
    # Facturación electrónica (para integración futura)
    factura_electronica_enviada = models.BooleanField(default=False)
    factura_electronica_clave = models.CharField(
        max_length=100,
        blank=True,
        help_text="Clave de acceso factura electrónica"
    )
    factura_electronica_xml = models.TextField(
        blank=True,
        help_text="XML de la factura electrónica"
    )
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Relación con caja
    caja = models.ForeignKey(
        'financial_management.Caja',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas'
    )
    
    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha_venta']
        db_table = 'sales_venta'
        indexes = [
            models.Index(fields=['numero_venta']),
            models.Index(fields=['numero_factura']),
            models.Index(fields=['-fecha_venta', 'estado']),
            models.Index(fields=['cliente', '-fecha_venta']),
            models.Index(fields=['vendedor', '-fecha_venta']),
        ]
    
    def __str__(self):
        return f"{self.numero_venta} - ${self.total} - {self.get_estado_display()}"
    
    def save(self, *args, **kwargs):
        """Genera numero_venta automáticamente si no existe"""
        if not self.numero_venta:
            from django.utils import timezone
            año = timezone.now().year
            
            # Obtener último número del año
            ultimo = Venta.objects.filter(
                numero_venta__startswith=f'VNT-{año}-'
            ).order_by('-numero_venta').first()
            
            if ultimo and ultimo.numero_venta:
                try:
                    ultimo_num = int(ultimo.numero_venta.split('-')[-1])
                    siguiente_num = ultimo_num + 1
                except (ValueError, IndexError):
                    siguiente_num = 1
            else:
                siguiente_num = 1
            
            self.numero_venta = f'VNT-{año}-{siguiente_num:05d}'
        
        super().save(*args, **kwargs)
    
    def calcular_totales(self):
        """
        ✅ CORREGIDO: Recalcula los totales de la venta basándose en los detalles
        Incluye el cálculo correcto de IVA
        """
        detalles = self.detalles.all()
        
        # Subtotal = suma de subtotales de detalles (ya con descuentos aplicados, SIN IVA)
        self.subtotal = sum(d.subtotal for d in detalles)
        
        # Impuestos = suma de montos de IVA de cada detalle
        self.impuestos = sum(d.monto_iva for d in detalles)
        
        # Obtener el porcentaje de IVA desde la configuración
        from apps.system_configuration.models import ConfiguracionSistema
        config = ConfiguracionSistema.get_config()
        self.porcentaje_iva_aplicado = config.porcentaje_iva
        
        # Total = subtotal - descuento adicional de venta + impuestos
        self.total = self.subtotal - self.descuento + self.impuestos
        
        self.save()
    
    def esta_pagada(self):
        """Verifica si la venta está completamente pagada"""
        return self.monto_pagado >= self.total
    
    def saldo_pendiente(self):
        """Retorna el saldo pendiente de pago"""
        return max(self.total - self.monto_pagado, Decimal('0'))


# ============================================================================
# DETALLE DE VENTA (Items individuales)
# ============================================================================

class DetalleVenta(models.Model):
    """
    Detalle de cada item vendido
    Puede ser quintal (por peso) o producto normal (por unidad)
    ✅ CORREGIDO: Incluye campos y lógica para calcular IVA
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relaciones
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        'inventory_management.Producto',
        on_delete=models.PROTECT,
        related_name='detalles_venta'
    )
    
    # Para QUINTALES (venta por peso)
    quintal = models.ForeignKey(
        'inventory_management.Quintal',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Quintal específico del que se vendió (FIFO)"
    )
    peso_vendido = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Peso vendido si es quintal"
    )
    unidad_medida = models.ForeignKey(
        'inventory_management.UnidadMedida',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    precio_por_unidad_peso = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Precio por unidad de peso al momento de la venta (SIN IVA)"
    )
    
    # Para PRODUCTOS NORMALES (venta por unidad)
    cantidad_unidades = models.IntegerField(
        null=True,
        blank=True,
        help_text="Cantidad de unidades si es producto normal"
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio por unidad al momento de la venta (SIN IVA)"
    )
    
    # Común para ambos
    descuento_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    descuento_monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # ✅ NUEVO: Campo para indicar si este item aplica IVA
    aplica_iva = models.BooleanField(
        default=False,
        help_text="Indica si este producto graba IVA (copiado de producto al momento de la venta)"
    )
    
    # ✅ NUEVO: Campo para guardar el monto de IVA calculado para este item
    monto_iva = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Monto de IVA calculado para este item"
    )
    
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monto ANTES del descuento (SIN IVA)"
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monto DESPUÉS del descuento + IVA"
    )
    
    # Costo para cálculo de rentabilidad
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Costo al momento de la venta (para rentabilidad)"
    )
    costo_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Costo total del item vendido"
    )
    
    # Orden en la venta
    orden = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Venta'
        ordering = ['venta', 'orden']
        db_table = 'sales_detalle_venta'
        indexes = [
            models.Index(fields=['venta', 'orden']),
            models.Index(fields=['producto']),
            models.Index(fields=['aplica_iva']),  # ✅ NUEVO índice
        ]
    
    def __str__(self):
        try:
            if self.producto and self.producto.es_quintal():
                if self.peso_vendido and self.unidad_medida:
                    return f"{self.peso_vendido} {self.unidad_medida.abreviatura} de {self.producto.nombre}"
                else:
                    return f"Quintal de {self.producto.nombre if self.producto else 'producto'}"
            elif self.cantidad_unidades:
                return f"{self.cantidad_unidades} x {self.producto.nombre if self.producto else 'producto'}"
            else:
                return f"Detalle de venta"
        except:
            return f"Detalle de venta"
    
    def save(self, *args, **kwargs):
        """Validar stock antes de guardar"""
        if not self.pk:  # Solo validar al crear (no al editar)
            producto = self.producto
            
            # ✅ Copiar el flag de aplica_impuestos del producto
            self.aplica_iva = producto.aplica_impuestos
            
            # Validar stock para productos normales
            if producto.tipo_inventario == 'NORMAL' and self.cantidad_unidades:
                try:
                    inventario = producto.inventario_normal
                    if inventario:
                        stock_disponible = inventario.stock_actual
                        if self.cantidad_unidades > stock_disponible:
                            raise ValidationError(
                                f'Stock insuficiente para {producto.nombre}. '
                                f'Disponible: {stock_disponible} unidades, Solicitado: {self.cantidad_unidades} unidades'
                            )
                    else:
                        raise ValidationError(f'El producto {producto.nombre} no tiene inventario configurado')
                except AttributeError:
                    raise ValidationError(f'El producto {producto.nombre} no tiene inventario configurado')
            
            # Validar peso para quintales
            elif producto.tipo_inventario == 'QUINTAL' and self.quintal and self.peso_vendido:
                quintal = self.quintal
                if self.peso_vendido > quintal.peso_actual:
                    raise ValidationError(
                        f'Peso insuficiente en el quintal. '
                        f'Disponible: {quintal.peso_actual} kg, Solicitado: {self.peso_vendido} kg'
                    )
        
        super().save(*args, **kwargs)
    
    def calcular_totales(self):
        """
        ✅ CORREGIDO: Calcula subtotal, descuento, IVA y total
        """
        # 1. Calcular subtotal base (SIN IVA, SIN descuento)
        if self.producto.es_quintal():
            # Cálculo para quintales
            subtotal_base = self.peso_vendido * self.precio_por_unidad_peso
        else:
            # Cálculo para productos normales
            subtotal_base = self.cantidad_unidades * self.precio_unitario
        
        # 2. Aplicar descuento sobre el subtotal base
        if self.descuento_porcentaje > 0:
            self.descuento_monto = subtotal_base * (self.descuento_porcentaje / Decimal('100'))
        else:
            self.descuento_monto = Decimal('0')
        
        # 3. Subtotal después de descuento (pero todavía SIN IVA)
        self.subtotal = subtotal_base - self.descuento_monto
        
        # 4. ✅ NUEVO: Calcular IVA si el producto lo requiere
        if self.aplica_iva:
            # Obtener porcentaje de IVA desde configuración
            from apps.system_configuration.models import ConfiguracionSistema
            config = ConfiguracionSistema.get_config()
            porcentaje_iva = config.porcentaje_iva
            
            # Calcular monto de IVA sobre el subtotal (después de descuento)
            self.monto_iva = self.subtotal * (porcentaje_iva / Decimal('100'))
        else:
            self.monto_iva = Decimal('0')
        
        # 5. Total = Subtotal (después de descuento) + IVA
        self.total = self.subtotal + self.monto_iva
    
    def utilidad(self):
        """Calcula la utilidad de este item"""
        return self.total - self.costo_total
    
    def margen_porcentaje(self):
        """Calcula el margen de ganancia en porcentaje"""
        if self.total > 0:
            return ((self.total - self.costo_total) / self.total) * 100
        return 0


# ============================================================================
# PAGO (Múltiples formas de pago por venta)
# ============================================================================

class Pago(models.Model):
    """
    Registro de pagos - una venta puede tener múltiples pagos
    """
    FORMA_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA_DEBITO', 'Tarjeta de Débito'),
        ('TARJETA_CREDITO', 'Tarjeta de Crédito'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
        ('CHEQUE', 'Cheque'),
        ('CREDITO', 'Crédito'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='pagos'
    )
    
    # Forma de pago
    forma_pago = models.CharField(
        max_length=20,
        choices=FORMA_PAGO_CHOICES
    )
    
    # Monto
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Información adicional según forma de pago
    numero_referencia = models.CharField(
        max_length=100,
        blank=True,
        help_text="Número de autorización, voucher, cheque, etc"
    )
    banco = models.CharField(max_length=100, blank=True)
    
    # Auditoría
    fecha_pago = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT
    )
    
    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago']
        db_table = 'sales_pago'
    
    def __str__(self):
        return f"{self.get_forma_pago_display()} - ${self.monto}"


# ============================================================================
# DEVOLUCIÓN (Returns)
# ============================================================================

class Devolucion(models.Model):
    """
    Registro de devoluciones de productos
    """
    MOTIVO_CHOICES = [
        ('DEFECTUOSO', 'Producto Defectuoso'),
        ('EQUIVOCACION', 'Equivocación en venta'),
        ('NO_SATISFECHO', 'Cliente no satisfecho'),
        ('VENCIDO', 'Producto vencido'),
        ('OTRO', 'Otro motivo'),
    ]
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de procesar'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    numero_devolucion = models.CharField(
        max_length=20,
        unique=True,
        help_text="Número único de devolución (DEV-2025-00001)"
    )
    
    # Relaciones
    venta_original = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name='devoluciones'
    )
    detalle_venta = models.ForeignKey(
        DetalleVenta,
        on_delete=models.PROTECT,
        help_text="Item específico que se devuelve"
    )
    
    # Cantidad devuelta
    cantidad_devuelta = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Peso o unidades devueltas"
    )
    monto_devolucion = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    # Motivo y estado
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES)
    descripcion = models.TextField(help_text="Descripción detallada del motivo de devolución")
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE'
    )
    
    # Auditoría
    fecha_devolucion = models.DateTimeField(default=timezone.now)
    usuario_solicita = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='devoluciones_solicitadas'
    )
    usuario_aprueba = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devoluciones_aprobadas'
    )
    fecha_procesado = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Devolución'
        verbose_name_plural = 'Devoluciones'
        ordering = ['-fecha_devolucion']
        db_table = 'sales_devolucion'
    
    def __str__(self):
        return f"{self.numero_devolucion} - ${self.monto_devolucion}"


# ============================================================================
# SIGNALS
# ============================================================================

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db import transaction

def detalle_venta_pre_save(sender, instance, **kwargs):
    """Calcular totales antes de guardar"""
    instance.calcular_totales()


def pago_post_save(sender, instance, created, **kwargs):
    """Actualizar monto pagado en la venta"""
    venta = instance.venta
    venta.monto_pagado = venta.pagos.aggregate(
        total=Sum('monto')
    )['total'] or Decimal('0')
    
    # Actualizar estado si está completamente pagada
    if venta.esta_pagada() and venta.estado == 'PENDIENTE':
        venta.estado = 'COMPLETADA'
    
    venta.save()


def venta_anulada_revertir_stock(sender, instance, **kwargs):
    """
    Si una venta se anula, revertir el stock
    """
    if instance.estado == 'ANULADA':
        with transaction.atomic():
            for detalle in instance.detalles.all():
                producto = detalle.producto
                
                if producto.tipo_inventario == 'QUINTAL' and detalle.quintal:
                    # Revertir peso al quintal
                    quintal = detalle.quintal
                    quintal.peso_actual += detalle.peso_vendido
                    if quintal.estado == 'AGOTADO':
                        quintal.estado = 'DISPONIBLE'
                    quintal.save()
                    
                elif producto.tipo_inventario == 'NORMAL' and detalle.cantidad_unidades:
                    # Revertir unidades al inventario
                    try:
                        inventario = producto.inventario_normal
                        if inventario:
                            inventario.stock_actual += detalle.cantidad_unidades
                            inventario.save()
                    except Exception as e:
                        print(f"Error al revertir inventario: {e}")