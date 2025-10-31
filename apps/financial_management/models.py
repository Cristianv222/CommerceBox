# apps/financial_management/models.py

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Sum, Q, F, Count
from decimal import Decimal
import uuid
from datetime import timedelta


# ============================================================================
# CAJA PRINCIPAL
# ============================================================================

class Caja(models.Model):
    """
    Caja principal para manejo de ventas diarias
    Una caja puede estar ABIERTA (operativa) o CERRADA
    """
    ESTADO_CHOICES = [
        ('ABIERTA', '🟢 Abierta - Operativa'),
        ('CERRADA', '🔴 Cerrada - Inactiva'),
    ]
    
    TIPO_CAJA_CHOICES = [
        ('PRINCIPAL', 'Caja Principal'),
        ('SECUNDARIA', 'Caja Secundaria'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre de la caja (ej: Caja 1, Caja POS)"
    )
    codigo = models.CharField(
        max_length=20,
        unique=True,
        help_text="Código único (ej: CJA-001)"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CAJA_CHOICES,
        default='PRINCIPAL'
    )
    
    # Estado actual
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='CERRADA',
        db_index=True
    )
    
    # Montos de la apertura actual (si está abierta)
    monto_apertura = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Monto inicial al abrir caja"
    )
    monto_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Monto actual en caja"
    )
    
    # Fechas apertura/cierre actual
    fecha_apertura = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de la última apertura"
    )
    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora del último cierre"
    )
    
    # Usuarios responsables
    usuario_apertura = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='cajas_abiertas_por',
        null=True,
        blank=True
    )
    usuario_cierre = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='cajas_cerradas_por',
        null=True,
        blank=True
    )
    
    # Configuración
    requiere_autorizacion_cierre = models.BooleanField(
        default=False,
        help_text="Si requiere autorización de supervisor para cerrar"
    )
    activa = models.BooleanField(
        default=True,
        help_text="Si la caja está activa en el sistema"
    )
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'
        ordering = ['codigo']
        db_table = 'fin_caja'
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['estado', 'activa']),
        ]
    
    def __str__(self):
        estado_icon = "🟢" if self.estado == 'ABIERTA' else "🔴"
        return f"{estado_icon} {self.nombre} ({self.codigo})"
    
    def abrir_caja(self, usuario, monto_inicial):
        """Abre la caja con un monto inicial"""
        if self.estado == 'ABIERTA':
            raise ValueError("La caja ya está abierta")
        
        self.estado = 'ABIERTA'
        self.monto_apertura = monto_inicial
        self.monto_actual = monto_inicial
        self.fecha_apertura = timezone.now()
        self.usuario_apertura = usuario
        self.fecha_cierre = None
        self.usuario_cierre = None
        self.save()
        
        # Crear registro de apertura
        MovimientoCaja.objects.create(
            caja=self,
            tipo_movimiento='APERTURA',
            monto=monto_inicial,
            saldo_anterior=Decimal('0'),
            saldo_nuevo=monto_inicial,
            usuario=usuario,
            observaciones=f"Apertura de caja con ${monto_inicial}"
        )
    
    def cerrar_caja(self, usuario, monto_contado):
        """Cierra la caja y genera arqueo"""
        if self.estado == 'CERRADA':
            raise ValueError("La caja ya está cerrada")
        
        # Calcular diferencia
        diferencia = monto_contado - self.monto_actual
        
        self.estado = 'CERRADA'
        self.fecha_cierre = timezone.now()
        self.usuario_cierre = usuario
        self.save()
        
        # Crear registro de cierre
        MovimientoCaja.objects.create(
            caja=self,
            tipo_movimiento='CIERRE',
            monto=monto_contado,
            saldo_anterior=self.monto_actual,
            saldo_nuevo=Decimal('0'),
            usuario=usuario,
            observaciones=f"Cierre de caja - Monto contado: ${monto_contado}"
        )
        
        return diferencia
    
    def registrar_venta(self, venta):
        """Registra una venta en la caja"""
        if self.estado != 'ABIERTA':
            raise ValueError("No se puede registrar venta en caja cerrada")
        
        saldo_anterior = self.monto_actual
        self.monto_actual += venta.total
        self.save()
        
        MovimientoCaja.objects.create(
            caja=self,
            tipo_movimiento='VENTA',
            monto=venta.total,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=self.monto_actual,
            venta=venta,
            usuario=venta.vendedor,
            observaciones=f"Venta {venta.numero_venta}"
        )
    
    def total_ventas_hoy(self):
        """Calcula el total de ventas del día actual"""
        hoy_inicio = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return MovimientoCaja.objects.filter(
            caja=self,
            tipo_movimiento='VENTA',
            fecha_movimiento__gte=hoy_inicio
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')


# ============================================================================
# MOVIMIENTOS DE CAJA
# ============================================================================

class MovimientoCaja(models.Model):
    """
    Registro de cada movimiento en caja
    Auditoría completa de entradas y salidas
    """
    TIPO_MOVIMIENTO_CHOICES = [
        ('APERTURA', '🔓 Apertura de caja'),
        ('CIERRE', '🔒 Cierre de caja'),
        ('VENTA', '💰 Venta'),
        ('INGRESO', '➕ Ingreso adicional'),
        ('RETIRO', '➖ Retiro de efectivo'),
        ('DEVOLUCION', '↩️ Devolución a cliente'),
        ('AJUSTE_POSITIVO', '➕ Ajuste positivo'),
        ('AJUSTE_NEGATIVO', '➖ Ajuste negativo'),
        ('TRANSFERENCIA_ENTRADA', '📥 Transferencia recibida'),
        ('TRANSFERENCIA_SALIDA', '📤 Transferencia enviada'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relaciones
    caja = models.ForeignKey(
        'Caja',
        on_delete=models.PROTECT,
        related_name='movimientos'
    )
    
    # Tipo de movimiento
    tipo_movimiento = models.CharField(
        max_length=30,
        choices=TIPO_MOVIMIENTO_CHOICES,
        db_index=True
    )
    
    # Montos
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monto del movimiento"
    )
    saldo_anterior = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Saldo antes del movimiento"
    )
    saldo_nuevo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Saldo después del movimiento"
    )
    
    # Referencias externas
    venta = models.ForeignKey(
        'sales_management.Venta',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_caja'
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
        verbose_name = 'Movimiento de Caja'
        verbose_name_plural = 'Movimientos de Caja'
        ordering = ['-fecha_movimiento']
        db_table = 'fin_movimiento_caja'
        indexes = [
            models.Index(fields=['caja', '-fecha_movimiento']),
            models.Index(fields=['tipo_movimiento', '-fecha_movimiento']),
            models.Index(fields=['usuario', '-fecha_movimiento']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_movimiento_display()} - ${self.monto}"
    
    def es_entrada(self):
        """Verifica si es un movimiento de entrada"""
        return self.tipo_movimiento in [
            'APERTURA', 'VENTA', 'INGRESO', 
            'AJUSTE_POSITIVO', 'TRANSFERENCIA_ENTRADA'
        ]
    
    def es_salida(self):
        """Verifica si es un movimiento de salida"""
        return self.tipo_movimiento in [
            'RETIRO', 'DEVOLUCION', 
            'AJUSTE_NEGATIVO', 'TRANSFERENCIA_SALIDA'
        ]
    
    def save(self, *args, **kwargs):
        """
        Calcula saldo_anterior y saldo_nuevo automáticamente
        y actualiza el saldo de la caja
        """
        from decimal import Decimal
        from django.db import transaction
        
        # Calcular saldos si están vacíos (nuevo registro)
        if self.saldo_anterior is None or self.saldo_nuevo is None:
            with transaction.atomic():
                # Obtener saldo actual de la caja (con lock)
                Caja = self.caja.__class__
                caja = Caja.objects.select_for_update().get(pk=self.caja.pk)
                
                # Establecer saldo anterior
                self.saldo_anterior = caja.monto_actual
                
                # Calcular nuevo saldo según tipo de movimiento
                if self.es_entrada():
                    self.saldo_nuevo = self.saldo_anterior + self.monto
                elif self.es_salida():
                    self.saldo_nuevo = self.saldo_anterior - self.monto
                else:
                    # Para CIERRE, mantener el saldo
                    self.saldo_nuevo = self.saldo_anterior
                
                # Guardar el movimiento
                super().save(*args, **kwargs)
                
                # Actualizar el monto actual de la caja
                caja.monto_actual = self.saldo_nuevo
                caja.save(update_fields=['monto_actual'])
        else:
            # Si ya existen los saldos, solo guardar
            super().save(*args, **kwargs)


# ============================================================================
# ARQUEO DE CAJA (Cierre y Conciliación)
# ============================================================================

class ArqueoCaja(models.Model):
    """
    Registro de arqueo al cerrar caja
    Compara el efectivo contado vs el esperado
    """
    ESTADO_CHOICES = [
        ('CUADRADO', '✅ Cuadrado - Sin diferencias'),
        ('SOBRANTE', '➕ Sobrante - Más efectivo del esperado'),
        ('FALTANTE', '➖ Faltante - Menos efectivo del esperado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    numero_arqueo = models.CharField(
        max_length=20,
        unique=True,
        help_text="Número único del arqueo (ARQ-2025-00001)"
    )
    
    # Relación
    caja = models.ForeignKey(
        'Caja',
        on_delete=models.PROTECT,
        related_name='arqueos'
    )
    
    # Fechas
    fecha_apertura = models.DateTimeField(
        help_text="Fecha de apertura de esta sesión"
    )
    fecha_cierre = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha de cierre"
    )
    
    # Montos calculados (según sistema)
    monto_apertura = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monto de apertura"
    )
    total_ventas = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total de ventas del período"
    )
    total_ingresos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total de ingresos adicionales"
    )
    total_retiros = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total de retiros"
    )
    monto_esperado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monto que debería haber en caja según el sistema"
    )
    
    # Montos físicos (conteo real)
    monto_contado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monto real contado en efectivo"
    )
    
    # Desglose de efectivo contado
    billetes_100 = models.IntegerField(default=0)
    billetes_50 = models.IntegerField(default=0)
    billetes_20 = models.IntegerField(default=0)
    billetes_10 = models.IntegerField(default=0)
    billetes_5 = models.IntegerField(default=0)
    billetes_1 = models.IntegerField(default=0)
    monedas = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Diferencia
    diferencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="monto_contado - monto_esperado (+ sobrante, - faltante)"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        db_index=True
    )
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    observaciones_diferencia = models.TextField(
        blank=True,
        help_text="Explicación de la diferencia si existe"
    )
    
    # Auditoría
    usuario_apertura = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='arqueos_abiertos'
    )
    usuario_cierre = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='arqueos_cerrados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Arqueo de Caja'
        verbose_name_plural = 'Arqueos de Caja'
        ordering = ['-fecha_cierre']
        db_table = 'fin_arqueo_caja'
        indexes = [
            models.Index(fields=['numero_arqueo']),
            models.Index(fields=['caja', '-fecha_cierre']),
            models.Index(fields=['estado', '-fecha_cierre']),
        ]
    
    def __str__(self):
        return f"{self.numero_arqueo} - {self.caja.nombre} - {self.get_estado_display()}"
    
    def calcular_diferencia(self):
        """Calcula la diferencia entre contado y esperado"""
        self.diferencia = self.monto_contado - self.monto_esperado
        
        if self.diferencia == 0:
            self.estado = 'CUADRADO'
        elif self.diferencia > 0:
            self.estado = 'SOBRANTE'
        else:
            self.estado = 'FALTANTE'
    
    def save(self, *args, **kwargs):
        # Generar número de arqueo si no existe
        if not self.numero_arqueo:
            from django.utils import timezone
            año = timezone.now().year
            # Obtener el último arqueo del año
            ultimo = ArqueoCaja.objects.filter(
                numero_arqueo__startswith=f'ARQ-{año}-'
            ).order_by('numero_arqueo').last()
            
            if ultimo and ultimo.numero_arqueo:
                # Extraer el número secuencial del último arqueo
                try:
                    ultimo_num = int(ultimo.numero_arqueo.split('-')[-1])
                    siguiente_num = ultimo_num + 1
                except (ValueError, IndexError):
                    siguiente_num = 1
            else:
                siguiente_num = 1
            
            # Generar el número con formato ARQ-2025-00001
            self.numero_arqueo = f'ARQ-{año}-{siguiente_num:05d}'
        
        # Calcular diferencia antes de guardar
        self.calcular_diferencia()
        super().save(*args, **kwargs)


