# apps/financial_management/models.py

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Sum, Q, F, Count
from decimal import Decimal
import uuid


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

@receiver(post_save, sender='sales_management.Venta')
def registrar_venta_en_caja(sender, instance, created, **kwargs):
    """
    Cuando se crea una venta, registrarla automáticamente en la caja
    """
    if created and instance.caja and instance.estado == 'COMPLETADA':
        try:
            instance.caja.registrar_venta(instance)
        except Exception as e:
            # Log error pero no interrumpir el flujo
            print(f"Error al registrar venta en caja: {e}")


@receiver(pre_save, sender=ArqueoCaja)
def arqueo_pre_save(sender, instance, **kwargs):
    """
    Antes de guardar arqueo, calcular diferencia
    """
    instance.calcular_diferencia()