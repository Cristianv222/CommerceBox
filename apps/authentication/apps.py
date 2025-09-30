from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """Configuración de la aplicación de autenticación"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authentication'
    verbose_name = 'Autenticación y Usuarios'
    
    def ready(self):
        """Configuraciones que se ejecutan cuando la app está lista"""
        # Importar señales
        import apps.authentication.signals
        
        # Crear grupos predeterminados
        self.create_default_groups()
    
    def create_default_groups(self):
        """Crear grupos predeterminados basados en roles"""
        try:
            from django.contrib.auth.models import Group
            from .models import Usuario
            
            roles = dict(Usuario.ROLES_CHOICES)
            
            for role_code, role_name in roles.items():
                group, created = Group.objects.get_or_create(name=role_name)
                if created:
                    print(f"Grupo creado: {role_name}")
                    
        except Exception as e:
            # Durante las migraciones iniciales puede que no existan las tablas
            pass