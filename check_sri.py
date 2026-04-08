import sys
from zeep import Client

url_autorizacion = "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
client_autorizacion = Client(url_autorizacion)
clave_acceso = "0804202601172259995600120010020000000021234567810"

try:
    print(f"Consultando {clave_acceso} en SRI Produccion...")
    respuesta_aut = client_autorizacion.service.autorizacionComprobante(clave_acceso)
    print(respuesta_aut)
except Exception as e:
    print(f"Error: {e}")