# ============================================================================
# CAJA CHICA
# ============================================================================

class CajaChica(models.Model):
    """
    Caja chica para gastos menores
    Fondo fijo que se repone periódicamente
    """
    ESTADO_CHOICES = [
        ('ACTIVA', '🟢 Activa'),
        ('INACTIVA', '🔴 Inactiva'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre de la caja chica (ej: Caja Chica Tienda)"
    )
    codigo = models.CharField(
        max_length=20,
        unique=True,
        help_text="Código único (ej: CCH-001)"
    )
    
    # Fondo
    monto_fondo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monto fijo del fondo de caja chica"
    )
    monto_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Saldo actual disponible"
    )
    
    # Límites
    limite_gasto_individual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50,
        help_text="Límite máximo por gasto individual"
    )
    umbral_reposicion = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Cuando el saldo baja de este monto, se debe reponer"
    )
    
    # Responsable
    responsable = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='cajas_chicas_responsable'
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='ACTIVA'
    )
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_ultima_reposicion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Caja Chica'
        verbose_name_plural = 'Cajas Chicas'
        ordering = ['codigo']
        db_table = 'fin_caja_chica'
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo}) - ${self.monto_actual}"
    
    def necesita_reposicion(self):
        """Verifica si necesita reposición"""
        return self.monto_actual <= self.umbral_reposicion
    
    def monto_a_reponer(self):
        """Calcula cuánto se necesita para completar el fondo"""
        return self.monto_fondo - self.monto_actual
    
    def registrar_gasto(self, monto, categoria, descripcion, usuario):
        """Registra un gasto de caja chica"""
        if monto > self.limite_gasto_individual:
            raise ValueError(
                f"El gasto excede el límite individual de ${self.limite_gasto_individual}"
            )
        
        if monto > self.monto_actual:
            raise ValueError("Fondos insuficientes en caja chica")
        
        saldo_anterior = self.monto_actual
        self.monto_actual -= monto
        self.save()
        
        MovimientoCajaChica.objects.create(
            caja_chica=self,
            tipo_movimiento='GASTO',
            monto=monto,
            categoria_gasto=categoria,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=self.monto_actual,
            usuario=usuario,
            descripcion=descripcion
        )
    
    def reponer_fondo(self, monto, usuario):
        """Repone el fondo de caja chica"""
        saldo_anterior = self.monto_actual
        self.monto_actual += monto
        self.fecha_ultima_reposicion = timezone.now()
        self.save()
        
        MovimientoCajaChica.objects.create(
            caja_chica=self,
            tipo_movimiento='REPOSICION',
            monto=monto,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=self.monto_actual,
            usuario=usuario,
            descripcion=f"Reposición de fondo - Completado a ${self.monto_fondo}"
        )


