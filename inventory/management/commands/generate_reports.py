# management/commands/generate_reports.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from inventory.inventory import models
from inventory.models import Product, StockMovement
import csv
import os

class Command(BaseCommand):
    help = 'Genera reportes del inventario'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['stock', 'movements', 'low_stock'],
            default='stock',
            help='Tipo de reporte a generar'
        )
        parser.add_argument(
            '--output',
            default='reports',
            help='Directorio de salida'
        )

    def handle(self, *args, **options):
        output_dir = options['output']
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        report_type = options['type']
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        if report_type == 'stock':
            self.generate_stock_report(output_dir, timestamp)
        elif report_type == 'movements':
            self.generate_movements_report(output_dir, timestamp)
        elif report_type == 'low_stock':
            self.generate_low_stock_report(output_dir, timestamp)

    def generate_stock_report(self, output_dir, timestamp):
        filename = f'{output_dir}/stock_report_{timestamp}.csv'
        
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                'Código', 'Nombre', 'Categoría', 'Proveedor', 
                'Stock Actual', 'Stock Mínimo', 'Stock Máximo', 
                'Precio Unitario', 'Valor Total'
            ])
            
            products = Product.objects.select_related('category', 'supplier').filter(is_active=True)
            
            for product in products:
                writer.writerow([
                    product.code,
                    product.name,
                    product.category.name,
                    product.supplier.name,
                    product.current_stock,
                    product.minimum_stock,
                    product.maximum_stock,
                    product.unit_price,
                    product.current_stock * product.unit_price,
                ])
        
        self.stdout.write(f'Reporte de stock generado: {filename}')

    def generate_movements_report(self, output_dir, timestamp):
        filename = f'{output_dir}/movements_report_{timestamp}.csv'
        
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                'Fecha', 'Producto', 'Código', 'Tipo', 'Cantidad',
                'Stock Anterior', 'Nuevo Stock', 'Usuario', 'Referencia'
            ])
            
            movements = StockMovement.objects.select_related(
                'product', 'created_by'
            ).order_by('-created_at')[:1000]  # Últimos 1000 movimientos
            
            for movement in movements:
                writer.writerow([
                    movement.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    movement.product.name,
                    movement.product.code,
                    movement.get_movement_type_display(),
                    movement.quantity,
                    movement.previous_stock,
                    movement.new_stock,
                    movement.created_by.username,
                    movement.reference or '',
                ])
        
        self.stdout.write(f'Reporte de movimientos generado: {filename}')

    def generate_low_stock_report(self, output_dir, timestamp):
        filename = f'{output_dir}/low_stock_report_{timestamp}.csv'
        
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                'Código', 'Nombre', 'Categoría', 'Proveedor',
                'Stock Actual', 'Stock Mínimo', 'Diferencia'
            ])
            
            products = Product.objects.select_related('category', 'supplier').filter(
                is_active=True,
                current_stock__lte=models.F('minimum_stock')
            )
            
            for product in products:
                writer.writerow([
                    product.code,
                    product.name,
                    product.category.name,
                    product.supplier.name,
                    product.current_stock,
                    product.minimum_stock,
                    product.current_stock - product.minimum_stock
                ])