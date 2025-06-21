from django import forms
from .models import ProductReview
from .models import Product

class ReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['stars', 'content']
        widgets = {
            "stars": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__' 