# ============================================================================
# MOVIMIENTOS DE CAJA CHICA
# ============================================================================

class MovimientoCajaChica(models.Model):
    """
    Registro de movimientos de caja chica
    """
    TIPO_MOVIMIENTO_CHOICES = [
        ('APERTURA', '🔓 Apertura de caja chica'),
        ('GASTO', '💸 Gasto'),
        ('REPOSICION', '➕ Reposición de fondo'),
        ('AJUSTE', '⚙️ Ajuste'),
    ]
    
    CATEGORIA_GASTO_CHOICES = [
        ('LIMPIEZA', '🧹 Limpieza y aseo'),
        ('OFICINA', '📎 Materiales de oficina'),
        ('MANTENIMIENTO', '🔧 Mantenimiento menor'),
        ('TRANSPORTE', '🚗 Transporte y combustible'),
        ('ALIMENTACION', '🍔 Alimentación'),
        ('EMERGENCIA', '🚨 Emergencia'),
        ('OTRO', '📦 Otro'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación
    caja_chica = models.ForeignKey(
        'CajaChica',
        on_delete=models.PROTECT,
        related_name='movimientos'
    )
    
    # Tipo
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES,
        db_index=True
    )
    
    # Categoría (solo para gastos)
    categoria_gasto = models.CharField(
        max_length=20,
        choices=CATEGORIA_GASTO_CHOICES,
        null=True,
        blank=True
    )
    
    # Montos
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    saldo_anterior = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    saldo_nuevo = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    # Detalles
    descripcion = models.TextField()
    numero_comprobante = models.CharField(
        max_length=50,
        blank=True,
        help_text="Número de factura o comprobante"
    )
    
    # Adjunto (opcional)
    comprobante_adjunto = models.FileField(
        upload_to='cajas_chicas/comprobantes/',
        null=True,
        blank=True,
        help_text="Foto o escaneo del comprobante"
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
    
    class Meta:
        verbose_name = 'Movimiento de Caja Chica'
        verbose_name_plural = 'Movimientos de Caja Chica'
        ordering = ['-fecha_movimiento']
        db_table = 'fin_movimiento_caja_chica'
        indexes = [
            models.Index(fields=['caja_chica', '-fecha_movimiento']),
            models.Index(fields=['tipo_movimiento', '-fecha_movimiento']),
            models.Index(fields=['categoria_gasto', '-fecha_movimiento']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_movimiento_display()} - ${self.monto}"
    
    def save(self, *args, **kwargs):
        """
        Calcula saldo_anterior y saldo_nuevo automáticamente
        y actualiza el saldo de la caja chica
        """
        from decimal import Decimal
        from django.db import transaction
        
        # Calcular saldos si están vacíos (nuevo registro)
        if self.saldo_anterior is None or self.saldo_nuevo is None:
            with transaction.atomic():
                # Obtener saldo actual de la caja chica (con lock)
                CajaChica = self.caja_chica.__class__
                caja_chica = CajaChica.objects.select_for_update().get(pk=self.caja_chica.pk)
                
                # Establecer saldo anterior
                self.saldo_anterior = caja_chica.monto_actual
                
                # Calcular nuevo saldo según tipo de movimiento
                if self.tipo_movimiento in ['APERTURA', 'REPOSICION']:
                    # Entrada de dinero
                    self.saldo_nuevo = self.saldo_anterior + self.monto
                elif self.tipo_movimiento == 'GASTO':
                    # Salida de dinero
                    self.saldo_nuevo = self.saldo_anterior - self.monto
                else:
                    # AJUSTE - mantener
                    self.saldo_nuevo = self.saldo_anterior
                
                # Guardar el movimiento
                super().save(*args, **kwargs)
                
                # Actualizar el monto actual de la caja chica
                caja_chica.monto_actual = self.saldo_nuevo
                caja_chica.save(update_fields=['monto_actual'])
        else:
            # Si ya existen los saldos, solo guardar
            super().save(*args, **kwargs)

# ============================================================================
# SIGNALS
# ============================================================================

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

# SIGNAL ELIMINADO: registrar_venta_en_caja
# Ahora se usa el signal en apps/financial_management/signals.py
# para evitar duplicados y tener mejor control

@receiver(pre_save, sender=ArqueoCaja)
def arqueo_pre_save(sender, instance, **kwargs):
    """
    Antes de guardar arqueo, calcular diferencia
    """
    instance.calcular_diferencia()

class CuentaPorCobrar(models.Model):
    """
    Registro de ventas a crédito a clientes
    Se genera automáticamente cuando una venta es de tipo CREDITO
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', '🟡 Pendiente'),
        ('PARCIAL', '🟠 Pago Parcial'),
        ('PAGADA', '🟢 Pagada'),
        ('VENCIDA', '🔴 Vencida'),
        ('CANCELADA', '⚫ Cancelada'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relaciones
    cliente = models.ForeignKey(
        'sales_management.Cliente',
        on_delete=models.PROTECT,
        related_name='cuentas_por_cobrar',
        help_text="Cliente que debe el pago"
    )
    venta = models.OneToOneField(
        'sales_management.Venta',
        on_delete=models.PROTECT,
        related_name='cuenta_credito',
        help_text="Venta asociada a esta cuenta"
    )
    
    # Información de la cuenta
    numero_cuenta = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Número único de la cuenta (CXC-000001)"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción adicional de la cuenta"
    )
    
    # Montos
    monto_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Monto total de la venta a crédito"
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total pagado hasta la fecha"
    )
    saldo_pendiente = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Saldo que aún debe el cliente"
    )
    
    # Fechas
    fecha_emision = models.DateField(
        default=timezone.now,
        db_index=True,
        help_text="Fecha de emisión de la cuenta"
    )
    fecha_vencimiento = models.DateField(
        db_index=True,
        help_text="Fecha de vencimiento del crédito"
    )
    fecha_pago_completo = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha en que se pagó completamente"
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        db_index=True
    )
    dias_vencidos = models.IntegerField(
        default=0,
        help_text="Días transcurridos desde el vencimiento (si aplica)"
    )
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    # Auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    usuario_registro = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='cuentas_cobrar_registradas'
    )
    
    class Meta:
        verbose_name = 'Cuenta por Cobrar'
        verbose_name_plural = 'Cuentas por Cobrar'
        ordering = ['-fecha_emision']
        db_table = 'fin_cuenta_por_cobrar'
        indexes = [
            models.Index(fields=['numero_cuenta']),
            models.Index(fields=['cliente', 'estado']),
            models.Index(fields=['fecha_vencimiento', 'estado']),
            models.Index(fields=['estado', '-fecha_emision']),
        ]
    
    def __str__(self):
        return f"{self.numero_cuenta} - {self.cliente.nombre_completo()} - ${self.saldo_pendiente}"
    
    def save(self, *args, **kwargs):
        """
        Al guardar:
        - Generar número de cuenta si no existe
        - Calcular saldo pendiente
        - Actualizar estado
        - Calcular días vencidos
        """
        # Generar número de cuenta
        if not self.numero_cuenta:
            self.numero_cuenta = self._generar_numero_cuenta()
        
        # Calcular saldo pendiente
        self.saldo_pendiente = self.monto_total - self.monto_pagado
        
        # Actualizar estado según saldo y fecha
        self._actualizar_estado()
        
        # Calcular días vencidos
        self._calcular_dias_vencidos()
        
        super().save(*args, **kwargs)
        
        # Actualizar crédito disponible del cliente
        if self.cliente:
            self._actualizar_credito_cliente()
    
    def _generar_numero_cuenta(self):
        """Genera un número único de cuenta por cobrar"""
        from datetime import datetime
        
        # Formato: CXC-AÑO-NUMERO
        año_actual = datetime.now().year
        ultimo = CuentaPorCobrar.objects.filter(
            numero_cuenta__startswith=f'CXC-{año_actual}-'
        ).order_by('-numero_cuenta').first()
        
        if ultimo and ultimo.numero_cuenta:
            try:
                ultimo_num = int(ultimo.numero_cuenta.split('-')[2])
                nuevo_num = ultimo_num + 1
            except:
                nuevo_num = 1
        else:
            nuevo_num = 1
        
        return f"CXC-{año_actual}-{nuevo_num:06d}"
    
    def _actualizar_estado(self):
        """Actualiza el estado de la cuenta según pagos y fecha"""
        if self.saldo_pendiente <= 0:
            self.estado = 'PAGADA'
            if not self.fecha_pago_completo:
                self.fecha_pago_completo = timezone.now().date()
        elif self.monto_pagado > 0:
            # Hay pago parcial
            if timezone.now().date() > self.fecha_vencimiento:
                self.estado = 'VENCIDA'
            else:
                self.estado = 'PARCIAL'
        else:
            # Sin pagos
            if timezone.now().date() > self.fecha_vencimiento:
                self.estado = 'VENCIDA'
            else:
                self.estado = 'PENDIENTE'
    
    def _calcular_dias_vencidos(self):
        """Calcula los días vencidos si la cuenta está vencida"""
        if timezone.now().date() > self.fecha_vencimiento and self.saldo_pendiente > 0:
            self.dias_vencidos = (timezone.now().date() - self.fecha_vencimiento).days
        else:
            self.dias_vencidos = 0
    
    def _actualizar_credito_cliente(self):
        """Actualiza el crédito disponible del cliente"""
        from django.db.models import Sum
        
        # Calcular total de deuda pendiente del cliente
        total_deuda = CuentaPorCobrar.objects.filter(
            cliente=self.cliente,
            estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDA']
        ).aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        # Actualizar crédito disponible
        self.cliente.credito_disponible = self.cliente.limite_credito - total_deuda
        self.cliente.save(update_fields=['credito_disponible'])
    
    def registrar_pago(self, monto, metodo_pago, usuario, observaciones="", numero_comprobante=""):
        """
        Registra un pago a la cuenta
        
        Args:
            monto: Monto del pago
            metodo_pago: Método de pago (EFECTIVO, TRANSFERENCIA, etc)
            usuario: Usuario que registra el pago
            observaciones: Observaciones del pago
            numero_comprobante: Número de comprobante/voucher
        
        Returns:
            PagoCuentaPorCobrar: Objeto del pago creado
        """
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        
        if monto > self.saldo_pendiente:
            raise ValueError(f"El monto (${monto}) excede el saldo pendiente (${self.saldo_pendiente})")
        
        # Crear registro de pago
        pago = PagoCuentaPorCobrar.objects.create(
            cuenta=self,
            monto=monto,
            metodo_pago=metodo_pago,
            usuario=usuario,
            observaciones=observaciones,
            numero_comprobante=numero_comprobante
        )
        
        # Actualizar montos
        self.monto_pagado += monto
        self.save()
        
        return pago
    
    def esta_vencida(self):
        """Verifica si la cuenta está vencida"""
        return timezone.now().date() > self.fecha_vencimiento and self.saldo_pendiente > 0
    
    def dias_para_vencer(self):
        """Retorna los días que faltan para vencer (negativo si ya venció)"""
        diferencia = (self.fecha_vencimiento - timezone.now().date()).days
        return diferencia
    
    def puede_cancelarse(self):
        """Verifica si la cuenta puede cancelarse"""
        return self.estado in ['PENDIENTE', 'PARCIAL', 'VENCIDA'] and self.monto_pagado == 0


# ============================================================================
# PAGOS DE CUENTAS POR COBRAR
# ============================================================================

class PagoCuentaPorCobrar(models.Model):
    """
    Registro de pagos realizados a cuentas por cobrar
    Permite pagos parciales o totales
    """
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', '💵 Efectivo'),
        ('TRANSFERENCIA', '🏦 Transferencia Bancaria'),
        ('TARJETA_DEBITO', '💳 Tarjeta de Débito'),
        ('TARJETA_CREDITO', '💳 Tarjeta de Crédito'),
        ('CHEQUE', '📝 Cheque'),
        ('DEPOSITO', '🏦 Depósito Bancario'),
        ('OTRO', '📦 Otro'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación
    cuenta = models.ForeignKey(
        'CuentaPorCobrar',
        on_delete=models.PROTECT,
        related_name='pagos'
    )
    
    # Información del pago
    numero_pago = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Número único del pago (PCX-000001)"
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES
    )
    
    # Información adicional del pago
    numero_comprobante = models.CharField(
        max_length=100,
        blank=True,
        help_text="Número de comprobante, voucher, cheque, etc."
    )
    banco = models.CharField(
        max_length=100,
        blank=True,
        help_text="Banco (para transferencias, cheques, etc.)"
    )
    numero_cuenta_banco = models.CharField(
        max_length=50,
        blank=True,
        help_text="Número de cuenta bancaria"
    )
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    # Auditoría
    fecha_pago = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='pagos_cuentas_cobrar_registrados'
    )
    
    class Meta:
        verbose_name = 'Pago de Cuenta por Cobrar'
        verbose_name_plural = 'Pagos de Cuentas por Cobrar'
        ordering = ['-fecha_pago']
        db_table = 'fin_pago_cuenta_por_cobrar'
        indexes = [
            models.Index(fields=['numero_pago']),
            models.Index(fields=['cuenta', '-fecha_pago']),
            models.Index(fields=['-fecha_pago']),
        ]
    
    def __str__(self):
        return f"{self.numero_pago} - ${self.monto} ({self.get_metodo_pago_display()})"
    
    def save(self, *args, **kwargs):
        """Al guardar, generar número de pago si no existe"""
        if not self.numero_pago:
            self.numero_pago = self._generar_numero_pago()
        
        super().save(*args, **kwargs)
    
    def _generar_numero_pago(self):
        """Genera un número único de pago"""
        from datetime import datetime
        
        # Formato: PCX-AÑO-NUMERO
        año_actual = datetime.now().year
        ultimo = PagoCuentaPorCobrar.objects.filter(
            numero_pago__startswith=f'PCX-{año_actual}-'
        ).order_by('-numero_pago').first()
        
        if ultimo and ultimo.numero_pago:
            try:
                ultimo_num = int(ultimo.numero_pago.split('-')[2])
                nuevo_num = ultimo_num + 1
            except:
                nuevo_num = 1
        else:
            nuevo_num = 1
        
        return f"PCX-{año_actual}-{nuevo_num:06d}"


# ============================================================================
# CUENTAS POR PAGAR (Compras a Crédito)
# ============================================================================

class CuentaPorPagar(models.Model):
    """
    Registro de compras a crédito a proveedores
    Se genera cuando se compra inventario a crédito
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', '🟡 Pendiente'),
        ('PARCIAL', '🟠 Pago Parcial'),
        ('PAGADA', '🟢 Pagada'),
        ('VENCIDA', '🔴 Vencida'),
        ('CANCELADA', '⚫ Cancelada'),
    ]
    
    TIPO_COMPRA_CHOICES = [
        ('QUINTAL', 'Compra de Quintales'),
        ('NORMAL', 'Compra de Productos Normales'),
        ('MIXTA', 'Compra Mixta'),
        ('SERVICIO', 'Servicio'),
        ('OTRO', 'Otro'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relaciones
    proveedor = models.ForeignKey(
        'inventory_management.Proveedor',
        on_delete=models.PROTECT,
        related_name='cuentas_por_pagar',
        help_text="Proveedor al que se le debe"
    )
    
    # Información de la cuenta
    numero_cuenta = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Número único de la cuenta (CXP-000001)"
    )
    numero_factura_proveedor = models.CharField(
        max_length=50,
        blank=True,
        help_text="Número de factura del proveedor"
    )
    tipo_compra = models.CharField(
        max_length=20,
        choices=TIPO_COMPRA_CHOICES,
        default='MIXTA'
    )
    descripcion = models.TextField(
        help_text="Descripción detallada de la compra"
    )
    
    # Montos
    monto_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Monto total de la compra a crédito"
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total pagado hasta la fecha"
    )
    saldo_pendiente = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Saldo que aún debemos al proveedor"
    )
    
    # Fechas
    fecha_emision = models.DateField(
        default=timezone.now,
        db_index=True,
        help_text="Fecha de emisión de la cuenta"
    )
    fecha_factura = models.DateField(
        help_text="Fecha de la factura del proveedor"
    )
    fecha_vencimiento = models.DateField(
        db_index=True,
        help_text="Fecha de vencimiento del crédito"
    )
    fecha_pago_completo = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha en que se pagó completamente"
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        db_index=True
    )
    dias_vencidos = models.IntegerField(
        default=0,
        help_text="Días transcurridos desde el vencimiento (si aplica)"
    )
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    # Auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    usuario_registro = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='cuentas_pagar_registradas'
    )
    
    class Meta:
        verbose_name = 'Cuenta por Pagar'
        verbose_name_plural = 'Cuentas por Pagar'
        ordering = ['-fecha_emision']
        db_table = 'fin_cuenta_por_pagar'
        indexes = [
            models.Index(fields=['numero_cuenta']),
            models.Index(fields=['proveedor', 'estado']),
            models.Index(fields=['fecha_vencimiento', 'estado']),
            models.Index(fields=['estado', '-fecha_emision']),
        ]
    
    def __str__(self):
        return f"{self.numero_cuenta} - {self.proveedor.nombre_comercial} - ${self.saldo_pendiente}"
    
    def save(self, *args, **kwargs):
        """
        Al guardar:
        - Generar número de cuenta si no existe
        - Calcular saldo pendiente
        - Actualizar estado
        - Calcular días vencidos
        """
        # Generar número de cuenta
        if not self.numero_cuenta:
            self.numero_cuenta = self._generar_numero_cuenta()
        
        # Calcular saldo pendiente
        self.saldo_pendiente = self.monto_total - self.monto_pagado
        
        # Actualizar estado según saldo y fecha
        self._actualizar_estado()
        
        # Calcular días vencidos
        self._calcular_dias_vencidos()
        
        super().save(*args, **kwargs)
    
    def _generar_numero_cuenta(self):
        """Genera un número único de cuenta por pagar"""
        from datetime import datetime
        
        # Formato: CXP-AÑO-NUMERO
        año_actual = datetime.now().year
        ultimo = CuentaPorPagar.objects.filter(
            numero_cuenta__startswith=f'CXP-{año_actual}-'
        ).order_by('-numero_cuenta').first()
        
        if ultimo and ultimo.numero_cuenta:
            try:
                ultimo_num = int(ultimo.numero_cuenta.split('-')[2])
                nuevo_num = ultimo_num + 1
            except:
                nuevo_num = 1
        else:
            nuevo_num = 1
        
        return f"CXP-{año_actual}-{nuevo_num:06d}"
    
    def _actualizar_estado(self):
        """Actualiza el estado de la cuenta según pagos y fecha"""
        if self.saldo_pendiente <= 0:
            self.estado = 'PAGADA'
            if not self.fecha_pago_completo:
                self.fecha_pago_completo = timezone.now().date()
        elif self.monto_pagado > 0:
            # Hay pago parcial
            if timezone.now().date() > self.fecha_vencimiento:
                self.estado = 'VENCIDA'
            else:
                self.estado = 'PARCIAL'
        else:
            # Sin pagos
            if timezone.now().date() > self.fecha_vencimiento:
                self.estado = 'VENCIDA'
            else:
                self.estado = 'PENDIENTE'
    
    def _calcular_dias_vencidos(self):
        """Calcula los días vencidos si la cuenta está vencida"""
        if timezone.now().date() > self.fecha_vencimiento and self.saldo_pendiente > 0:
            self.dias_vencidos = (timezone.now().date() - self.fecha_vencimiento).days
        else:
            self.dias_vencidos = 0
    
    def registrar_pago(self, monto, metodo_pago, usuario, observaciones="", numero_comprobante=""):
        """
        Registra un pago a la cuenta
        
        Args:
            monto: Monto del pago
            metodo_pago: Método de pago
            usuario: Usuario que registra el pago
            observaciones: Observaciones del pago
            numero_comprobante: Número de comprobante/voucher
        
        Returns:
            PagoCuentaPorPagar: Objeto del pago creado
        """
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        
        if monto > self.saldo_pendiente:
            raise ValueError(f"El monto (${monto}) excede el saldo pendiente (${self.saldo_pendiente})")
        
        # Crear registro de pago
        pago = PagoCuentaPorPagar.objects.create(
            cuenta=self,
            monto=monto,
            metodo_pago=metodo_pago,
            usuario=usuario,
            observaciones=observaciones,
            numero_comprobante=numero_comprobante
        )
        
        # Actualizar montos
        self.monto_pagado += monto
        self.save()
        
        return pago
    
    def esta_vencida(self):
        """Verifica si la cuenta está vencida"""
        return timezone.now().date() > self.fecha_vencimiento and self.saldo_pendiente > 0
    
    def dias_para_vencer(self):
        """Retorna los días que faltan para vencer (negativo si ya venció)"""
        diferencia = (self.fecha_vencimiento - timezone.now().date()).days
        return diferencia


