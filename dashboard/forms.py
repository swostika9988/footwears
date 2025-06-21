from django import forms
from products.models import Product, ProductImage, Category

class MultiImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True  # Django 4.2+ supports this flag
    def __init__(self, attrs=None):
        final_attrs = {'multiple': True}
        if attrs:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs)

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'product_name',
            'slug',
            'category',
            'price',
            'product_desription',  # typo consistent with model
            'color_variant',
            'size_variant',
            'newest_product',
        ]
        widgets = {
            'product_desription': forms.Textarea(attrs={'rows': 3}),
            'color_variant': forms.CheckboxSelectMultiple(),
            'size_variant': forms.CheckboxSelectMultiple(),
        }

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
        widgets = {
            'image': MultiImageInput(),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['category_name', 'category_image']  # exclude slug since it's auto-generated
        widgets = {
            'category_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name',
            }),
            'category_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
        }