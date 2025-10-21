#!/usr/bin/env python3
"""
🧪 SCRIPT DE PRUEBA DE ENDPOINTS - Punto de Venta
Prueba directamente los endpoints para diagnosticar el error 404
"""

import requests
import json
import sys
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
ENDPOINTS_TO_TEST = [
    {
        "name": "URL INCORRECTA (debe dar 404)",
        "url": "/panel/ventas/api/procesar/",
        "expected": 404,
        "color": "yellow"
    },
    {
        "name": "URL CORRECTA",
        "url": "/api/ventas/api/procesar/",
        "expected": [200, 201, 400, 403, 500],
        "color": "green"
    },
    {
        "name": "Reimprimir Ticket (URL INCORRECTA)",
        "url": "/panel/ventas/00000000-0000-0000-0000-000000000000/reimprimir-ticket/",
        "expected": 404,
        "color": "yellow"
    },
    {
        "name": "Reimprimir Ticket (URL CORRECTA)",
        "url": "/api/ventas/ventas/00000000-0000-0000-0000-000000000000/reimprimir-ticket/",
        "expected": [200, 201, 400, 403, 404, 500],
        "color": "green"
    }
]

# Colores ANSI
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

def print_header(text):
    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.NC}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.NC}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.NC}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.NC}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.NC}")

def test_endpoint(name, url, expected_codes, method="POST"):
    """Prueba un endpoint específico"""
    full_url = f"{BASE_URL}{url}"
    
    print(f"\n{Colors.BOLD}Probando: {name}{Colors.NC}")
    print(f"URL: {full_url}")
    print(f"Método: {method}")
    
    # Datos de prueba
    data = {
        "items": [],
        "cliente_id": None,
        "tipo_venta": "CONTADO",
        "metodo_pago": "EFECTIVO",
        "monto_recibido": 0
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-CSRFToken": "test-token-123"
    }
    
    try:
        # Hacer la petición
        if method == "POST":
            response = requests.post(full_url, json=data, headers=headers, timeout=5)
        else:
            response = requests.get(full_url, headers=headers, timeout=5)
        
        status_code = response.status_code
        
        # Normalizar expected_codes a lista
        if not isinstance(expected_codes, list):
            expected_codes = [expected_codes]
        
        # Analizar resultado
        print(f"Status Code: {status_code}")
        
        if status_code in expected_codes:
            if status_code == 404:
                print_warning(f"HTTP {status_code} - Endpoint NO existe (esperado para URL incorrecta)")
            elif status_code == 403:
                print_success(f"HTTP {status_code} - Endpoint EXISTE (error CSRF es normal sin sesión)")
            elif status_code == 400:
                print_success(f"HTTP {status_code} - Endpoint EXISTE (error de validación es normal)")
            elif status_code in [200, 201]:
                print_success(f"HTTP {status_code} - Endpoint funciona PERFECTAMENTE")
            elif status_code == 500:
                print_warning(f"HTTP {status_code} - Endpoint existe pero hay error en el servidor")
                try:
                    print(f"Error: {response.text[:200]}")
                except:
                    pass
            else:
                print_info(f"HTTP {status_code}")
        else:
            if status_code == 404 and 404 not in expected_codes:
                print_error(f"HTTP {status_code} - 🚨 PROBLEMA: Este endpoint debería existir pero NO existe")
            else:
                print_warning(f"HTTP {status_code} - Código inesperado")
        
        # Mostrar respuesta si es JSON
        try:
            response_json = response.json()
            print(f"Respuesta: {json.dumps(response_json, indent=2)[:300]}")
        except:
            if response.text and len(response.text) < 200:
                print(f"Respuesta: {response.text}")
        
        return status_code
        
    except requests.exceptions.ConnectionError:
        print_error("No se pudo conectar al servidor")
        print_info("Verifica que el servidor esté corriendo en localhost")
        return None
    except requests.exceptions.Timeout:
        print_error("Timeout - El servidor no respondió")
        return None
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def main():
    print_header("🧪 PRUEBA DE ENDPOINTS - PUNTO DE VENTA")
    
    print(f"Servidor: {BASE_URL}")
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Probar conexión básica
    print_header("TEST 0: Verificando servidor")
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code in [200, 301, 302]:
            print_success("Servidor está corriendo")
        else:
            print_warning(f"Servidor responde con código {response.status_code}")
    except:
        print_error("Servidor NO está corriendo")
        print_info("Inicia el servidor con: docker-compose up -d")
        sys.exit(1)
    
    # Probar cada endpoint
    print_header("PRUEBAS DE ENDPOINTS")
    results = {}
    
    for i, endpoint in enumerate(ENDPOINTS_TO_TEST, 1):
        print(f"\n{'─' * 60}")
        print(f"TEST {i}/{len(ENDPOINTS_TO_TEST)}")
        status = test_endpoint(
            endpoint["name"],
            endpoint["url"],
            endpoint["expected"]
        )
        results[endpoint["name"]] = status
    
    # Resumen final
    print_header("📊 RESUMEN DE RESULTADOS")
    
    for name, status in results.items():
        if status == 404 and "INCORRECTA" in name:
            print_success(f"{name}: HTTP {status} ✓")
        elif status in [200, 201, 400, 403] and "CORRECTA" in name:
            print_success(f"{name}: HTTP {status} ✓")
        elif status == 404 and "CORRECTA" in name:
            print_error(f"{name}: HTTP {status} ✗ - ENDPOINT NO EXISTE")
        elif status:
            print_warning(f"{name}: HTTP {status}")
        else:
            print_error(f"{name}: Sin respuesta")
    
    # Diagnóstico
    print_header("🔍 DIAGNÓSTICO")
    
    # Verificar URL correcta
    url_correcta_status = results.get("URL CORRECTA")
    if url_correcta_status == 404:
        print_error("PROBLEMA CRÍTICO: El endpoint /api/ventas/api/procesar/ NO existe")
        print_info("Soluciones:")
        print("  1. Verifica apps/sales_management/urls.py")
        print("  2. Verifica commercebox/urls.py")
        print("  3. Reinicia el servidor: docker-compose restart commercebox_web")
    elif url_correcta_status in [200, 201, 400, 403]:
        print_success("El endpoint /api/ventas/api/procesar/ EXISTE correctamente")
        print_info("El problema puede ser:")
        print("  1. Caché del navegador (Ctrl + Shift + R)")
        print("  2. El archivo JavaScript no se actualizó")
        print("  3. El servidor necesita reiniciarse")
    
    print("\n" + "=" * 60)
    print("Pruebas completadas")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPrueba cancelada por el usuario")
        sys.exit(0)