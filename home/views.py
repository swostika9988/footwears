from django.db.models import Q
from django.shortcuts import render
from products.models import Product, Category, Brand
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils.dateparse import parse_datetime
from django.db.models import Q, F, IntegerField, ExpressionWrapper
# Create your views here.
import json


def index(request):
    query = Product.objects.all()
    categories = Category.objects.all()
    selected_sort = request.GET.get('sort')
    selected_category = request.GET.get('category')

    if selected_category:
        query = query.filter(category__category_name=selected_category)

    if selected_sort:
        if selected_sort == 'newest':
            query = query.filter(newest_product=True).order_by('category_id')
        elif selected_sort == 'priceAsc':
            query = query.order_by('price')
        elif selected_sort == 'priceDesc':
            query = query.order_by('-price')

    page = request.GET.get('page', 1)
    paginator = Paginator(query, 20)
    trending_products = query.filter(is_trending=True).order_by('-created_at')[:10]
    # lets take 10 brands
    brands = Brand.objects.all()[:10]
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    except Exception as e:
        print(e)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'selected_sort': selected_sort,
        'trending_products': trending_products,
        'brands': brands,
    }
    return render(request, 'home/index.html', context)


# Custom filter method
def get_description_filter(desc):
    return Q(product_desription__icontains=desc)


def product_search(request):
    filter_query = request.GET.copy()
    filters = Q()
    get = request.GET

    def get_list_or_single(param):
        return get.getlist(param) if len(get.getlist(param)) > 1 else get.get(param)

    # Boolean Filters
    if 'is_trending' in get:
        filters &= Q(is_trending=get.get('is_trending').lower() == 'true')

    if 'newest_product' in get:
        filters &= Q(newest_product=get.get('newest_product').lower() == 'true')

    if 'is_men' in get:
        filters &= Q(is_men=get.get('is_men').lower() == 'true')

    if 'is_women' in get:
        filters &= Q(is_women=get.get('is_women').lower() == 'true')

    # Category filter (single or multiple)
    category_ids = get_list_or_single('category')
    if category_ids:
        if isinstance(category_ids, list):
            filters &= Q(category_id__in=category_ids)
        else:
            filters &= Q(category_id=category_ids)

    # Brand filter (single or multiple)
    brand_ids = get_list_or_single('brand')
    if brand_ids:
        if isinstance(brand_ids, list):
            filters &= Q(brand_id__in=brand_ids)
        else:
            filters &= Q(brand_id=brand_ids)

    # Price range
    if 'price_gte' in get:
        filters &= Q(price__gte=int(get.get('price_gte')))
    if 'price_lte' in get:
        filters &= Q(price__lte=int(get.get('price_lte')))

    # Product description match
    if 'product_description' in get:
        filters &= get_description_filter(get.get('product_description'))

    # Date filters
    if 'created_after' in get:
        filters &= Q(created_at__gte=parse_datetime(get.get('created_after')))
    if 'created_before' in get:
        filters &= Q(created_at__lte=parse_datetime(get.get('created_before')))

    # Base product queryset
    products = Product.objects.filter(filters).annotate(
        discount_percent_annotated=ExpressionWrapper(
            100 * (F('price') - F('discounted_price')) / F('price'),
            output_field=IntegerField()
        )
    )

    # Discount filter (e.g., discount_gte=40 means "at least 40% discount")
    # Discount filter: try to apply safely
    if 'discount_gte' in get:
        try:
            discount_value = int(get.get('discount_gte'))
            products = products.filter(discount_percent_annotated__gte=discount_value)
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    # lets get the brands
    brands = Brand.objects.all()
    # let get the categories
    categories = Category.objects.all()
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 20)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    except Exception as e:
        print(e)
    context = {
        'products': products,
        'brands': brands,
        'categories': categories,
        'filter_query': json.dumps(filter_query)
    }
    return render(request, 'product/filter.html', context)


def contact(request):
    context = {"form_id": "xgvvlrvn"}
    return render(request, 'home/contact.html', context)


def about(request):
    return render(request, 'home/about.html')


def terms_and_conditions(request):
    return render(request, 'home/terms_and_conditions.html')


def privacy_policy(request):
    return render(request, 'home/privacy_policy.html')
