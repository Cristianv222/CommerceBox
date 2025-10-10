# diagnostico_roles.py
# Coloca este archivo en el mismo directorio que manage.py
# Ejecutar con: python manage.py shell < diagnostico_roles.py

from apps.authentication.models import Usuario, Rol
from django.db.models import Count

print("\n" + "="*60)
print("DIAGNÓSTICO DE ROLES Y USUARIOS")
print("="*60)

# 1. Verificar roles existentes
print("\n1. ROLES EN EL SISTEMA:")
print("-" * 60)
roles = Rol.objects.all()
print(f"Total de roles: {roles.count()}")
for rol in roles:
    usuarios_count = Usuario.objects.filter(rol=rol).count()
    print(f"  - {rol.codigo} ({rol.nombre})")
    print(f"    Activo: {rol.is_active}")
    print(f"    Usuarios asignados: {usuarios_count}")
    print(f"    Permisos: {len(rol.permissions)} permisos")
    print()

# 2. Verificar usuarios
print("\n2. USUARIOS EN EL SISTEMA:")
print("-" * 60)
usuarios = Usuario.objects.select_related('rol').all()
print(f"Total de usuarios: {usuarios.count()}")

usuarios_sin_rol = Usuario.objects.filter(rol__isnull=True)
print(f"\n⚠️  Usuarios SIN ROL asignado: {usuarios_sin_rol.count()}")
if usuarios_sin_rol.exists():
    print("   USUARIOS SIN ROL:")
    for user in usuarios_sin_rol[:10]:  # Mostrar máximo 10
        print(f"   - {user.username} ({user.email}) - ID: {user.id}")
        print(f"     Estado: {user.estado}")
        print()

# 3. Verificar distribución de usuarios por rol
print("\n3. DISTRIBUCIÓN DE USUARIOS POR ROL:")
print("-" * 60)
distribucion = Usuario.objects.values(
    'rol__codigo', 'rol__nombre'
).annotate(
    total=Count('id')
).order_by('-total')

for item in distribucion:
    rol_codigo = item['rol__codigo'] or 'SIN ROL'
    rol_nombre = item['rol__nombre'] or 'Sin asignar'
    print(f"  {rol_codigo} ({rol_nombre}): {item['total']} usuarios")

# 4. Verificar usuarios activos
print("\n4. ESTADO DE USUARIOS:")
print("-" * 60)
usuarios_por_estado = Usuario.objects.values('estado').annotate(
    total=Count('id')
).order_by('-total')

for item in usuarios_por_estado:
    print(f"  {item['estado']}: {item['total']} usuarios")

# 5. Verificar superusuarios
print("\n5. SUPERUSUARIOS:")
print("-" * 60)
superusers = Usuario.objects.filter(is_superuser=True)
print(f"Total de superusuarios: {superusers.count()}")
for user in superusers:
    rol_info = f"{user.rol.codigo} ({user.rol.nombre})" if user.rol else "SIN ROL"
    print(f"  - {user.username} ({user.email})")
    print(f"    Rol: {rol_info}")
    print(f"    Estado: {user.estado}")
    print()

# 6. Sugerencias de corrección
print("\n6. SUGERENCIAS DE CORRECCIÓN:")
print("-" * 60)
if usuarios_sin_rol.exists():
    print("⚠️  PROBLEMA DETECTADO: Hay usuarios sin rol asignado")
    print("\nSOLUCIÓN:")
    print("   Ejecuta el siguiente comando para asignar un rol por defecto:")
    print("   python manage.py shell")
    print("   >>> from authentication.models import Usuario, Rol")
    print("   >>> rol_default = Rol.objects.get(codigo='TU_ROL_DEFAULT')")
    print("   >>> Usuario.objects.filter(rol__isnull=True).update(rol=rol_default)")
    print()

if not roles.exists():
    print("❌ PROBLEMA CRÍTICO: No hay roles en el sistema")
    print("\nSOLUCIÓN:")
    print("   Crea roles básicos ejecutando:")
    print("   python manage.py shell")
    print("   >>> from authentication.models import Rol")
    print("   >>> Rol.objects.create(codigo='ADMIN', nombre='Administrador', permissions=['*'])")
    print("   >>> Rol.objects.create(codigo='USER', nombre='Usuario', permissions=['inventory.view'])")
    print()

print("\n" + "="*60)
print("FIN DEL DIAGNÓSTICO")
print("="*60 + "\n")