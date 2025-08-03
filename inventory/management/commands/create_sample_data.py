# management/commands/create_sample_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Category, Supplier, Product, StockMovement
import random
from decimal import Decimal

class Command(BaseCommand):
    help = 'Crea datos de ejemplo para el sistema de inventario'

    def add_arguments(self, parser):
        parser.add_argument(
            '--products',
            type=int,
            default=50,
            help='Número de productos a crear'
        )

    def handle(self, *args, **options):
        self.stdout.write('Creando datos de ejemplo...')
        
        # Crear usuario admin si no existe
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            
        # Crear categorías
        categories = ['Electrónicos', 'Ropa', 'Hogar', 'Deportes', 'Libros', 'Salud']
        for cat_name in categories:
            Category.objects.get_or_create(name=cat_name)
        
        # Crear proveedores
        suppliers_data = [
            {'name': 'Tech Solutions', 'email': 'contact@techsolutions.com'},
            {'name': 'Fashion World', 'email': 'info@fashionworld.com'},
            {'name': 'Home & Garden', 'email': 'sales@homeandgarden.com'},
            {'name': 'Sports Pro', 'email': 'orders@sportspro.com'},
        ]
        
        for supplier_data in suppliers_data:
            Supplier.objects.get_or_create(
                name=supplier_data['name'],
                defaults={'email': supplier_data['email']}
            )
        
        # Crear productos
        categories_qs = Category.objects.all()
        suppliers_qs = Supplier.objects.all()
        user = User.objects.get(username='admin')
        
        for i in range(options['products']):
            product_name = f'Producto {i+1:03d}'
            code = f'PRD{i+1:04d}'
            
            if not Product.objects.filter(code=code).exists():
                product = Product.objects.create(
                    code=code,
                    name=product_name,
                    description=f'Descripción del {product_name}',
                    category=random.choice(categories_qs),
                    supplier=random.choice(suppliers_qs),
                    unit_price=Decimal(str(round(random.uniform(10, 1000), 2))),
                    current_stock=random.randint(0, 100),
                    minimum_stock=random.randint(5, 20),
                    maximum_stock=random.randint(100, 500),
                )
                
                # Crear algunos movimientos aleatorios
                for _ in range(random.randint(1, 5)):
                    movement_type = random.choice(['IN', 'OUT'])
                    quantity = random.randint(1, 20)
                    
                    if movement_type == 'OUT' and product.current_stock < quantity:
                        continue  # Evitar stock negativo
                    
                    StockMovement.objects.create(
                        product=product,
                        movement_type=movement_type,
                        quantity=quantity,
                        unit_price=product.unit_price,
                        reference=f'REF-{random.randint(1000, 9999)}',
                        created_by=user,
                        previous_stock=product.current_stock,
                        new_stock=product.current_stock + (quantity if movement_type == 'IN' else -quantity)
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Datos de ejemplo creados exitosamente: {options["products"]} productos'
            )
        )