# ============================================================================
# PAGOS DE CUENTAS POR PAGAR
# ============================================================================

class PagoCuentaPorPagar(models.Model):
    """
    Registro de pagos realizados a cuentas por pagar (proveedores)
    Permite pagos parciales o totales
    """
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', '💵 Efectivo'),
        ('TRANSFERENCIA', '🏦 Transferencia Bancaria'),
        ('CHEQUE', '📝 Cheque'),
        ('DEPOSITO', '🏦 Depósito Bancario'),
        ('TARJETA_CREDITO', '💳 Tarjeta de Crédito'),
        ('OTRO', '📦 Otro'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación
    cuenta = models.ForeignKey(
        'CuentaPorPagar',
        on_delete=models.PROTECT,
        related_name='pagos'
    )
    
    # Información del pago
    numero_pago = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Número único del pago (PPX-000001)"
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES
    )
    
    # Información adicional del pago
    numero_comprobante = models.CharField(
        max_length=100,
        blank=True,
        help_text="Número de comprobante, voucher, cheque, etc."
    )
    banco = models.CharField(
        max_length=100,
        blank=True,
        help_text="Banco (para transferencias, cheques, etc.)"
    )
    numero_cuenta_banco = models.CharField(
        max_length=50,
        blank=True,
        help_text="Número de cuenta bancaria"
    )
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    # Auditoría
    fecha_pago = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    usuario = models.ForeignKey(
        'authentication.Usuario',
        on_delete=models.PROTECT,
        related_name='pagos_cuentas_pagar_registrados'
    )
    
    class Meta:
        verbose_name = 'Pago de Cuenta por Pagar'
        verbose_name_plural = 'Pagos de Cuentas por Pagar'
        ordering = ['-fecha_pago']
        db_table = 'fin_pago_cuenta_por_pagar'
        indexes = [
            models.Index(fields=['numero_pago']),
            models.Index(fields=['cuenta', '-fecha_pago']),
            models.Index(fields=['-fecha_pago']),
        ]
    
    def __str__(self):
        return f"{self.numero_pago} - ${self.monto} ({self.get_metodo_pago_display()})"
    
    def save(self, *args, **kwargs):
        """Al guardar, generar número de pago si no existe"""
        if not self.numero_pago:
            self.numero_pago = self._generar_numero_pago()
        
        super().save(*args, **kwargs)
    
    def _generar_numero_pago(self):
        """Genera un número único de pago"""
        from datetime import datetime
        
        # Formato: PPX-AÑO-NUMERO
        año_actual = datetime.now().year
        ultimo = PagoCuentaPorPagar.objects.filter(
            numero_pago__startswith=f'PPX-{año_actual}-'
        ).order_by('-numero_pago').first()
        
        if ultimo and ultimo.numero_pago:
            try:
                ultimo_num = int(ultimo.numero_pago.split('-')[2])
                nuevo_num = ultimo_num + 1
            except:
                nuevo_num = 1
        else:
            nuevo_num = 1
        
        return f"PPX-{año_actual}-{nuevo_num:06d}"


