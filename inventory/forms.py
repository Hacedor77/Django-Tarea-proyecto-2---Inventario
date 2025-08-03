# forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Product, Supplier, Category, StockMovement
import csv
import io

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code', 'name', 'description', 'category', 'supplier', 
                 'unit_price', 'minimum_stock', 'maximum_stock', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'maximum_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        minimum_stock = cleaned_data.get('minimum_stock')
        maximum_stock = cleaned_data.get('maximum_stock')
        
        if minimum_stock and maximum_stock and minimum_stock >= maximum_stock:
            raise ValidationError('El stock mínimo debe ser menor al stock máximo.')
        
        return cleaned_data

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'unit_price', 'reference', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'movement_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        movement_type = cleaned_data.get('movement_type')
        quantity = cleaned_data.get('quantity')
        
        if product and movement_type == 'OUT' and quantity:
            # Obtener stock actual con consulta fresca
            try:
                current_product = Product.objects.get(pk=product.pk)
                stock_actual = current_product.current_stock
                
                if stock_actual < quantity:
                    raise ValidationError(
                        f'Stock insuficiente. Stock actual: {stock_actual}, '
                        f'Cantidad solicitada: {quantity}'
                    )
            except Product.DoesNotExist:
                raise ValidationError('Producto no válido.')
        
        return cleaned_data

class ProductFilterForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Todas las categorías",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        required=False,
        empty_label="Todos los proveedores",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    stock_status = forms.ChoiceField(
        choices=[
            ('', 'Todos los estados'),
            ('low', 'Stock bajo'),
            ('out', 'Sin stock'),
            ('normal', 'Stock normal'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por código o nombre...'
        })
    )

class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label="Archivo CSV",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        })
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        
        if not file.name.endswith('.csv'):
            raise ValidationError('El archivo debe ser un CSV.')
        
        # Validar que el archivo tenga el formato correcto
        file.seek(0)
        content = file.read().decode('utf-8')
        file.seek(0)
        
        csv_reader = csv.DictReader(io.StringIO(content))
        required_fields = ['code', 'name', 'category', 'supplier', 'unit_price']
        
        try:
            headers = csv_reader.fieldnames
            if not headers:
                raise ValidationError('El archivo CSV está vacío o no tiene encabezados.')
            
            missing_fields = [field for field in required_fields if field not in headers]
            if missing_fields:
                raise ValidationError(
                    f'Faltan los siguientes campos requeridos: {", ".join(missing_fields)}'
                )
                
        except Exception as e:
            raise ValidationError(f'Error al leer el archivo CSV: {str(e)}')
        
        return file

class MovementFilterForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        required=False,
        empty_label="Todos los productos",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    movement_type = forms.ChoiceField(
        choices=[('', 'Todos los tipos')] + StockMovement.MOVEMENT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
