# management/commands/check_low_stock.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from inventory.inventory import models
from inventory.models import Product, LowStockAlert

class Command(BaseCommand):
    help = 'Revisa productos con stock bajo y crea alertas'

    def handle(self, *args, **options):
        low_stock_products = Product.objects.filter(
            is_active=True,
            current_stock__lte=models.F('minimum_stock')
        )
        
        alerts_created = 0
        for product in low_stock_products:
            alert, created = LowStockAlert.objects.get_or_create(
                product=product,
                is_resolved=False,
                defaults={
                    'current_stock': product.current_stock,
                    'minimum_stock': product.minimum_stock
                }
            )
            
            if created:
                alerts_created += 1
                
                # Enviar email si está configurado
                if getattr(settings, 'STOCK_ALERT_EMAIL', None):
                    send_mail(
                        f'⚠️ Stock bajo: {product.name}',
                        f'El producto {product.name} ({product.code}) tiene stock bajo.\n'
                        f'Stock actual: {product.current_stock}\n'
                        f'Stock mínimo: {product.minimum_stock}',
                        settings.DEFAULT_FROM_EMAIL,
                        [settings.STOCK_ALERT_EMAIL],
                        fail_silently=True,
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Revisión completada. Alertas creadas: {alerts_created}')
        )