# ============================================================================
# SIGNALS - Automatización de procesos
# ============================================================================

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender='sales_management.Venta')
def crear_cuenta_por_cobrar_automatico(sender, instance, created, **kwargs):
    """
    Cuando se crea una venta a CREDITO, crear automáticamente
    la cuenta por cobrar
    """
    if created and instance.tipo_venta == 'CREDITO' and instance.cliente:
        # Verificar que no exista ya una cuenta por cobrar para esta venta
        if not hasattr(instance, 'cuenta_credito'):
            from datetime import timedelta
            
            # Calcular fecha de vencimiento
            dias_credito = instance.cliente.dias_credito or 30
            fecha_vencimiento = instance.fecha_venta.date() + timedelta(days=dias_credito)
            
            # Crear cuenta por cobrar
            CuentaPorCobrar.objects.create(
                cliente=instance.cliente,
                venta=instance,
                monto_total=instance.total,
                fecha_emision=instance.fecha_venta.date(),
                fecha_vencimiento=fecha_vencimiento,
                descripcion=f"Venta {instance.numero_venta} a crédito",
                usuario_registro=instance.vendedor
            )


# ============================================================================
# MÉTODOS AUXILIARES PARA REPORTES
# ============================================================================

class ReporteCuentasPorCobrar:
    """Clase para generar reportes de cuentas por cobrar"""
    
    @staticmethod
    def resumen_general():
        """
        Resumen general de todas las cuentas por cobrar
        
        Returns:
            dict: Diccionario con totales y estadísticas
        """
        from .models import CuentaPorCobrar
        
        hoy = timezone.now().date()
        fecha_30_dias = hoy + timedelta(days=30)
        
        # Cuentas pendientes (PENDIENTE, PARCIAL, VENCIDA)
        cuentas_activas = CuentaPorCobrar.objects.filter(
            estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDA']
        )
        
        # Total por cobrar
        total_por_cobrar = cuentas_activas.aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        # Total vencido
        total_vencido = cuentas_activas.filter(
            estado='VENCIDA'
        ).aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        # Total por vencer en 30 días
        total_por_vencer = cuentas_activas.filter(
            fecha_vencimiento__lte=fecha_30_dias,
            fecha_vencimiento__gt=hoy
        ).aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        # Cantidad de cuentas pendientes
        cuentas_pendientes = cuentas_activas.count()
        
        # Cuentas cobradas este mes
        primer_dia_mes = hoy.replace(day=1)
        cuentas_cobradas = CuentaPorCobrar.objects.filter(
            estado='PAGADA',
            fecha_emision__gte=primer_dia_mes
        ).count()
        
        return {
            'total_por_cobrar': total_por_cobrar,
            'total_vencido': total_vencido,
            'total_por_vencer': total_por_vencer,
            'cuentas_pendientes': cuentas_pendientes,
            'cuentas_cobradas': cuentas_cobradas
        }
    
    @staticmethod
    def antiguedad_saldos():
        """
        Calcula la antigüedad de los saldos por cobrar
        
        Returns:
            list: Lista de diccionarios con rangos de antigüedad
        """
        from .models import CuentaPorCobrar
        
        hoy = timezone.now().date()
        
        # Definir rangos de antigüedad
        rangos = [
            {
                'rango': 'Al corriente (no vencidas)',
                'dias_min': None,
                'dias_max': 0,
                'filtro': Q(fecha_vencimiento__gt=hoy)
            },
            {
                'rango': '1-30 días vencidos',
                'dias_min': 1,
                'dias_max': 30,
                'filtro': Q(fecha_vencimiento__lte=hoy) & 
                         Q(fecha_vencimiento__gte=hoy - timedelta(days=30))
            },
            {
                'rango': '31-60 días vencidos',
                'dias_min': 31,
                'dias_max': 60,
                'filtro': Q(fecha_vencimiento__lt=hoy - timedelta(days=30)) & 
                         Q(fecha_vencimiento__gte=hoy - timedelta(days=60))
            },
            {
                'rango': '61-90 días vencidos',
                'dias_min': 61,
                'dias_max': 90,
                'filtro': Q(fecha_vencimiento__lt=hoy - timedelta(days=60)) & 
                         Q(fecha_vencimiento__gte=hoy - timedelta(days=90))
            },
            {
                'rango': 'Más de 90 días vencidos',
                'dias_min': 91,
                'dias_max': None,
                'filtro': Q(fecha_vencimiento__lt=hoy - timedelta(days=90))
            }
        ]
        
        # Total general para calcular porcentajes
        total_general = CuentaPorCobrar.objects.filter(
            estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDA']
        ).aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        resultados = []
        
        for rango in rangos:
            # Filtrar cuentas según el rango
            cuentas = CuentaPorCobrar.objects.filter(
                estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDA']
            ).filter(rango['filtro'])
            
            # Calcular totales
            total = cuentas.aggregate(
                total=Sum('saldo_pendiente')
            )['total'] or Decimal('0')
            
            cantidad = cuentas.count()
            
            # Calcular porcentaje
            if total_general > 0:
                porcentaje = float((total / total_general) * 100)
            else:
                porcentaje = 0.0
            
            resultados.append({
                'rango': rango['rango'],
                'dias_min': rango['dias_min'],
                'dias_max': rango['dias_max'],
                'cantidad': cantidad,
                'total': float(total),
                'porcentaje': porcentaje
            })
        
        return resultados
