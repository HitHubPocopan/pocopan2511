from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()

class Producto(db.Model):
    __tablename__ = 'productos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), unique=True, nullable=False)
    categoria = db.Column(db.String(100), default='Sin Categoría')
    subcategoria = db.Column(db.String(100))
    precio_venta = db.Column(db.Float, nullable=False)
    proveedor = db.Column(db.String(100), default='Sin Proveedor')
    estado = db.Column(db.String(50), default='Disponible')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'categoria': self.categoria,
            'subcategoria': self.subcategoria,
            'precio_venta': self.precio_venta,
            'proveedor': self.proveedor,
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }

class Venta(db.Model):
    __tablename__ = 'ventas'
    
    id = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.Date, default=date.today)
    hora = db.Column(db.Time)
    id_cliente = db.Column(db.String(50))
    producto_nombre = db.Column(db.String(255))
    cantidad = db.Column(db.Integer)
    precio_unitario = db.Column(db.Float)
    total_venta = db.Column(db.Float)
    vendedor = db.Column(db.String(100))
    id_terminal = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            'id_venta': self.id_venta,
            'fecha': str(self.fecha) if self.fecha else None,
            'hora': str(self.hora) if self.hora else None,
            'id_cliente': self.id_cliente,
            'producto_nombre': self.producto_nombre,
            'cantidad': self.cantidad,
            'precio_unitario': self.precio_unitario,
            'total_venta': self.total_venta,
            'vendedor': self.vendedor,
            'id_terminal': self.id_terminal
        }

class Contador(db.Model):
    __tablename__ = 'contadores'
    
    id = db.Column(db.Integer, primary_key=True)
    terminal = db.Column(db.String(50), unique=True, nullable=False)
    ultimo_cliente = db.Column(db.Integer, default=0)
    ultima_venta = db.Column(db.Integer, default=0)
    total_ventas = db.Column(db.Integer, default=0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'terminal': self.terminal,
            'ultimo_cliente': self.ultimo_cliente,
            'ultima_venta': self.ultima_venta,
            'total_ventas': self.total_ventas,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
