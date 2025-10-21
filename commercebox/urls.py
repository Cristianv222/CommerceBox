from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.custom_admin.views import login_page_view
from django.contrib.auth.views import LogoutView
from django.views.generic import RedirectView

admin.site.site_header = 'CommerceBox - Django Admin'
admin.site.site_title = 'CommerceBox Admin'
admin.site.index_title = 'Administración Avanzada'

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False), name='home'),
    path('login/', login_page_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='/login/'), name='logout'),
    path('panel/', include('apps.custom_admin.urls', namespace='custom_admin')),
    path('django-admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls', namespace='authentication')),
    path('api/inventario/', include('apps.inventory_management.urls')),
    path('api/ventas/', include('apps.sales_management.urls')),
    path('api/finanzas/', include('apps.financial_management.urls')),
    path('api/reportes/', include('apps.reports_analytics.urls')),
    path('api/hardware/', include('apps.hardware_integration.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)