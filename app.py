from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, date, time
import json
import os
import re
import math
from urllib.parse import unquote
from functools import wraps
import logging
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CATALOGO_XLSX = os.path.join(BASE_DIR, 'catalogo.xlsx')
VENTAS_XLSX = os.path.join(BASE_DIR, 'ventas.xlsx')

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
    """Inicializa la base con los datos de catálogo y ventas"""
    with app.app_context():
        db.create_all()
        catalog_result = seed_catalog_from_excel()
        ventas_result = seed_sales_from_excel()
        refresh_contadores()
        if catalog_result['created'] or catalog_result['updated']:
            logger.info(
                f"✅ Catálogo: {catalog_result['created']} nuevos, {catalog_result['updated']} actualizados"
            )
        if ventas_result['created'] or ventas_result['updated']:
            logger.info(
                f"✅ Ventas: {ventas_result['created']} nuevas, {ventas_result['updated']} actualizadas"
            )


def seed_catalog_from_excel():
    result = {'created': 0, 'updated': 0}
    if not os.path.exists(CATALOGO_XLSX):
        logger.warning("catalogo.xlsx no encontrado, omitiendo carga inicial")
        return result
    try:
        import pandas as pd
    except ImportError as exc:
        logger.error(f"Pandas no disponible para cargar catálogo: {exc}")
        return result
    df = pd.read_excel(CATALOGO_XLSX)
    if df.empty:
        logger.warning("catalogo.xlsx está vacío")
        return result
    nombres_vistos = set()
    for _, row in df.iterrows():
        nombre = _clean_string(row.get('Nombre'))
        if not nombre or nombre in nombres_vistos:
            continue
        precio_col = 'Precio Venta' if 'Precio Venta' in row.index else 'Precio_Venta'
        precio = _safe_float(row.get(precio_col))
        if precio is None:
            continue
        categoria = _clean_string(row.get('Categoria'), 'Sin Categoría')
        subcategoria = _clean_string(row.get('SubCAT'))
        proveedor = 'Catálogo'
        producto = Producto.query.filter(
            db.func.lower(Producto.nombre) == nombre.lower()
        ).first()
        if producto:
            producto.categoria = categoria or producto.categoria or 'Sin Categoría'
            producto.subcategoria = subcategoria
            producto.precio_venta = precio
            producto.proveedor = proveedor
            result['updated'] += 1
        else:
            producto = Producto(
                nombre=nombre,
                categoria=categoria or 'Sin Categoría',
                subcategoria=subcategoria,
                precio_venta=precio,
                proveedor=proveedor,
                estado='Disponible'
            )
            db.session.add(producto)
            result['created'] += 1
        nombres_vistos.add(nombre)
    if result['created'] or result['updated']:
        db.session.commit()
    return result


def seed_sales_from_excel():
    result = {'created': 0, 'updated': 0}
    if not os.path.exists(VENTAS_XLSX):
        return result
    try:
        import pandas as pd
    except ImportError as exc:
        logger.error(f"Pandas no disponible para cargar ventas: {exc}")
        return result
    df = pd.read_excel(VENTAS_XLSX)
    if df.empty:
        return result
    next_id = (db.session.query(db.func.max(Venta.id_venta)).scalar() or 0) + 1
    for _, row in df.iterrows():
        id_venta = _safe_int(row.get('ID_Venta'))
        fecha = _parse_date(row.get('Fecha')) or date.today()
        hora = _parse_time(row.get('Hora'))
        id_cliente = _clean_string(row.get('ID_Cliente'))
        producto_nombre = _clean_string(row.get('Producto'))
        cantidad = _safe_int(row.get('Cantidad')) or 0
        precio_unitario = _safe_float(row.get('Precio_Unitario')) or 0
        total_venta = _safe_float(row.get('Total_Venta')) or (cantidad * precio_unitario)
        vendedor = _clean_string(row.get('Vendedor'), 'POS')
        terminal = _clean_string(row.get('ID_Terminal'), 'TODAS') or 'TODAS'
        if not producto_nombre or not cantidad:
            continue
        venta = None
        if id_venta is not None:
            venta = Venta.query.filter_by(id_venta=id_venta, id_terminal=terminal).first()
        if venta:
            venta.fecha = fecha
            venta.hora = hora
            venta.id_cliente = id_cliente or venta.id_cliente
            venta.producto_nombre = producto_nombre
            venta.cantidad = cantidad
            venta.precio_unitario = precio_unitario
            venta.total_venta = total_venta
            venta.vendedor = vendedor
            result['updated'] += 1
        else:
            assigned_id = id_venta or next_id
            if id_venta is None:
                next_id += 1
            venta = Venta(
                id_venta=assigned_id,
                fecha=fecha,
                hora=hora,
                id_cliente=id_cliente or f"CLIENTE-{terminal}-{assigned_id:04d}",
                producto_nombre=producto_nombre,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                total_venta=total_venta,
                vendedor=vendedor,
                id_terminal=terminal
            )
            db.session.add(venta)
            result['created'] += 1
    if result['created'] or result['updated']:
        db.session.commit()
    return result


