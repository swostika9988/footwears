import random
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .forms import ReviewForm
from products.models import Product, SizeVariant, ProductReview, Wishlist, Brand, UserBehavior
from accounts.models import Cart, CartItem
from .recommendation_engine import RecommendationService
from .feature_extractor import ProductFeatureExtractor
from .preference_learner import PreferenceService as UserPreferenceService
from .sentiment_analyzer import SentimentService


def get_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    sorted_size_variants = product.size_variant.all().order_by('size_name')
    
    # Record user behavior for recommendation learning
    if request.user.is_authenticated:
        # Record product view
        recommendation_service = RecommendationService()
        recommendation_service.record_user_behavior(
            user=request.user,
            product=product,
            behavior_type='view',
            weight=1.0
        )
        
        # Update user preferences
        preference_service = UserPreferenceService()
        preference_service.update_user_preferences(request.user)
    
    # Get related products using recommendation system
    recommendation_service = RecommendationService()
    related_products = recommendation_service.get_recommendations_for_product(product, limit=4)
    
    # Fallback to category-based products if no recommendations
    if not related_products:
        related_products = list(product.category.products.filter(parent=None).exclude(uid=product.uid))
        if len(related_products) >= 4:
            related_products = random.sample(related_products, 4)
    
    # Get sentiment analysis for the product
    sentiment_service = SentimentService()
    sentiment_insights = sentiment_service.get_sentiment_insights(product)
    
    # Get AI-powered similar products (collaborative filtering)
    ai_similar_products = recommendation_service.engine.get_collaborative_filtering_recommendations(
        user=request.user if request.user.is_authenticated else None,
        method='item_based',
        limit=4
    )

    review = None
    if request.user.is_authenticated:
        review = ProductReview.objects.filter(product=product, user=request.user).first()

    rating_percentage = 0
    if product.reviews.exists():
        rating_percentage = (product.get_rating() / 5) * 100

    if request.method == 'POST' and request.user.is_authenticated:
        review_form = ReviewForm(request.POST, instance=review) if review else ReviewForm(request.POST)
        if review_form.is_valid():
            review_instance = review_form.save(commit=False)
            review_instance.product = product
            review_instance.user = request.user
            review_instance.save()
            
            # Record review behavior
            recommendation_service.record_user_behavior(
                user=request.user,
                product=product,
                behavior_type='review',
                weight=2.0
            )
            
            messages.success(request, "Review added successfully!")
            return redirect('get_product', slug=slug)
    else:
        review_form = ReviewForm(instance=review) if review else ReviewForm()

    in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists() if request.user.is_authenticated else False

    context = {
        'product': product,
        'sorted_size_variants': sorted_size_variants,
        'related_products': related_products,
        'ai_similar_products': ai_similar_products,
        'sentiment_insights': sentiment_insights,
        'review_form': review_form,
        'rating_percentage': rating_percentage,
        'in_wishlist': in_wishlist,
    }

    if request.GET.get('size'):
        size = request.GET.get('size')
        price = product.get_product_price_by_size(size)
        context['selected_size'] = size
        context['updated_price'] = price

    return render(request, 'product/product.html', context=context)


@login_required
def product_reviews(request):
    reviews = ProductReview.objects.filter(user=request.user).select_related('product').order_by('-date_added')
    return render(request, 'product/all_product_reviews.html', {'reviews': reviews})


@login_required
def edit_review(request, review_uid):
    review = get_object_or_404(ProductReview, uid=review_uid, user=request.user)
    if request.method == "POST":
        review.stars = request.POST.get("stars")
        review.content = request.POST.get("content")
        review.save()
        messages.success(request, "Your review has been updated successfully.")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    return JsonResponse({"detail": "Invalid request"}, status=400)


def like_review(request, review_uid):
    review = get_object_or_404(ProductReview, uid=review_uid)
    if request.user in review.likes.all():
        review.likes.remove(request.user)
    else:
        review.likes.add(request.user)
        review.dislikes.remove(request.user)
    return JsonResponse({'likes': review.like_count(), 'dislikes': review.dislike_count()})


def dislike_review(request, review_uid):
    review = get_object_or_404(ProductReview, uid=review_uid)
    if request.user in review.dislikes.all():
        review.dislikes.remove(request.user)
    else:
        review.dislikes.add(request.user)
        review.likes.remove(request.user)
    return JsonResponse({'likes': review.like_count(), 'dislikes': review.dislike_count()})


@login_required
def delete_review(request, slug, review_uid):
    review = get_object_or_404(ProductReview, uid=review_uid, product__slug=slug, user=request.user)
    review.delete()
    messages.success(request, "Your review has been deleted.")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required
def add_to_wishlist(request, uid):
    size_name = request.GET.get('size')
    if not size_name:
        messages.warning(request, 'Please select a size variant before adding to the wishlist!')
        return redirect(request.META.get('HTTP_REFERER'))

    product = get_object_or_404(Product, uid=uid)
    size_variant = get_object_or_404(SizeVariant, size_name=size_name)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user, product=product, size_variant=size_variant)

    if created:
        messages.success(request, "Product added to Wishlist!")

    return redirect(reverse('wishlist'))


@login_required
def remove_from_wishlist(request, uid):
    product = get_object_or_404(Product, uid=uid)
    size_variant_name = request.GET.get('size')

    if size_variant_name:
        size_variant = get_object_or_404(SizeVariant, size_name=size_variant_name)
        Wishlist.objects.filter(user=request.user, product=product, size_variant=size_variant).delete()
    else:
        Wishlist.objects.filter(user=request.user, product=product).delete()

    messages.success(request, "Product removed from wishlist!")
    return redirect(reverse('wishlist'))


@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'product/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
def move_to_cart(request, uid):
    product = get_object_or_404(Product, uid=uid)
    wishlist = get_object_or_404(Wishlist, user=request.user, product=product)
    size_variant = wishlist.size_variant
    wishlist.delete()

    cart, _ = Cart.objects.get_or_create(user=request.user, is_paid=False)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, size_variant=size_variant)

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, "Product moved to cart successfully!")
    return redirect('cart')


def index(request):
    products = Product.objects.all()
    trending_products = Product.objects.filter(is_trending=True)[:8]
    featured_products = Product.objects.filter(newest_product=True)[:8]

    return render(request, 'index.html', {
        'products': products,
        'trending_products': trending_products,
        'featured_products': featured_products,
    })

# 👇 Add your brand_products view here:
def brand_products(request, brand_id):
    brand = get_object_or_404(Brand, uid=brand_id)
    products = Product.objects.filter(brand=brand)
    return render(request, 'product/brand_products.html', {
        'brand': brand,
        'products': products,
    })

