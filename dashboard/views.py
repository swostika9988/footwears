from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from django.contrib import messages
from products.models import Product, Category, ProductImage, ProductReview
from .forms import ProductForm, ProductImageForm, CategoryForm
from .forms import ProductForm, ProductImageForm

# dashboard/views.py
from django.shortcuts import render
from products.models import Category, Product

def dashboard_home(request):
    categories = Category.objects.all()
    products = Product.objects.all()

    # Pie chart data: Number of products per category
    category_names = [cat.category_name for cat in categories]
    products_per_category = [cat.products.count() for cat in categories]

    # Bar chart data: Example - total price sum per category (just for demo)
    total_price_per_category = [
        sum(prod.price for prod in cat.products.all()) for cat in categories
    ]

    # Line chart data: Number of reviews per product
    product_names = [prod.product_name for prod in products]
    product_reviews_count = [prod.reviews.count() for prod in products]

    context = {
        'category_names': category_names,
        'products_per_category': products_per_category,
        'total_price_per_category': total_price_per_category,
        'product_names': product_names,
        'product_reviews_count': product_reviews_count,
    }
    return render(request, 'dashboard/dashboard.html', context)

def home(request):
    categories = Category.objects.all()
    return render(request, 'home.html', {'categories': categories})


def categories(request):
    categories = Category.objects.all()
    # Checking for PK if needed
    for cat in categories:
        if not cat.pk:
            print("Category without PK found:", cat)
    return render(request, 'dashboard/categories.html', {'categories': categories})


def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            return redirect('categories')  # make sure 'categories' is the URL name for category list
    else:
        form = CategoryForm(instance=category)
    return render(request, 'dashboard/add_category.html', {'form': form})


def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    return redirect('categories')


def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('categories')
    else:
        form = CategoryForm()
    return render(request, 'dashboard/add_category.html', {'form': form})


def dashboard_reviews(request):
    reviews = ProductReview.objects.all()
    return render(request, 'dashboard/review_list.html', {'reviews': reviews})




class ProductListView(ListView):
    model = Product
    template_name = 'dashboard/product_list.html'
    context_object_name = 'products'
    queryset = Product.objects.all().select_related('category').prefetch_related('product_images')


def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')  # ensure this matches your URL name for product list
    else:
        form = ProductForm(instance=product)
    return render(request, 'dashboard/edit_product.html', {'form': form})


def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')  # again, make sure this matches your URL name
    return render(request, 'dashboard/delete_product_confirm.html', {'product': product})


def add_product_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        images_form = ProductImageForm(request.POST, request.FILES)

        if form.is_valid() and images_form.is_valid():
            product = form.save()

            # Save multiple images
            for image in request.FILES.getlist('image'):
                ProductImage.objects.create(product=product, image=image)

            messages.success(request, "Product added successfully!")
            return redirect('add_product')  # or 'product_list' if you have that
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()
        images_form = ProductImageForm()

    return render(request, 'dashboard/add_product.html', {
        'form': form,
        'images_form': images_form,
    })