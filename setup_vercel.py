import os
import sys
from app import app, db, init_db

if __name__ == '__main__':
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL no configurada")
        print("Asegúrate de configurar DATABASE_URL en Vercel Environment Variables")
        sys.exit(1)
    
    print(f"🔗 Conectando a base de datos...")
    print(f"🗄️  URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    
    with app.app_context():
        try:
            print("📊 Inicializando base de datos...")
            init_db()
            print("✅ Base de datos inicializada correctamente")
            print("✅ Productos de ejemplo creados")
            print("✅ Contadores inicializados")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            sys.exit(1)