def refresh_contadores():
    terminales = ['POS1', 'POS2', 'POS3', 'TODAS']
    for terminal in terminales:
        contador = Contador.query.filter_by(terminal=terminal).first()
        if not contador:
            contador = Contador(terminal=terminal)
            db.session.add(contador)
        query = Venta.query if terminal == 'TODAS' else Venta.query.filter_by(id_terminal=terminal)
        contador.total_ventas = query.count()
        contador.ultima_venta = query.with_entities(db.func.max(Venta.id_venta)).scalar() or 0
        contador.ultimo_cliente = _max_cliente_sequence(query.with_entities(Venta.id_cliente).all())
    db.session.commit()


def _clean_string(value, default=''):
    if value is None:
        return default
    if isinstance(value, str):
        cleaned = re.sub(r'\s+', ' ', value).strip()
        return cleaned if cleaned else default
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return default
        return str(value).strip()
    return default


def _safe_float(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.replace('$', '').replace(',', '.').strip()
        cleaned = cleaned.replace(' ', '')
        if not cleaned:
            return None
        value = cleaned
    try:
        result = float(value)
        if math.isnan(result):
            return None
        return result
    except (TypeError, ValueError):
        return None


def _safe_int(value):
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _parse_time(value):
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        for fmt in ('%H:%M:%S', '%H:%M'):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
    return None


def _extract_cliente_sequence(value):
    if not value:
        return 0
    match = re.search(r'(\d+)$', value)
    return int(match.group(1)) if match else 0


def _max_cliente_sequence(rows):
    max_seq = 0
    for item in rows:
        value = item
        if isinstance(item, (list, tuple)):
            value = item[0]
        elif hasattr(item, '_mapping'):
            value = next(iter(item._mapping.values()), None)
        max_seq = max(max_seq, _extract_cliente_sequence(value))
    return max_seq

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

def calculate_totals(carrito):
    carrito = carrito or []
    subtotal = 0
    for item in carrito:
        if not isinstance(item, dict):
            continue
        if item.get('subtotal') is not None:
            subtotal += item.get('subtotal', 0)
        else:
            subtotal += (item.get('precio', 0) or 0) * (item.get('cantidad', 0) or 0)
    iva = subtotal * (CONFIG['iva'] / 100)
    total = subtotal + iva
    return {
        'subtotal': round(subtotal, 2),
        'iva': round(iva, 2),
        'total': round(total, 2),
        'porcentaje_iva': CONFIG['iva']
    }

@app.route('/punto-venta')
@login_required
def punto_venta():
    usuario = session.get('usuario')
    rol = session.get('rol')
    terminal = session.get('terminal')
    
    carrito_actual = get_carrito()
    totales = calculate_totals(carrito_actual)
    
    contador = Contador.query.filter_by(terminal=terminal).first()
    id_cliente_proximo = (contador.ultimo_cliente + 1) if contador else 1
    
    productos = Producto.query.filter_by(estado='Disponible').all()
    
    return render_template('pos.html',
                         productos=productos,
                         carrito=carrito_actual,
                         usuario_actual=usuario,
                         rol_actual=rol,
                         terminal_actual=terminal,
                         totales=totales,
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
@login_required
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

@app.route('/detalles-producto/<path:producto_nombre>')
@login_required
def detalles_producto(producto_nombre):
    try:
        producto = Producto.query.filter(
            db.func.lower(Producto.nombre) == unquote(producto_nombre).lower()
        ).first()
        if not producto:
            return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404
        return jsonify({'success': True, 'producto': producto.to_dict()})
    except Exception as e:
        logger.error(f"Error en detalles-producto: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno'}), 500

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
        
        totales = calculate_totals(carrito)
        
        return jsonify({
            'success': True,
            'message': f'{producto.nombre} agregado al carrito',
            'carrito': carrito,
            'totales': totales
        })
        
    except Exception as e:
        logger.error(f"Error en agregar-carrito: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/eliminar-carrito/<int:index>', methods=['DELETE'])
@login_required
def eliminar_carrito(index):
    try:
        carrito = get_carrito()
        if index < 0 or index >= len(carrito):
            return jsonify({'success': False, 'message': 'Ítem no encontrado en el carrito'}), 404
        item_eliminado = carrito.pop(index)
        session[f'carrito_{session.get('""usuario""')}] = carrito
        totales = calculate_totals(carrito)
        return jsonify({
            'success': True,
            'message': f"{item_eliminado.get('producto', 'Producto')} eliminado del carrito",
            'carrito': carrito,
            'totales': totales
        })
    except Exception as e:
        logger.error(f"Error en eliminar-carrito: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/limpiar-carrito', methods=['DELETE'])
@login_required
def limpiar_carrito():
    try:
        usuario = session.get('usuario')
        session[f'carrito_{usuario}'] = []
        totales = calculate_totals([])
        return jsonify({
            'success': True,
            'message': 'Carrito limpiado correctamente',
            'carrito': [],
            'totales': totales
        })
    except Exception as e:
        logger.error(f"Error en limpiar-carrito: {str(e)}")
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
