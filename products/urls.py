from django.urls import path
from products.views import *
from products.api_views import (
    get_content_based_recommendations, get_user_preferences, get_similar_users,
    record_user_behavior, get_product_features, get_recommendation_explanation,
    get_content_filtering_stats, get_collaborative_recommendations, 
    get_collaborative_similar_users, get_collaborative_similar_products,
    get_collaborative_filtering_stats, get_product_sentiment, get_sentiment_insights,
    get_top_sentiment_products, get_aspect_insights, get_sentiment_stats
)

urlpatterns = [
    path('brand/<brand_id>/', brand_products, name='brand_products'),
    path('wishlist/', wishlist_view, name='wishlist'),
    path('wishlist/add/<uid>/', add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/move_to_cart/<uid>/', move_to_cart, name='move_to_cart'),
    path('wishlist/remove/<uid>/', remove_from_wishlist, name='remove_from_wishlist'),
    path('product-reviews/', product_reviews, name='product_reviews'),
    path('product-reviews/edit/<uuid:review_uid>/', edit_review, name='edit_review'),
    path('like-review/<review_uid>/', like_review, name='like_review'),
    path('dislike-review/<review_uid>/',dislike_review, name='dislike_review'),
    path('<slug>/', get_product, name='get_product'),
    path('<slug>/<review_uid>/delete/', delete_review, name='delete_review'),
    
    # API endpoints for content-based filtering
    path('api/recommendations/content-based/', get_content_based_recommendations, name='api_content_recommendations'),
    path('api/preferences/', get_user_preferences, name='api_user_preferences'),
    path('api/similar-users/', get_similar_users, name='api_similar_users'),
    path('api/record-behavior/', record_user_behavior, name='api_record_behavior'),
    path('api/product-features/<uuid:product_id>/', get_product_features, name='api_product_features'),
    path('api/recommendation-explanation/<uuid:product_id>/', get_recommendation_explanation, name='api_recommendation_explanation'),
    path('api/content-filtering-stats/', get_content_filtering_stats, name='api_content_filtering_stats'),
    
    # API endpoints for collaborative filtering
    path('api/recommendations/collaborative/', get_collaborative_recommendations, name='api_collaborative_recommendations'),
    path('api/collaborative/similar-users/', get_collaborative_similar_users, name='api_collaborative_similar_users'),
    path('api/collaborative/similar-products/<uuid:product_id>/', get_collaborative_similar_products, name='api_collaborative_similar_products'),
    path('api/collaborative/stats/', get_collaborative_filtering_stats, name='api_collaborative_filtering_stats'),
    
    # API endpoints for sentiment analysis
    path('api/sentiment/product/<uuid:product_id>/', get_product_sentiment, name='api_product_sentiment'),
    path('api/sentiment/insights/<uuid:product_id>/', get_sentiment_insights, name='api_sentiment_insights'),
    path('api/sentiment/top-products/', get_top_sentiment_products, name='api_top_sentiment_products'),
    path('api/sentiment/aspect-insights/', get_aspect_insights, name='api_aspect_insights'),
    path('api/sentiment/stats/', get_sentiment_stats, name='api_sentiment_stats'),
]
