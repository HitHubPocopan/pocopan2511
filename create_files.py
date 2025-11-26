import pandas as pd
import numpy as np
import json
import os

print("--- Inicializando y verificando archivos del sistema ---")

# 1. Reparar/crear catalogo.xlsx
ARCHIVO_CATALOGO = 'catalogo.xlsx'
try:
    # Intentar leer y reparar el archivo existente
    df = pd.read_excel(ARCHIVO_CATALOGO)
    
    # Reemplazar todos los NaN por valores vacíos
    df = df.replace({np.nan: None})
    
    # Guardar el archivo limpio
    df.to_excel(ARCHIVO_CATALOGO, index=False, engine='openpyxl')
    print("✅ Archivo catalogo.xlsx reparado exitosamente")
    
except Exception as e:
    print(f"⚠️ No se pudo reparar catalogo.xlsx: {e}")
    # Crear archivo vacío
    try:
        columnas = ['Nombre', 'Categoria', 'SubCAT', 'Precio Venta', 'Proveedor', 'Estado']
        df_limpio = pd.DataFrame(columns=columnas)
        df_limpio.to_excel(ARCHIVO_CATALOGO, index=False, engine='openpyxl')
        print("✅ Nuevo archivo catalogo.xlsx creado (vacío)")
    except Exception as e2:
        print(f"❌ Error crítico al crear catalogo.xlsx: {e2}")

# 2. Crear ventas.xlsx con estructura correcta
ARCHIVO_VENTAS = 'ventas.xlsx'
columnas_ventas = [
    'ID_Venta', 'Fecha', 'Hora', 'ID_Cliente', 'Producto', 
    'Cantidad', 'Precio_Unitario', 'Total_Venta', 'Vendedor', 'ID_Terminal'
]

try:
    df_ventas_vacio = pd.DataFrame(columns=columnas_ventas)
    df_ventas_vacio.to_excel(ARCHIVO_VENTAS, index=False, engine='openpyxl')
    print(f"✅ Creado/Verificado {ARCHIVO_VENTAS}")
except Exception as e:
    print(f"❌ Error al crear {ARCHIVO_VENTAS}: {e}")

# 3. Crear contadores.json
ARCHIVO_CONTADORES = 'contadores.json'
contadores_default = {
    "POS1": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
    "POS2": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
    "POS3": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0},
    "TODAS": {"ultimo_cliente": 0, "ultima_venta": 0, "total_ventas": 0}
}
try:
    with open(ARCHIVO_CONTADORES, 'w', encoding='utf-8') as f:
        json.dump(contadores_default, f, indent=4)
    print(f"✅ Creado/Verificado {ARCHIVO_CONTADORES}")
except Exception as e:
    print(f"❌ Error al crear {ARCHIVO_CONTADORES}: {e}")

# 4. Crear config.json
ARCHIVO_CONFIG = 'config.json'
config_default = {
    "iva": 21.0,
    "moneda": "$",
    "empresa": "POCOPAN",
    "backup_automatico": False,
    "mostrar_estadisticas_inicio": True
}
try:
    with open(ARCHIVO_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config_default, f, indent=4)
    print(f"✅ Creado/Verificado {ARCHIVO_CONFIG}")
except Exception as e:
    print(f"❌ Error al crear {ARCHIVO_CONFIG}: {e}")

print("--- Proceso finalizado ---")
print("📝 Archivos listos para usar:")
print(f"   • {ARCHIVO_CATALOGO} - Catálogo de productos")
print(f"   • {ARCHIVO_VENTAS} - Registro de ventas") 
print(f"   • {ARCHIVO_CONTADORES} - Contadores del sistema")
print(f"   • {ARCHIVO_CONFIG} - Configuración general")
