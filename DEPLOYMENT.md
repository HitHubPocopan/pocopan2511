# Guía de Deployment POCOPAN en Vercel

## 📋 PASOS RÁPIDOS (Haz esto en orden)

### PASO 1: Subir código a GitHub
```bash
cd C:\Users\54225\Desktop\clonacon\2511

git init
git add .
git commit -m "Initial commit - POCOPAN ready for Vercel"
git branch -M main
git remote add origin https://github.com/HitHubPocopan/pocopan2511.git
git push -u origin main
```

### PASO 2: Crear Base de Datos en Vercel Postgres
1. Ir a https://vercel.com/dashboard
2. Dashboard → Storage → Create Database
3. Seleccionar "Postgres"
4. Nombre: "pocopan-db"
5. Region: Más cercana a ti
6. **Copiar la conexión string (DATABASE_URL)**

### PASO 3: Conectar GitHub a Vercel
1. Ir a https://vercel.com/new
2. Seleccionar "Import Git Repository"
3. Buscar y seleccionar: `HitHubPocopan/pocopan2511`
4. Hacer click en Import

### PASO 4: Configurar Variables de Entorno
En Vercel (después de importar el repositorio):
1. Environment Variables
2. Añadir estas 3 variables:

| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | (Pegar la URL de Postgres de PASO 2) |
| `SECRET_KEY` | `pocopan-super-secret-key-2024-vercel` |
| `FLASK_ENV` | `production` |

3. Hacer click en Deploy

### PASO 5: Inicializar Base de Datos
Una vez que el primer deploy termina:
1. Ir a tu proyecto en Vercel
2. Hacer click en los "..." (más opciones)
3. Seleccionar "Environment"
4. En la terminal:
```bash
vercel env pull .env.production
```

5. Ejecutar el setup inicial:
```bash
python setup_vercel.py
```

---

## 🔍 VERIFICAR QUE TODO FUNCIONA

1. Ir a https://tu-proyecto.vercel.app/diagnostico
2. Deberías ver:
```json
{
  "status": "OK",
  "mensaje": "Sistema POCOPAN operativo con BD",
  "productos": 5,
  "ventas_registradas": 0,
  "database": "PostgreSQL"
}
```

---

## 📁 Estructura del Proyecto

```
pocopan2511/
├── api/
│   └── index.py          ← Punto de entrada Vercel
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── editor_catalogo.html
│   ├── error.html
│   ├── login.html
│   └── pos.html
├── static/
│   └── css/
├── app.py                ← Aplicación Flask
├── models.py             ← Modelos de BD
├── requirements.txt      ← Dependencias
├── vercel.json           ← Config Vercel
├── setup_vercel.py       ← Script de setup
├── .env.example          ← Referencia de variables
├── .gitignore            ← Archivos a ignorar
└── DEPLOYMENT.md         ← Esta guía
```

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### ❌ "ModuleNotFoundError: No module named 'models'"
- Verifica que `models.py` esté en la raíz (junto a `app.py`)
- Reinicia el deploy

### ❌ "Connection refused" en DATABASE_URL
- Verifica que DATABASE_URL está correctamente en Environment Variables
- Comprueba que Postgres está activo en Vercel Storage
- Espera 2-3 minutos después de crear la BD

### ❌ "FATAL: password authentication failed"
- Copia nuevamente la DATABASE_URL completa de Vercel
- Asegúrate de no tener espacios extras

### ❌ Error "Timed out" en deploy
- Aumenta el timeout en vercel.json si es necesario
- Verifica la conexión a internet

### ✅ Verificar logs en tiempo real
```
Vercel Dashboard → Deployments → Seleccionar deployment → Logs
```

---

## 💻 DESARROLLO LOCAL

```bash
# Crear archivo .env local
echo DATABASE_URL=sqlite:///pocopan.db > .env

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python app.py

# Acceder a http://localhost:5000
# Usuario: admin
# Contraseña: admin123
```

---

## 📊 URLs Útiles

- **Vercel Dashboard**: https://vercel.com/dashboard
- **Tu App**: https://tu-proyecto.vercel.app/
- **Storage**: https://vercel.com/dashboard/stores
- **Settings**: https://vercel.com/dashboard/settings

---

## 🔐 SEGURIDAD (Importante después del deploy)

1. **Cambiar contraseñas por defecto** en `CONFIG` de `app.py`
2. **Cambiar SECRET_KEY** a algo más seguro
3. **Habilitar HTTPS** (Vercel lo hace automáticamente)
4. **Backups de BD** - Configurar en Vercel Postgres
