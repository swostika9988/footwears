"""
Recommendation Engine for Footwear E-commerce
Handles content-based filtering, collaborative filtering, and hybrid recommendations
"""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from django.db.models import Q, Avg, Count
from django.contrib.auth.models import User
from .models import (
    Product, UserPreference, ProductFeature, UserBehavior, 
    UserSimilarity, ProductSimilarity, UserRating, ProductReview
)
from .feature_extractor import ContentBasedRecommender
from .preference_learner import PreferenceService
from .collaborative_filtering import CollaborativeFilteringService
from .matrix_factorization import MatrixFactorizationService


class RecommendationEngine:
    """Main recommendation engine class"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.content_recommender = ContentBasedRecommender()
        self.preference_service = PreferenceService()
        self.collaborative_service = CollaborativeFilteringService()
        self.matrix_factorization_service = MatrixFactorizationService()
        
    def get_content_based_recommendations(self, user, limit=10):
        """
        Get enhanced content-based recommendations based on user preferences
        """
        try:
            # Update user preferences first
            self.preference_service.update_user_preferences(user)
            
            # Use the enhanced content-based recommender
            return self.content_recommender.get_content_based_recommendations(user, limit)
            
        except Exception as e:
            print(f"Error in content-based recommendations: {e}")
            return self._get_trending_products(limit)
    
    def get_collaborative_filtering_recommendations(self, user, method='hybrid', limit=10):
        """
        Get collaborative filtering recommendations
        """
        try:
            if method == 'user_based':
                return self.collaborative_service.get_collaborative_recommendations(user, 'user_based', limit)
            elif method == 'item_based':
                return self.collaborative_service.get_collaborative_recommendations(user, 'item_based', limit)
            elif method == 'hybrid':
                return self.collaborative_service.get_collaborative_recommendations(user, 'hybrid', limit)
            elif method == 'matrix_factorization':
                return self.matrix_factorization_service.get_recommendations(user, 'mf', limit)
            elif method == 'svd':
                return self.matrix_factorization_service.get_recommendations(user, 'svd', limit)
            elif method == 'nmf':
                return self.matrix_factorization_service.get_recommendations(user, 'nmf', limit)
            elif method == 'mf_hybrid':
                return self.matrix_factorization_service.get_hybrid_recommendations(user, limit)
            else:
                return self.collaborative_service.get_collaborative_recommendations(user, 'hybrid', limit)
                
        except Exception as e:
            print(f"Error in collaborative filtering recommendations: {e}")
            return self._get_trending_products(limit)
    
    def get_hybrid_recommendations(self, user, limit=10):
        """
        Get hybrid recommendations combining content-based and collaborative filtering
        """
        try:
            # Get both types of recommendations
            content_recs = self.get_content_based_recommendations(user, limit=limit*2)
            collab_recs = self.get_collaborative_filtering_recommendations(user, limit=limit*2)
            
            # Combine and score
            product_scores = {}
            
            # Score content-based recommendations
            for i, product in enumerate(content_recs):
                if product.uid not in product_scores:
                    product_scores[product.uid] = 0
                product_scores[product.uid] += (len(content_recs) - i) * 0.6  # Content weight
            
            # Score collaborative recommendations
            for i, product in enumerate(collab_recs):
                if product.uid not in product_scores:
                    product_scores[product.uid] = 0
                product_scores[product.uid] += (len(collab_recs) - i) * 0.4  # Collaborative weight
            
            # Sort by combined score
            sorted_products = sorted(product_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Get product objects
            recommended_products = []
            for product_uid, score in sorted_products[:limit]:
                try:
                    product = Product.objects.get(uid=product_uid)
                    recommended_products.append(product)
                except Product.DoesNotExist:
                    continue
            
            return recommended_products
            
        except Exception as e:
            print(f"Error in hybrid recommendations: {e}")
            return self._get_trending_products(limit)
    
    def get_similar_products(self, product, limit=5):
        """
        Get products similar to a given product
        """
        try:
            # Get product similarities
            similarities = ProductSimilarity.objects.filter(
                Q(product1=product) | Q(product2=product)
            ).order_by('-similarity_score')[:limit*2]
            
            similar_products = []
            for similarity in similarities:
                if similarity.product1 == product:
                    similar_product = similarity.product2
                else:
                    similar_product = similarity.product1
                
                if similar_product not in similar_products:
                    similar_products.append(similar_product)
                
                if len(similar_products) >= limit:
                    break
            
            return similar_products
            
        except Exception as e:
            print(f"Error getting similar products: {e}")
            return self._get_products_by_category(product.category, limit)
    
    def _get_similar_users(self, user, limit=5):
        """
        Get users similar to the given user
        """
        try:
            similarities = UserSimilarity.objects.filter(
                Q(user1=user) | Q(user2=user)
            ).order_by('-similarity_score')[:limit]
            
            similar_users = []
            for similarity in similarities:
                if similarity.user1 == user:
                    similar_user = similarity.user2
                else:
                    similar_user = similarity.user1
                
                similar_users.append((similar_user, similarity.similarity_score))
            
            return similar_users
            
        except Exception as e:
            print(f"Error getting similar users: {e}")
            return []
    
    def _user_has_product(self, user, product):
        """
        Check if user already has the product (purchased, in cart, or wishlist)
        """
        return (
            UserBehavior.objects.filter(
                user=user,
                product=product,
                behavior_type__in=['purchase', 'cart_add', 'wishlist']
            ).exists()
        )
    
    def _get_trending_products(self, limit=10):
        """
        Get trending products as fallback
        """
        return Product.objects.filter(is_trending=True).order_by('-created_at')[:limit]
    
    def _get_products_by_category(self, category, limit=5):
        """
        Get products from the same category as fallback
        """
        return Product.objects.filter(category=category).exclude(uid=category.uid)[:limit]


class UserPreferenceLearner:
    """Learn and update user preferences based on behavior"""
    
    def __init__(self):
        self.preference_service = PreferenceService()
    
    def update_user_preferences(self, user):
        """
        Update user preferences based on their behavior
        """
        self.preference_service.update_user_preferences(user)


class RecommendationService:
    """Service class for recommendation operations"""
    
    def __init__(self):
        self.engine = RecommendationEngine()
        self.learner = UserPreferenceLearner()
    
    def get_recommendations_for_user(self, user, recommendation_type='hybrid', limit=10):
        """
        Get recommendations for a user based on specified type
        """
        if recommendation_type == 'content':
            return self.engine.get_content_based_recommendations(user, limit)
        elif recommendation_type == 'collaborative':
            return self.engine.get_collaborative_filtering_recommendations(user, limit)
        else:
            return self.engine.get_hybrid_recommendations(user, limit)
    
    def get_recommendations_for_product(self, product, limit=5):
        """
        Get similar products for a given product
        """
        return self.engine.get_similar_products(product, limit)
    
    def update_user_preferences(self, user):
        """
        Update user preferences based on their behavior
        """
        self.learner.update_user_preferences(user)
    
    def record_user_behavior(self, user, product, behavior_type, weight=1.0):
        """
        Record user behavior for recommendation learning
        """
        try:
            behavior, created = UserBehavior.objects.get_or_create(
                user=user,
                product=product,
                behavior_type=behavior_type,
                defaults={'weight': weight}
            )
            
            if not created:
                behavior.weight = (behavior.weight + weight) / 2
                behavior.save()
            
            # Update user preferences periodically
            if behavior_type in ['purchase', 'wishlist']:
                self.update_user_preferences(user)
                
        except Exception as e:
            print(f"Error recording user behavior: {e}") 