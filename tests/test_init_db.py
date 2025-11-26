import os
import unittest
import tempfile
from datetime import date, time

import pandas as pd

test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_unit.db'))
os.environ['DATABASE_URL'] = f'sqlite:///{test_db_path}'

import app as pocopan_app
from app import (
    app,
    db,
    Producto,
    Venta,
    Contador,
    seed_catalog_from_excel,
    seed_sales_from_excel,
    refresh_contadores,
)


class InitDbTests(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.catalog_path = os.path.join(self.temp_dir.name, 'catalogo.xlsx')
        self.sales_path = os.path.join(self.temp_dir.name, 'ventas.xlsx')
        self.prev_catalog = pocopan_app.CATALOGO_XLSX
        self.prev_sales = pocopan_app.VENTAS_XLSX
        pocopan_app.CATALOGO_XLSX = self.catalog_path
        pocopan_app.VENTAS_XLSX = self.sales_path

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        pocopan_app.CATALOGO_XLSX = self.prev_catalog
        pocopan_app.VENTAS_XLSX = self.prev_sales
        self.temp_dir.cleanup()
        if os.path.exists(test_db_path):
            os.remove(test_db_path)

    def write_catalog(self, rows):
        pd.DataFrame(rows).to_excel(self.catalog_path, index=False)

    def write_sales(self, rows):
        pd.DataFrame(rows).to_excel(self.sales_path, index=False)

    def test_seed_catalog_creates_and_updates_products(self):
        self.write_catalog([
            {'Nombre': 'Prod A', 'Categoria': 'Cat 1', 'SubCAT': 'Sub', 'Precio Venta': 100},
            {'Nombre': 'Prod B', 'Categoria': 'Cat 2', 'SubCAT': 'Otro', 'Precio Venta': 200},
            {'Nombre': 'Prod A', 'Categoria': 'Cat 1', 'SubCAT': 'Sub', 'Precio Venta': 150},
        ])

        result_first = seed_catalog_from_excel()
        self.assertEqual(result_first['created'], 2)
        self.assertEqual(result_first['updated'], 0)

        self.write_catalog([
            {'Nombre': 'Prod A', 'Categoria': 'Cat 1', 'SubCAT': 'Sub', 'Precio Venta': 120},
            {'Nombre': 'Prod B', 'Categoria': 'Cat 2', 'SubCAT': 'Otro', 'Precio Venta': 250},
        ])

        result_second = seed_catalog_from_excel()
        self.assertEqual(result_second['created'], 0)
        self.assertEqual(result_second['updated'], 2)

        prod_a = Producto.query.filter_by(nombre='Prod A').first()
        prod_b = Producto.query.filter_by(nombre='Prod B').first()
        self.assertEqual(prod_a.precio_venta, 120)
        self.assertEqual(prod_b.precio_venta, 250)

    def test_seed_sales_creates_and_updates_records(self):
        self.write_catalog([
            {'Nombre': 'Prod A', 'Categoria': 'Cat 1', 'SubCAT': 'Sub', 'Precio Venta': 100},
        ])
        seed_catalog_from_excel()

        self.write_sales([
            {
                'ID_Venta': 100,
                'Fecha': '2024-01-01',
                'Hora': '10:00',
                'ID_Cliente': 'CLIENTE-POS1-0001',
                'Producto': 'Prod A',
                'Cantidad': 2,
                'Precio_Unitario': 10,
                'Total_Venta': 20,
                'Vendedor': 'pos1',
                'ID_Terminal': 'POS1',
            },
            {
                'ID_Venta': None,
                'Fecha': '2024-01-02',
                'Hora': '11:30',
                'ID_Cliente': '',
                'Producto': 'Prod A',
                'Cantidad': 1,
                'Precio_Unitario': 5,
                'Total_Venta': '',
                'Vendedor': 'pos2',
                'ID_Terminal': 'POS2',
            },
        ])

        first_result = seed_sales_from_excel()
        self.assertEqual(first_result['created'], 2)
        self.assertEqual(first_result['updated'], 0)
        self.assertEqual(Venta.query.count(), 2)

        pos2_sale = Venta.query.filter_by(id_terminal='POS2').first()

        self.write_sales([
            {
                'ID_Venta': 100,
                'Fecha': '2024-01-03',
                'Hora': '10:00',
                'ID_Cliente': 'CLIENTE-POS1-0001',
                'Producto': 'Prod A',
                'Cantidad': 5,
                'Precio_Unitario': 12,
                'Total_Venta': 60,
                'Vendedor': 'pos1',
                'ID_Terminal': 'POS1',
            },
            {
                'ID_Venta': pos2_sale.id_venta,
                'Fecha': '2024-01-04',
                'Hora': '12:00',
                'ID_Cliente': 'CLIENTE-POS2-9999',
                'Producto': 'Prod A',
                'Cantidad': 4,
                'Precio_Unitario': 8,
                'Total_Venta': 32,
                'Vendedor': 'pos2',
                'ID_Terminal': 'POS2',
            },
        ])

        second_result = seed_sales_from_excel()
        self.assertEqual(second_result['created'], 0)
        self.assertEqual(second_result['updated'], 2)

        venta_100 = Venta.query.filter_by(id_venta=100, id_terminal='POS1').first()
        venta_pos2 = Venta.query.filter_by(id_venta=pos2_sale.id_venta, id_terminal='POS2').first()
        self.assertEqual(venta_100.cantidad, 5)
        self.assertEqual(venta_100.total_venta, 60)
        self.assertEqual(venta_pos2.id_cliente, 'CLIENTE-POS2-9999')
        self.assertEqual(venta_pos2.cantidad, 4)

    def test_refresh_contadores_matches_sales_totals(self):
        ventas = [
            Venta(
                id_venta=1,
                fecha=date(2024, 1, 1),
                hora=time(10, 0),
                id_cliente='CLIENTE-POS1-0005',
                producto_nombre='Prod A',
                cantidad=2,
                precio_unitario=10,
                total_venta=20,
                vendedor='pos1',
                id_terminal='POS1',
            ),
            Venta(
                id_venta=2,
                fecha=date(2024, 1, 2),
                hora=time(11, 30),
                id_cliente='CLIENTE-POS2-0010',
                producto_nombre='Prod B',
                cantidad=1,
                precio_unitario=15,
                total_venta=15,
                vendedor='pos2',
                id_terminal='POS2',
            ),
        ]
        db.session.add_all(ventas)
        db.session.commit()

        refresh_contadores()

        pos1 = Contador.query.filter_by(terminal='POS1').first()
        pos2 = Contador.query.filter_by(terminal='POS2').first()
        all_terminals = Contador.query.filter_by(terminal='TODAS').first()

        self.assertEqual(pos1.total_ventas, 1)
        self.assertEqual(pos1.ultima_venta, 1)
        self.assertEqual(pos1.ultimo_cliente, 5)

        self.assertEqual(pos2.total_ventas, 1)
        self.assertEqual(pos2.ultima_venta, 2)
        self.assertEqual(pos2.ultimo_cliente, 10)

        self.assertEqual(all_terminals.total_ventas, 2)
        self.assertEqual(all_terminals.ultima_venta, 2)
        self.assertEqual(all_terminals.ultimo_cliente, 10)


if __name__ == '__main__':
    unittest.main()
