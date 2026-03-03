from django.contrib import admin
from .models import SRIConfig, SRILog

@admin.register(SRIConfig)
class SRIConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_test_mode', 'is_active')
    list_editable = ('is_active',)

@admin.register(SRILog)
class SRILogAdmin(admin.ModelAdmin):
    list_display = ('fecha_envio', 'venta', 'status_code', 'success', 'invoice_number_sri')
    list_filter = ('success', 'status_code')
    readonly_fields = ('fecha_envio', 'request_data', 'response_data')
    search_fields = ('venta__numero_venta', 'invoice_number_sri')
