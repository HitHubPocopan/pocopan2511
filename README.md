# 🍞 POCOPAN - Sistema POS

Sistema de Punto de Venta (POS) con panel administrativo para gestión de productos y ventas.

**Estado**: Listo para hostear en Vercel ✅

## 🚀 DEPLOY EN VERCEL (5 MINUTOS)

Lee el archivo **`DEPLOYMENT.md`** para instrucciones paso a paso.

En resumen:
1. Sube el código a GitHub (`git push`)
2. Crea BD PostgreSQL en Vercel
3. Conecta el repositorio a Vercel
4. Configura variables de entorno
5. ¡Listo! 🎉

## 🔑 Usuarios por Defecto

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| admin | admin123 | Administrador |
| pos1 | pos1123 | Vendedor POS 1 |
| pos2 | pos2123 | Vendedor POS 2 |
| pos3 | pos3123 | Vendedor POS 3 |

## 📋 Funcionalidades

- ✅ Autenticación de usuarios
- ✅ Gestión de productos (crear, editar, eliminar)
- ✅ Punto de venta con carrito
- ✅ Dashboard de ventas
- ✅ Múltiples terminales
- ✅ Base de datos PostgreSQL
- ✅ Interfaz responsive

## 💻 Desarrollo Local

```bash
pip install -r requirements.txt
python app.py
```

Acceder a http://localhost:5000

## 📁 Estructura

```
├── app.py              # Aplicación Flask
├── models.py           # Modelos de base de datos
├── api/index.py        # Punto de entrada para Vercel
├── templates/          # Templates HTML
├── static/             # Archivos CSS/JS
├── requirements.txt    # Dependencias
├── vercel.json         # Configuración Vercel
└── DEPLOYMENT.md       # Guía de deployment
```

## 🔐 IMPORTANTE

Cambiar contraseñas por defecto antes de usar en producción.

---

**Documentación completa**: Ver `DEPLOYMENT.md`
