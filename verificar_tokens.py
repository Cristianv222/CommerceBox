#!/usr/bin/env python
"""
Script para crear usuario de sistema para CommerceBox
Específico para el modelo Usuario personalizado

EJECUCIÓN:
docker-compose exec commercebox-web python crear_usuario_sistema_final.py
"""

import os
import sys
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commercebox.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from apps.authentication.models import Rol

def crear_usuario_sistema():
    """
    Crea el usuario de sistema para el agente
    Compatible con el modelo Usuario de CommerceBox
    """
    print("="*70)
    print("     COMMERCEBOX - USUARIO DE SISTEMA PARA AGENTE")
    print("="*70)
    print()
    
    try:
        User = get_user_model()
        
        # Verificar si ya existe
        username = 'agente_impresion'
        
        usuario_existente = User.objects.filter(username=username).first()
        
        if usuario_existente:
            print(f"✅ Usuario '{username}' ya existe")
            print(f"   ID: {usuario_existente.id}")
            print(f"   Código: {usuario_existente.codigo_empleado}")
            print(f"   Email: {usuario_existente.email}")
            print()
            
            # Verificar token
            token = Token.objects.filter(user=usuario_existente).first()
            
            if token:
                print("✅ Token existente encontrado")
                mostrar_token_final(token.key, usuario_existente)
                return token.key
            else:
                print("⚠️  Creando token para usuario existente...")
                token = Token.objects.create(user=usuario_existente)
                mostrar_token_final(token.key, usuario_existente)
                return token.key
        
        # CREAR NUEVO USUARIO
        print("[1/4] Generando datos únicos...")
        
        # 🔥 Generar codigo_empleado único (4-10 caracteres alfanuméricos mayúsculas)
        def generar_codigo_empleado():
            while True:
                codigo = f"SYS{random.randint(1000, 9999)}"  # SYS1234
                if not User.objects.filter(codigo_empleado=codigo).exists():
                    return codigo
        
        # 🔥 Generar documento_identidad único
        def generar_documento():
            while True:
                documento = f"SYSTEM-{random.randint(100000, 999999)}"
                if not User.objects.filter(documento_identidad=documento).exists():
                    return documento
        
        codigo_empleado = generar_codigo_empleado()
        documento_identidad = generar_documento()
        
        print(f"   📋 Código empleado: {codigo_empleado}")
        print(f"   🆔 Documento: {documento_identidad}")
        print()
        
        # [2/4] Obtener o crear rol básico
        print("[2/4] Configurando rol...")
        
        # Intentar obtener un rol existente o crear uno básico
        rol = None
        try:
            # Buscar rol SISTEMA o crear uno básico
            rol = Rol.objects.filter(codigo='SISTEMA').first()
            
            if not rol:
                # Buscar cualquier rol activo
                rol = Rol.objects.filter(is_active=True).first()
            
            if not rol:
                # Crear rol básico para el agente
                print("   ⚠️  No hay roles. Creando rol SISTEMA...")
                rol = Rol.objects.create(
                    nombre='Sistema',
                    codigo='SISTEMA',
                    descripcion='Rol para agentes y servicios del sistema',
                    permissions=[
                        'hardware.view',
                        'hardware.create',
                        'hardware.update'
                    ],
                    is_active=True
                )
                print(f"   ✅ Rol SISTEMA creado")
            else:
                print(f"   ✅ Rol asignado: {rol.nombre}")
        except Exception as e:
            print(f"   ⚠️  No se pudo crear/asignar rol: {e}")
            print(f"   ℹ️  Usuario se creará sin rol (puede asignarse después)")
        
        print()
        
        # [3/4] Crear usuario
        print("[3/4] Creando usuario de sistema...")
        
        usuario = User.objects.create(
            # Identificadores únicos
            codigo_empleado=codigo_empleado,
            documento_identidad=documento_identidad,
            
            # Autenticación
            username='agente_impresion',
            email='agente@commercebox.local',
            
            # Información personal
            nombres='Agente',
            apellidos='Sistema Impresión',
            telefono='',  # Vacío (blank=True)
            
            # Rol y estado
            rol=rol,  # Puede ser None
            estado='ACTIVO',
            
            # Control de acceso
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        
        # Establecer contraseña
        usuario.set_password('AgEnTeImPrEsIoN2024!ComMeRcE')
        usuario.save()
        
        print(f"   ✅ Usuario creado exitosamente")
        print(f"   📝 ID: {usuario.id}")
        print()
        
        # [4/4] Crear token
        print("[4/4] Generando token de autenticación...")
        token = Token.objects.create(user=usuario)
        print(f"   ✅ Token generado")
        print()
        
        mostrar_token_final(token.key, usuario)
        
        return token.key
        
    except Exception as e:
        print()
        print("="*70)
        print("❌ ERROR AL CREAR USUARIO")
        print("="*70)
        print()
        print(f"Error: {e}")
        print()
        
        import traceback
        print("DETALLES DEL ERROR:")
        print("-"*70)
        traceback.print_exc()
        print("-"*70)
        print()
        
        print("POSIBLES SOLUCIONES:")
        print()
        print("1. Verificar que no existan registros duplicados:")
        print("   python manage.py shell")
        print("   >>> from apps.authentication.models import Usuario")
        print("   >>> Usuario.objects.filter(username='agente_impresion')")
        print()
        print("2. Si existe pero está corrupto, eliminarlo:")
        print("   >>> Usuario.objects.filter(username='agente_impresion').delete()")
        print()
        print("3. Verificar constraints en la base de datos:")
        print("   Puede haber índices únicos que causen conflictos")
        print()
        
        return None


def mostrar_token_final(token_key, usuario):
    """Muestra el token y las instrucciones finales"""
    print()
    print("="*70)
    print("     ✅ CONFIGURACIÓN COMPLETADA")
    print("="*70)
    print()
    print("INFORMACIÓN DEL USUARIO:")
    print("─"*70)
    print(f"   👤 Usuario:        {usuario.username}")
    print(f"   🆔 ID:             {usuario.id}")
    print(f"   📋 Código:         {usuario.codigo_empleado}")
    print(f"   📄 Documento:      {usuario.documento_identidad}")
    print(f"   📧 Email:          {usuario.email}")
    print(f"   👥 Nombre:         {usuario.get_full_name()}")
    print(f"   🔐 Contraseña:     AgEnTeImPrEsIoN2024!ComMeRcE")
    if usuario.rol:
        print(f"   🎭 Rol:            {usuario.rol.nombre}")
    print("─"*70)
    print()
    print("🔑 TOKEN DE AUTENTICACIÓN:")
    print("─"*70)
    print(f"   {token_key}")
    print("─"*70)
    print()
    print()
    print("="*70)
    print("     📋 SIGUIENTES PASOS")
    print("="*70)
    print()
    print("PASO 1: Actualizar las vistas del agente")
    print("─"*70)
    print()
    print("   1. En tu proyecto, edita:")
    print("      apps/hardware_integration/api/agente_views.py")
    print()
    print("   2. Busca la función: obtener_trabajos_pendientes()")
    print()
    print("   3. Reemplaza ESTE BLOQUE:")
    print()
    print("      # ❌ VERSIÓN ANTIGUA (solo ve trabajos de UN usuario)")
    print("      trabajos_query = TrabajoImpresion.objects.filter(")
    print("          estado='PENDIENTE',")
    print("          creado_por=request.user  # ← QUITA ESTA LÍNEA")
    print("      )")
    print()
    print("   4. Por ESTE NUEVO BLOQUE:")
    print()
    print("      # ✅ VERSIÓN NUEVA (usuario sistema ve TODOS los trabajos)")
    print("      USUARIO_SISTEMA = 'agente_impresion'")
    print("      es_sistema = request.user.username == USUARIO_SISTEMA")
    print("      ")
    print("      if es_sistema:")
    print("          # Usuario sistema ve TODOS")
    print("          trabajos_query = TrabajoImpresion.objects.filter(")
    print("              estado='PENDIENTE'")
    print("          )")
    print("      else:")
    print("          # Usuario normal solo ve los suyos")
    print("          trabajos_query = TrabajoImpresion.objects.filter(")
    print("              estado='PENDIENTE',")
    print("              creado_por=request.user")
    print("          )")
    print()
    print()
    print("PASO 2: Reiniciar el servidor")
    print("─"*70)
    print()
    print("   docker-compose restart commercebox-web")
    print()
    print()
    print("PASO 3: Configurar el agente en Windows")
    print("─"*70)
    print()
    print("   1. Abre: CommerceBox-Agente.exe")
    print()
    print("   2. Ve a la pestaña: ⚙️ Configuración")
    print()
    print("   3. Completa:")
    print("      • URL del servidor: http://tu-servidor:8000")
    print("      • Token API: [PEGA EL TOKEN DE ARRIBA]")
    print("      • Intervalo: 3 segundos")
    print()
    print("   4. Haz clic en: 💾 Guardar Configuración")
    print()
    print("   5. Haz clic en: 🔌 Probar Conexión")
    print("      → Debe mostrar: ✅ Conexión exitosa")
    print()
    print("   6. Haz clic en: ▶️ Iniciar Agente")
    print()
    print()
    print("PASO 4: Probar el sistema")
    print("─"*70)
    print()
    print("   1. Inicia sesión en CommerceBox con un usuario NORMAL")
    print()
    print("   2. Crea una venta o un trabajo de impresión")
    print()
    print("   3. El agente debe detectarlo e imprimir automáticamente")
    print("      (aunque el trabajo lo haya creado otro usuario)")
    print()
    print("   4. Verifica en la pestaña 📋 Registro del agente:")
    print("      Debe mostrar: '📤 Trabajo enviado al agente'")
    print()
    print()
    print("="*70)
    print("     🎉 ¡CONFIGURACIÓN LISTA!")
    print("="*70)
    print()
    print("⚠️  IMPORTANTE: No olvides actualizar agente_views.py (Paso 1)")
    print()


if __name__ == '__main__':
    print()
    try:
        crear_usuario_sistema()
    except KeyboardInterrupt:
        print()
        print("⚠️  Cancelado por el usuario")
    except Exception as e:
        print()
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()