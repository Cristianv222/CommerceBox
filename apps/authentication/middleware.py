from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
import jwt
from django.conf import settings

Usuario = get_user_model()

class DualAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware que maneja autenticación dual: JWT + Django Sessions
    Prioridad: Sessions > JWT > Anonymous
    """
    
    def process_request(self, request):
        # 1. Si ya está autenticado por SessionMiddleware, no hacer nada
        if hasattr(request, 'user') and request.user.is_authenticated:
            return None
        
        # 2. Intentar autenticar con JWT desde cookies
        token = request.COOKIES.get('access_token')
        
        if token:
            try:
                # Decodificar el token JWT
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=['HS256']
                )
                
                user_id = payload.get('user_id')
                
                if user_id:
                    try:
                        user = Usuario.objects.get(id=user_id)
                        request.user = user
                        return None
                    except Usuario.DoesNotExist:
                        pass
                        
            except (jwt.ExpiredSignatureError, jwt.DecodeError, ValueError):
                pass
        
        # 3. Si todo falla, dejar como AnonymousUser (ya establecido por Django)
        return None
