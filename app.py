from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, date, time
import json
import os
import re
from urllib.parse import unquote
from functools import wraps
import logging
from dotenv import load_dotenv

load_dotenv()

from models import db, Producto, Venta, Contador

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv('SECRET_KEY', 'pocopan_secure_key_2024_v2_con_db')

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DATABASE_URL = 'sqlite:///pocopan.db'
else:
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {
        'connect_timeout': 10,
        'application_name': 'pocopan_app'
    } if 'postgresql' in DATABASE_URL else {}
}
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

db.init_app(app)

CONFIG = {
    "iva": 21.0,
    "moneda": "$",
    "empresa": "POCOPAN",
    "usuarios": {
        "admin": {"password": "admin123", "rol": "admin", "terminal": "TODAS"},
        "pos1": {"password": "pos1123", "rol": "pos", "terminal": "POS1"},
        "pos2": {"password": "pos2123", "rol": "pos", "terminal": "POS2"},
        "pos3": {"password": "pos3123", "rol": "pos", "terminal": "POS3"}
    }
}

def init_db():
    """Inicializa la base de datos con datos de ejemplo"""
    with app.app_context():
        db.create_all()
        
        if Producto.query.first() is None:
            logger.info("Creando productos de ejemplo...")
            productos = [
                Producto(nombre='Cajas Verdes GRANJA ANIMALES DINOS', categoria='Ingenio', subcategoria='Madera Ingenio', precio_venta=25000.0, proveedor='Proveedor A'),
                Producto(nombre='Pezca Gusanos', categoria='Ingenio', subcategoria='Madera Ingenio', precio_venta=30800.0, proveedor='Proveedor B'),
                Producto(nombre='Juego de Mesa Clásico', categoria='Juego Meza', subcategoria='Estrategia', precio_venta=15500.0, proveedor='Proveedor C'),
                Producto(nombre='Rompecabezas 1000 Piezas', categoria='Puzzle', subcategoria='Educativo', precio_venta=12000.0, proveedor='Proveedor D'),
                Producto(nombre='Muñeco Coleccionable', categoria='Figuras', subcategoria='Acción', precio_venta=8900.0, proveedor='Proveedor E'),
            ]
            for p in productos:
                db.session.add(p)
            db.session.commit()
            logger.info(f"✅ {len(productos)} productos creados")
        
        for terminal in ['POS1', 'POS2', 'POS3', 'TODAS']:
            if not Contador.query.filter_by(terminal=terminal).first():
                contador = Contador(terminal=terminal)
                db.session.add(contador)
        db.session.commit()
        logger.info("✅ Contadores inicializados")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session or session.get('rol') != 'admin':
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
            if is_ajax:
                return jsonify({'error': 'No autorizado', 'message': 'Acceso denegado'}), 403
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    if session.get('rol') == 'admin':
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('punto_venta'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')
        
        if usuario in CONFIG['usuarios']:
            user_config = CONFIG['usuarios'][usuario]
            if user_config['password'] == password:
                session['usuario'] = usuario
                session['rol'] = user_config['rol']
                session['terminal'] = user_config['terminal']
                session.permanent = True
                
                if user_config['rol'] == 'admin':
                    return redirect(url_for('dashboard'))
                else:
                    return redirect(url_for('punto_venta'))
        
        return render_template('login.html', error='Usuario o contraseña incorrectos')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def get_carrito():
    usuario = session.get('usuario')
    if f'carrito_{usuario}' not in session:
        session[f'carrito_{usuario}'] = []
    return session[f'carrito_{usuario}']

@app.route('/punto-venta')
@login_required
def punto_venta():
    usuario = session.get('usuario')
    rol = session.get('rol')
    terminal = session.get('terminal')
    
    carrito_actual = get_carrito()
    
    contador = Contador.query.filter_by(terminal=terminal).first()
    id_cliente_proximo = (contador.ultimo_cliente + 1) if contador else 1
    
    productos = Producto.query.filter_by(estado='Disponible').all()
    
    return render_template('pos.html',
                         productos=productos,
                         carrito=carrito_actual,
                         usuario_actual=usuario,
                         rol_actual=rol,
                         terminal_actual=terminal,
                         id_cliente_actual=f"CLIENTE-{terminal}-{id_cliente_proximo:04d}")

@app.route('/dashboard')
@app.route('/dashboard/<terminal_id>')
@login_required
def dashboard(terminal_id=None):
    rol = session.get('rol')
    terminal = session.get('terminal')
    
    if terminal_id is None:
        terminal_id = terminal if rol != 'admin' else 'TODAS'
    
    if rol == 'pos' and terminal_id != terminal:
        return redirect(url_for('dashboard'))
    
    if terminal_id == 'TODAS':
        ventas = Venta.query.all()
        terminal_nombre = "General (Todas las Terminales)"
    else:
        ventas = Venta.query.filter_by(id_terminal=terminal_id).all()
        terminal_nombre = f"Terminal {terminal_id}"
    
    if ventas:
        ids_venta_unicos = len(set(v.id_venta for v in ventas))
        ingresos_totales = sum(v.total_venta for v in ventas)
        ventas_hoy = [v for v in ventas if v.fecha == date.today()]
        ventas_hoy_count = len(set(v.id_venta for v in ventas_hoy))
    else:
        ids_venta_unicos = 0
        ingresos_totales = 0
        ventas_hoy_count = 0
    
    productos_disponibles = Producto.query.filter_by(estado='Disponible').count()
    
    stats = {
        'ventas_totales': ids_venta_unicos,
        'ingresos_totales': f"{CONFIG['moneda']}{ingresos_totales:,.2f}",
        'productos_catalogo': productos_disponibles,
        'usuarios_activos': 1,
        'ventas_hoy_count': ventas_hoy_count,
        'dashboard_nombre': f"Dashboard - {terminal_nombre}",
        'terminal_actual': terminal_id
    }
    
    return render_template('dashboard.html',
                         stats=stats,
                         empresa=CONFIG['empresa'],
                         rol_actual=rol,
                         terminal_actual=terminal,
                         now=datetime.now())

@app.route('/editor-catalogo')
@admin_required
def editor_catalogo():
    productos = Producto.query.all()
    return render_template('editor_catalogo.html',
                         productos=productos,
                         usuario_actual=session.get('usuario'),
                         rol_actual=session.get('rol'),
                         terminal_actual=session.get('terminal'))

@app.route('/obtener-producto/<path:producto_nombre>')
@admin_required
def obtener_producto(producto_nombre):
    try:
        producto_decodificado = unquote(producto_nombre)
        producto_limpio = re.sub(r'\s+', ' ', producto_decodificado).strip()
        
        logger.info(f"🔍 Buscando producto: '{producto_limpio}'")
        
        producto = Producto.query.filter(
            db.func.lower(Producto.nombre) == producto_limpio.lower()
        ).first()
        
        if producto:
            logger.info(f"✅ Producto encontrado: {producto.nombre}")
            return jsonify(producto.to_dict())
        
        logger.warning(f"❌ Producto no encontrado: {producto_limpio}")
        return jsonify({'error': 'Producto no encontrado'}), 404
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo producto: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/actualizar-producto', methods=['POST'])
@admin_required
def actualizar_producto():
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Content-Type debe ser application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos JSON'}), 400
        
        logger.info(f"📝 Datos recibidos para actualizar: {data}")
        
        producto_original = data.get('producto_original', '').strip()
        nuevo_nombre = data.get('nombre', '').strip()
        nueva_categoria = data.get('categoria', '').strip() or 'Sin Categoría'
        nueva_subcategoria = data.get('subcategoria', '').strip()
        nuevo_precio = data.get('precio_venta', 0)
        nuevo_proveedor = data.get('proveedor', '').strip() or 'Sin Proveedor'
        
        if not producto_original or not nuevo_nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        try:
            precio_float = float(nuevo_precio)
            if precio_float <= 0:
                return jsonify({'success': False, 'message': 'El precio debe ser mayor a 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Precio inválido'}), 400
        
        producto = Producto.query.filter(
            db.func.lower(Producto.nombre) == producto_original.lower()
        ).first()
        
        if not producto:
            return jsonify({'success': False, 'message': f'Producto no encontrado: {producto_original}'}), 404
        
        producto.nombre = nuevo_nombre
        producto.categoria = nueva_categoria
        producto.subcategoria = nueva_subcategoria
        producto.precio_venta = precio_float
        producto.proveedor = nuevo_proveedor
        
        db.session.commit()
        logger.info(f"✅ Producto actualizado en BD: {nuevo_nombre}")
        
        return jsonify({
            'success': True,
            'message': f'Producto "{nuevo_nombre}" actualizado correctamente'
        })
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error actualizando producto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/agregar-producto', methods=['POST'])
@admin_required
def agregar_producto():
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Content-Type debe ser application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos JSON'}), 400
        
        logger.info(f"📝 Datos recibidos para agregar: {data}")
        
        nombre = re.sub(r'\s+', ' ', data.get('nombre', '')).strip()
        categoria = data.get('categoria', '').strip() or 'Sin Categoría'
        subcategoria = data.get('subcategoria', '').strip()
        precio_venta = data.get('precio_venta', 0)
        proveedor = data.get('proveedor', '').strip() or 'Sin Proveedor'
        
        if not nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        try:
            precio_float = float(precio_venta)
            if precio_float <= 0:
                return jsonify({'success': False, 'message': 'El precio debe ser mayor a 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Precio inválido'}), 400
        
        existente = Producto.query.filter(
            db.func.lower(Producto.nombre) == nombre.lower()
        ).first()
        
        if existente:
            return jsonify({'success': False, 'message': f'El producto "{nombre}" ya existe'}), 400
        
        nuevo_producto = Producto(
            nombre=nombre,
            categoria=categoria,
            subcategoria=subcategoria,
            precio_venta=precio_float,
            proveedor=proveedor,
            estado='Disponible'
        )
        
        db.session.add(nuevo_producto)
        db.session.commit()
        logger.info(f"✅ Producto agregado a BD: {nombre}")
        
        return jsonify({
            'success': True,
            'message': f'Producto "{nombre}" agregado correctamente'
        })
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error agregando producto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/eliminar-producto', methods=['POST'])
@admin_required
def eliminar_producto():
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Content-Type debe ser application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos JSON'}), 400
        
        producto_nombre = re.sub(r'\s+', ' ', data.get('producto_nombre', '')).strip()
        
        if not producto_nombre:
            return jsonify({'success': False, 'message': 'Nombre del producto requerido'}), 400
        
        logger.info(f"🗑️ Intentando eliminar producto: {producto_nombre}")
        
        producto = Producto.query.filter(
            db.func.lower(Producto.nombre) == producto_nombre.lower()
        ).first()
        
        if not producto:
            return jsonify({'success': False, 'message': f'Producto no encontrado: {producto_nombre}'}), 404
        
        db.session.delete(producto)
        db.session.commit()
        logger.info(f"✅ Producto eliminado de BD: {producto_nombre}")
        
        return jsonify({
            'success': True,
            'message': f'Producto "{producto_nombre}" eliminado correctamente'
        })
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error eliminando producto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/buscar-productos')
def buscar_productos():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    productos = Producto.query.filter(
        Producto.nombre.ilike(f'%{query}%'),
        Producto.estado == 'Disponible'
    ).limit(10).all()
    
    return jsonify([p.nombre for p in productos])

@app.route('/agregar-carrito', methods=['POST'])
@login_required
def agregar_carrito():
    try:
        data = request.get_json()
        producto_nombre = data.get('producto', '').strip()
        cantidad = int(data.get('cantidad', 1))
        
        if not producto_nombre or cantidad <= 0:
            return jsonify({'success': False, 'message': 'Datos inválidos'}), 400
        
        producto = Producto.query.filter(
            db.func.lower(Producto.nombre) == producto_nombre.lower()
        ).first()
        
        if not producto:
            return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404
        
        carrito = get_carrito()
        
        item = {
            'producto': producto.nombre,
            'cantidad': cantidad,
            'precio': producto.precio_venta,
            'subtotal': cantidad * producto.precio_venta,
            'proveedor': producto.proveedor,
            'categoria': producto.categoria,
            'timestamp': datetime.now().isoformat()
        }
        
        carrito.append(item)
        session[f'carrito_{session.get("usuario")}'] = carrito
        
        subtotal = sum(i['subtotal'] for i in carrito)
        iva = subtotal * 0.21
        total = subtotal + iva
        
        return jsonify({
            'success': True,
            'message': f'{producto.nombre} agregado al carrito',
            'carrito': carrito,
            'totales': {
                'subtotal': round(subtotal, 2),
                'iva': round(iva, 2),
                'total': round(total, 2),
                'porcentaje_iva': 21
            }
        })
        
    except Exception as e:
        logger.error(f"Error en agregar-carrito: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/finalizar-venta', methods=['POST'])
@login_required
def finalizar_venta():
    try:
        carrito = get_carrito()
        terminal_id = session.get('terminal')
        usuario = session.get('usuario')
        
        if not carrito:
            return jsonify({'success': False, 'message': 'El carrito está vacío'}), 400
        
        contador = Contador.query.filter_by(terminal=terminal_id).first()
        if not contador:
            return jsonify({'success': False, 'message': 'Terminal no configurada'}), 500
        
        id_cliente = contador.ultimo_cliente + 1
        id_venta_actual = contador.ultima_venta + 1
        fecha = date.today()
        hora = datetime.now().time()
        
        for item in carrito:
            venta = Venta(
                id_venta=id_venta_actual,
                fecha=fecha,
                hora=hora,
                id_cliente=f"CLIENTE-{terminal_id}-{id_cliente:04d}",
                producto_nombre=item['producto'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio'],
                total_venta=item['subtotal'],
                vendedor=f'POS {terminal_id}',
                id_terminal=terminal_id
            )
            db.session.add(venta)
        
        contador.ultimo_cliente = id_cliente
        contador.ultima_venta = id_venta_actual
        contador.total_ventas += 1
        
        db.session.commit()
        
        subtotal = sum(i['subtotal'] for i in carrito)
        iva = subtotal * 0.21
        total = subtotal + iva
        
        session[f'carrito_{usuario}'] = []
        
        logger.info(f"✅ Venta finalizada: {id_venta_actual} - Terminal {terminal_id} - ${total:,.2f}")
        
        return jsonify({
            'success': True,
            'message': 'Venta finalizada exitosamente',
            'resumen': {
                'id_venta': id_venta_actual,
                'id_cliente': f"CLIENTE-{terminal_id}-{id_cliente:04d}",
                'total_productos': len(carrito),
                'totales': {
                    'subtotal': round(subtotal, 2),
                    'iva': round(iva, 2),
                    'total': round(total, 2)
                },
                'fecha': str(fecha),
                'hora': str(hora)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error en finalizar-venta: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/diagnostico')
def diagnostico():
    try:
        productos_count = Producto.query.count()
        ventas_count = Venta.query.count()
        
        return jsonify({
            'status': 'OK',
            'mensaje': 'Sistema POCOPAN operativo con BD',
            'productos': productos_count,
            'ventas_registradas': ventas_count,
            'database': 'PostgreSQL' if 'postgresql' in DATABASE_URL else 'SQLite'
        })
    except Exception as e:
        return jsonify({'status': 'ERROR', 'mensaje': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', mensaje="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', mensaje="Error interno del servidor"), 500

if __name__ == '__main__':
    with app.app_context():
        init_db()
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
