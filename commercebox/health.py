"""
Health Check endpoint para monitoreo
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    """
    Endpoint de health check para Docker y Nginx Proxy Manager
    """
    checks = {
        'status': 'healthy',
        'database': False,
        'cache': False
    }
    
    # Test PostgreSQL
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks['database'] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks['status'] = 'unhealthy'
    
    # Test Redis
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            checks['cache'] = True
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        checks['status'] = 'unhealthy'
    
    status_code = 200 if checks['status'] == 'healthy' else 503
    return JsonResponse(checks, status=status_code)