class ReporteCuentasPorPagar:
    """Clase para generar reportes de cuentas por pagar"""
    
    @staticmethod
    def resumen_general():
        """
        Resumen general de todas las cuentas por pagar
        
        Returns:
            dict: Diccionario con totales y estadísticas
        """
        from .models import CuentaPorPagar
        
        hoy = timezone.now().date()
        fecha_30_dias = hoy + timedelta(days=30)
        
        # Cuentas pendientes (PENDIENTE, PARCIAL, VENCIDA)
        cuentas_activas = CuentaPorPagar.objects.filter(
            estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDA']
        )
        
        # Total por pagar
        total_por_pagar = cuentas_activas.aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        # Total vencido
        total_vencido = cuentas_activas.filter(
            estado='VENCIDA'
        ).aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        # Total por vencer en 30 días
        total_por_vencer = cuentas_activas.filter(
            fecha_vencimiento__lte=fecha_30_dias,
            fecha_vencimiento__gt=hoy
        ).aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        # Cantidad de cuentas pendientes
        cuentas_pendientes = cuentas_activas.count()
        
        # Cuentas pagadas este mes
        primer_dia_mes = hoy.replace(day=1)
        cuentas_pagadas = CuentaPorPagar.objects.filter(
            estado='PAGADA',
            fecha_emision__gte=primer_dia_mes
        ).count()
        
        return {
            'total_por_pagar': total_por_pagar,
            'total_vencido': total_vencido,
            'total_por_vencer': total_por_vencer,
            'cuentas_pendientes': cuentas_pendientes,
            'cuentas_pagadas': cuentas_pagadas
        }
    
    @staticmethod
    def antiguedad_saldos():
        """
        Calcula la antigüedad de los saldos por pagar
        
        Returns:
            list: Lista de diccionarios con rangos de antigüedad
        """
        from .models import CuentaPorPagar
        
        hoy = timezone.now().date()
        
        # Definir rangos de antigüedad
        rangos = [
            {
                'rango': 'Al corriente (no vencidas)',
                'dias_min': None,
                'dias_max': 0,
                'filtro': Q(fecha_vencimiento__gt=hoy)
            },
            {
                'rango': '1-30 días vencidos',
                'dias_min': 1,
                'dias_max': 30,
                'filtro': Q(fecha_vencimiento__lte=hoy) & 
                         Q(fecha_vencimiento__gte=hoy - timedelta(days=30))
            },
            {
                'rango': '31-60 días vencidos',
                'dias_min': 31,
                'dias_max': 60,
                'filtro': Q(fecha_vencimiento__lt=hoy - timedelta(days=30)) & 
                         Q(fecha_vencimiento__gte=hoy - timedelta(days=60))
            },
            {
                'rango': '61-90 días vencidos',
                'dias_min': 61,
                'dias_max': 90,
                'filtro': Q(fecha_vencimiento__lt=hoy - timedelta(days=60)) & 
                         Q(fecha_vencimiento__gte=hoy - timedelta(days=90))
            },
            {
                'rango': 'Más de 90 días vencidos',
                'dias_min': 91,
                'dias_max': None,
                'filtro': Q(fecha_vencimiento__lt=hoy - timedelta(days=90))
            }
        ]
        
        # Total general para calcular porcentajes
        total_general = CuentaPorPagar.objects.filter(
            estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDA']
        ).aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or Decimal('0')
        
        resultados = []
        
        for rango in rangos:
            # Filtrar cuentas según el rango
            cuentas = CuentaPorPagar.objects.filter(
                estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDA']
            ).filter(rango['filtro'])
            
            # Calcular totales
            total = cuentas.aggregate(
                total=Sum('saldo_pendiente')
            )['total'] or Decimal('0')
            
            cantidad = cuentas.count()
            
            # Calcular porcentaje
            if total_general > 0:
                porcentaje = float((total / total_general) * 100)
            else:
                porcentaje = 0.0
            
            resultados.append({
                'rango': rango['rango'],
                'dias_min': rango['dias_min'],
                'dias_max': rango['dias_max'],
                'cantidad': cantidad,
                'total': float(total),
                'porcentaje': porcentaje
            })
        
        return resultados
