"""
API Views for Content-Based Recommendations
Provides REST API endpoints for recommendation system
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from .models import Product, UserPreference, UserBehavior
from .feature_extractor import ContentBasedRecommender
from .preference_learner import PreferenceService
from .collaborative_filtering import CollaborativeFilteringService
from .matrix_factorization import MatrixFactorizationService
from .sentiment_analyzer import SentimentService
import json


@login_required
@require_http_methods(["GET"])
def get_content_based_recommendations(request):
    """
    Get content-based recommendations for the authenticated user
    """
    try:
        limit = int(request.GET.get('limit', 10))
        user = request.user
        
        # Get recommendations
        recommender = ContentBasedRecommender()
        recommendations = recommender.get_content_based_recommendations(user, limit)
        
        # Format response
        products_data = []
        for product in recommendations:
            products_data.append({
                'id': str(product.uid),
                'name': product.product_name,
                'price': product.price,
                'discounted_price': float(product.discounted_price) if product.discounted_price else None,
                'category': product.category.category_name,
                'brand': product.brand.name if product.brand else None,
                'image_url': product.product_images.first().image.url if product.product_images.exists() else None,
                'rating': product.get_rating(),
                'review_count': product.reviews.count(),
                'is_trending': product.is_trending,
                'is_newest': product.newest_product,
                'slug': product.slug
            })
        
        return JsonResponse({
            'success': True,
            'recommendations': products_data,
            'count': len(products_data),
            'user_id': user.id,
            'username': user.username
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_user_preferences(request):
    """
    Get user preference summary
    """
    try:
        user = request.user
        preference_service = PreferenceService()
        preferences = preference_service.get_user_preferences(user)
        
        if preferences:
            return JsonResponse({
                'success': True,
                'preferences': preferences
            })
        else:
            return JsonResponse({
                'success': True,
                'preferences': {
                    'total_preferences': 0,
                    'categories': [],
                    'brands': [],
                    'price_range': None,
                    'confidence_score': 0.0
                }
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_similar_users(request):
    """
    Get users with similar preferences
    """
    try:
        limit = int(request.GET.get('limit', 5))
        user = request.user
        
        preference_service = PreferenceService()
        similar_users = preference_service.get_similar_users(user, limit)
        
        # Format response
        users_data = []
        for similar_user, similarity_score in similar_users:
            users_data.append({
                'id': similar_user.id,
                'username': similar_user.username,
                'similarity_score': similarity_score,
                'first_name': similar_user.first_name,
                'last_name': similar_user.last_name
            })
        
        return JsonResponse({
            'success': True,
            'similar_users': users_data,
            'count': len(users_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def record_user_behavior(request):
    """
    Record user behavior for preference learning
    """
    try:
        data = json.loads(request.body)
        user = request.user
        
        product_id = data.get('product_id')
        behavior_type = data.get('behavior_type')
        target = data.get('target')  # For category/brand views
        weight = data.get('weight', 1.0)
        
        if not behavior_type:
            return JsonResponse({
                'success': False,
                'error': 'behavior_type is required'
            }, status=400)
        
        # Handle different behavior types
        if behavior_type in ['view', 'cart_add', 'purchase', 'wishlist', 'review']:
            if not product_id:
                return JsonResponse({
                    'success': False,
                    'error': 'product_id required for this behavior type'
                }, status=400)
            
            # Get product
            product = get_object_or_404(Product, uid=product_id)
            
            # Record behavior
            from .recommendation_engine import RecommendationService
            recommendation_service = RecommendationService()
            recommendation_service.record_user_behavior(
                user=user,
                product=product,
                behavior_type=behavior_type,
                weight=weight
            )
        
        elif behavior_type in ['category_view', 'brand_view']:
            # For category/brand views, we might store this differently
            # For now, just log it
            print(f"User {user.username} viewed {behavior_type}: {target}")
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid behavior_type'
            }, status=400)
        
        # Update preferences
        preference_service = PreferenceService()
        preference_service.update_user_preferences(user)
        
        return JsonResponse({
            'success': True,
            'message': 'Behavior recorded successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_product_features(request, product_id):
    """
    Get product features for analysis
    """
    try:
        product = get_object_or_404(Product, uid=product_id)
        
        # Get product features
        features = product.features.all()
        features_data = {}
        
        for feature in features:
            features_data[feature.feature_name] = feature.feature_value
        
        return JsonResponse({
            'success': True,
            'product_id': str(product.uid),
            'product_name': product.product_name,
            'features': features_data,
            'feature_count': len(features_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_recommendation_explanation(request, product_id):
    """
    Get explanation for why a product was recommended
    """
    try:
        user = request.user
        product = get_object_or_404(Product, uid=product_id)
        
        # Get user preferences
        preference_service = PreferenceService()
        user_preferences = preference_service.get_user_preferences(user)
        
        # Get product features
        from .feature_extractor import FeatureVectorBuilder
        vector_builder = FeatureVectorBuilder()
        product_features = vector_builder.build_product_feature_vector(product)
        user_preference_vector = vector_builder.build_user_preference_vector(user)
        
        # Find matching preferences
        explanations = []
        
        if user_preferences and user_preferences.get('categories'):
            for category_pref in user_preferences['categories']:
                if category_pref['name'] == product.category.category_name:
                    explanations.append({
                        'type': 'category_match',
                        'description': f"You prefer {category_pref['name']} products",
                        'confidence': category_pref['weight']
                    })
        
        if user_preferences and user_preferences.get('brands'):
            for brand_pref in user_preferences['brands']:
                if product.brand and brand_pref['name'] == product.brand.name:
                    explanations.append({
                        'type': 'brand_match',
                        'description': f"You prefer {brand_pref['name']} brand",
                        'confidence': brand_pref['weight']
                    })
        
        if user_preferences and user_preferences.get('price_range'):
            price_range = user_preferences['price_range']
            if price_range['min'] <= product.price <= price_range['max']:
                explanations.append({
                    'type': 'price_match',
                    'description': f"Price fits your preferred range (Rs. {price_range['min']} - Rs. {price_range['max']})",
                    'confidence': 0.8
                })
        
        return JsonResponse({
            'success': True,
            'product_id': str(product.uid),
            'product_name': product.product_name,
            'explanations': explanations,
            'explanation_count': len(explanations)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_content_filtering_stats(request):
    """
    Get statistics about content-based filtering system
    """
    try:
        # Get system statistics
        total_products = Product.objects.count()
        products_with_features = Product.objects.filter(features__isnull=False).distinct().count()
        total_users = User.objects.count()
        users_with_preferences = User.objects.filter(preferences__isnull=False).distinct().count()
        total_behaviors = UserBehavior.objects.count()
        
        # Get feature statistics
        from .models import ProductFeature
        total_features = ProductFeature.objects.count()
        unique_feature_types = ProductFeature.objects.values('feature_name').distinct().count()
        
        stats = {
            'products': {
                'total': total_products,
                'with_features': products_with_features,
                'feature_coverage': round(products_with_features / total_products * 100, 2) if total_products > 0 else 0
            },
            'users': {
                'total': total_users,
                'with_preferences': users_with_preferences,
                'preference_coverage': round(users_with_preferences / total_users * 100, 2) if total_users > 0 else 0
            },
            'behaviors': {
                'total': total_behaviors
            },
            'features': {
                'total': total_features,
                'unique_types': unique_feature_types
            }
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_collaborative_recommendations(request):
    """
    Get collaborative filtering recommendations for the authenticated user
    """
    try:
        limit = int(request.GET.get('limit', 10))
        method = request.GET.get('method', 'hybrid')
        user = request.user
        
        # Get recommendations based on method
        if method in ['user_based', 'item_based', 'hybrid']:
            collaborative_service = CollaborativeFilteringService()
            recommendations = collaborative_service.get_collaborative_recommendations(user, method, limit)
        elif method in ['mf', 'svd', 'nmf', 'mf_hybrid']:
            mf_service = MatrixFactorizationService()
            if method == 'mf_hybrid':
                recommendations = mf_service.get_hybrid_recommendations(user, limit)
            else:
                recommendations = mf_service.get_recommendations(user, method, limit)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid method specified'
            }, status=400)
        
        # Format response
        products_data = []
        for product in recommendations:
            products_data.append({
                'id': str(product.uid),
                'name': product.product_name,
                'price': product.price,
                'discounted_price': float(product.discounted_price) if product.discounted_price else None,
                'category': product.category.category_name,
                'brand': product.brand.name if product.brand else None,
                'image_url': product.product_images.first().image.url if product.product_images.exists() else None,
                'rating': product.get_rating(),
                'review_count': product.reviews.count(),
                'is_trending': product.is_trending,
                'is_newest': product.newest_product,
                'slug': product.slug
            })
        
        return JsonResponse({
            'success': True,
            'recommendations': products_data,
            'count': len(products_data),
            'method': method,
            'user_id': user.id,
            'username': user.username
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_collaborative_similar_users(request):
    """
    Get users similar to the authenticated user
    """
    try:
        limit = int(request.GET.get('limit', 5))
        user = request.user
        
        collaborative_service = CollaborativeFilteringService()
        similar_users = collaborative_service.get_similar_users(user, limit)
        
        # Format response
        users_data = []
        for similar_user, similarity_score in similar_users:
            users_data.append({
                'id': similar_user.id,
                'username': similar_user.username,
                'similarity_score': similarity_score,
                'first_name': similar_user.first_name,
                'last_name': similar_user.last_name
            })
        
        return JsonResponse({
            'success': True,
            'similar_users': users_data,
            'count': len(users_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_collaborative_similar_products(request, product_id):
    """
    Get products similar to the specified product
    """
    try:
        limit = int(request.GET.get('limit', 5))
        product = get_object_or_404(Product, uid=product_id)
        
        collaborative_service = CollaborativeFilteringService()
        similar_products = collaborative_service.get_similar_products(product, limit)
        
        # Format response
        products_data = []
        for similar_product, similarity_score in similar_products:
            products_data.append({
                'id': str(similar_product.uid),
                'name': similar_product.product_name,
                'price': similar_product.price,
                'discounted_price': float(similar_product.discounted_price) if similar_product.discounted_price else None,
                'category': similar_product.category.category_name,
                'brand': similar_product.brand.name if similar_product.brand else None,
                'image_url': similar_product.product_images.first().image.url if similar_product.product_images.exists() else None,
                'rating': similar_product.get_rating(),
                'review_count': similar_product.reviews.count(),
                'similarity_score': similarity_score,
                'slug': similar_product.slug
            })
        
        return JsonResponse({
            'success': True,
            'similar_products': products_data,
            'count': len(products_data),
            'product_id': str(product.uid),
            'product_name': product.product_name
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_collaborative_filtering_stats(request):
    """
    Get statistics about collaborative filtering system
    """
    try:
        # Get system statistics
        total_users = User.objects.count()
        users_with_behaviors = User.objects.filter(behaviors__isnull=False).distinct().count()
        total_products = Product.objects.count()
        products_with_behaviors = Product.objects.filter(user_behaviors__isnull=False).distinct().count()
        total_behaviors = UserBehavior.objects.count()
        
        # Get behavior statistics
        behavior_counts = UserBehavior.objects.values('behavior_type').annotate(
            count=Count('uid')
        )
        
        # Get similarity statistics
        from .models import UserSimilarity, ProductSimilarity
        user_similarities = UserSimilarity.objects.count()
        product_similarities = ProductSimilarity.objects.count()
        
        stats = {
            'users': {
                'total': total_users,
                'with_behaviors': users_with_behaviors,
                'behavior_coverage': round(users_with_behaviors / total_users * 100, 2) if total_users > 0 else 0
            },
            'products': {
                'total': total_products,
                'with_behaviors': products_with_behaviors,
                'behavior_coverage': round(products_with_behaviors / total_products * 100, 2) if total_products > 0 else 0
            },
            'behaviors': {
                'total': total_behaviors,
                'by_type': {item['behavior_type']: item['count'] for item in behavior_counts}
            },
            'similarities': {
                'user_similarities': user_similarities,
                'product_similarities': product_similarities
            }
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_product_sentiment(request, product_id):
    """
    Get sentiment analysis for a specific product
    """
    try:
        product = get_object_or_404(Product, uid=product_id)
        
        sentiment_service = SentimentService()
        sentiment_data = sentiment_service.get_product_sentiment(product)
        
        if sentiment_data:
            return JsonResponse({
                'success': True,
                'product_id': str(product.uid),
                'product_name': product.product_name,
                'sentiment_data': sentiment_data
            })
        else:
            return JsonResponse({
                'success': True,
                'product_id': str(product.uid),
                'product_name': product.product_name,
                'sentiment_data': None,
                'message': 'No sentiment analysis available'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_sentiment_insights(request, product_id):
    """
    Get comprehensive sentiment insights for a product
    """
    try:
        product = get_object_or_404(Product, uid=product_id)
        
        sentiment_service = SentimentService()
        insights = sentiment_service.get_sentiment_insights(product)
        
        if insights:
            return JsonResponse({
                'success': True,
                'product_id': str(product.uid),
                'product_name': product.product_name,
                'insights': insights
            })
        else:
            return JsonResponse({
                'success': True,
                'product_id': str(product.uid),
                'product_name': product.product_name,
                'insights': None,
                'message': 'No sentiment insights available'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_top_sentiment_products(request):
    """
    Get products with highest sentiment scores
    """
    try:
        sentiment_type = request.GET.get('type', 'positive')
        limit = int(request.GET.get('limit', 10))
        
        sentiment_service = SentimentService()
        products = sentiment_service.get_top_sentiment_products(sentiment_type, limit)
        
        # Format response
        products_data = []
        for product in products:
            sentiment_data = sentiment_service.get_product_sentiment(product)
            products_data.append({
                'id': str(product.uid),
                'name': product.product_name,
                'price': product.price,
                'discounted_price': float(product.discounted_price) if product.discounted_price else None,
                'category': product.category.category_name,
                'brand': product.brand.name if product.brand else None,
                'image_url': product.product_images.first().image.url if product.product_images.exists() else None,
                'rating': product.get_rating(),
                'review_count': product.reviews.count(),
                'sentiment_score': sentiment_data['sentiment_score'] if sentiment_data else 0.0,
                'overall_sentiment': sentiment_data['overall_sentiment'] if sentiment_data else 'neutral',
                'slug': product.slug
            })
        
        return JsonResponse({
            'success': True,
            'sentiment_type': sentiment_type,
            'products': products_data,
            'count': len(products_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_aspect_insights(request):
    """
    Get insights for a specific aspect across all products
    """
    try:
        aspect = request.GET.get('aspect', 'comfort')
        limit = int(request.GET.get('limit', 10))
        
        sentiment_service = SentimentService()
        insights = sentiment_service.get_aspect_insights(aspect, limit)
        
        # Format response
        insights_data = []
        for insight in insights:
            product = insight['product']
            insights_data.append({
                'product_id': str(product.uid),
                'product_name': product.product_name,
                'category': product.category.category_name,
                'brand': product.brand.name if product.brand else None,
                'image_url': product.product_images.first().image.url if product.product_images.exists() else None,
                'sentiment_score': insight['sentiment_score'],
                'positive_mentions': insight['positive_mentions'],
                'negative_mentions': insight['negative_mentions'],
                'total_mentions': insight['total_mentions'],
                'confidence': insight['confidence']
            })
        
        return JsonResponse({
            'success': True,
            'aspect': aspect,
            'insights': insights_data,
            'count': len(insights_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_sentiment_stats(request):
    """
    Get statistics about sentiment analysis system
    """
    try:
        from .models import SentimentAnalysis, AspectSentiment, SentimentTrend
        
        # Get system statistics
        total_products = Product.objects.count()
        products_with_sentiment = SentimentAnalysis.objects.count()
        total_aspect_analyses = AspectSentiment.objects.count()
        total_trend_analyses = SentimentTrend.objects.count()
        
        # Get sentiment distribution
        sentiment_distribution = SentimentAnalysis.objects.values('overall_sentiment').annotate(
            count=Count('uid')
        )
        
        # Get aspect distribution
        aspect_distribution = AspectSentiment.objects.values('aspect').annotate(
            total_mentions=Sum('total_mentions'),
            avg_sentiment=Avg('sentiment_score')
        )
        
        stats = {
            'products': {
                'total': total_products,
                'with_sentiment': products_with_sentiment,
                'sentiment_coverage': round(products_with_sentiment / total_products * 100, 2) if total_products > 0 else 0
            },
            'analyses': {
                'sentiment_analyses': products_with_sentiment,
                'aspect_analyses': total_aspect_analyses,
                'trend_analyses': total_trend_analyses
            },
            'sentiment_distribution': {
                item['overall_sentiment']: item['count'] for item in sentiment_distribution
            },
            'aspect_distribution': [
                {
                    'aspect': item['aspect'],
                    'total_mentions': item['total_mentions'],
                    'avg_sentiment': round(item['avg_sentiment'], 3) if item['avg_sentiment'] else 0
                }
                for item in aspect_distribution
            ]
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)