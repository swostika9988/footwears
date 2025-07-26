"""
Similarity Calculator for Collaborative Filtering
Calculates user and product similarities using various algorithms
"""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.preprocessing import StandardScaler
from django.db.models import Q, Count, Avg, Max
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    Product, UserBehavior, UserSimilarity, ProductSimilarity, 
    UserRating, ProductReview, Category, Brand
)


class SimilarityCalculator:
    """Calculate similarities between users and products"""
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def calculate_user_similarities(self, force_recalculate=False):
        """
        Calculate similarities between all users
        """
        try:
            # Get all users with behaviors
            users_with_behaviors = User.objects.filter(behaviors__isnull=False).distinct()
            
            if not force_recalculate:
                # Only calculate for users without recent similarity data
                recent_threshold = timezone.now() - timezone.timedelta(days=7)
                users_with_behaviors = users_with_behaviors.exclude(
                    similarities_as_user1__last_calculated__gte=recent_threshold
                ).exclude(
                    similarities_as_user2__last_calculated__gte=recent_threshold
                )
            
            user_list = list(users_with_behaviors)
            
            if len(user_list) < 2:
                return
            
            # Create user behavior matrix
            behavior_matrix = self._create_user_behavior_matrix(user_list)
            
            # Calculate similarities
            similarities = cosine_similarity(behavior_matrix)
            
            # Store similarities
            for i, user1 in enumerate(user_list):
                for j, user2 in enumerate(user_list):
                    if i != j and similarities[i][j] > 0.1:  # Only store meaningful similarities
                        self._store_user_similarity(user1, user2, similarities[i][j])
            
            print(f"Calculated similarities for {len(user_list)} users")
            
        except Exception as e:
            print(f"Error calculating user similarities: {e}")
    
    def calculate_product_similarities(self, force_recalculate=False):
        """
        Calculate similarities between all products
        """
        try:
            # Get all products with behaviors
            products_with_behaviors = Product.objects.filter(user_behaviors__isnull=False).distinct()
            
            if not force_recalculate:
                # Only calculate for products without recent similarity data
                recent_threshold = timezone.now() - timezone.timedelta(days=7)
                products_with_behaviors = products_with_behaviors.exclude(
                    similarities_as_product1__last_calculated__gte=recent_threshold
                ).exclude(
                    similarities_as_product2__last_calculated__gte=recent_threshold
                )
            
            product_list = list(products_with_behaviors)
            
            if len(product_list) < 2:
                return
            
            # Create product feature matrix
            feature_matrix = self._create_product_feature_matrix(product_list)
            
            # Calculate similarities
            similarities = cosine_similarity(feature_matrix)
            
            # Store similarities
            for i, product1 in enumerate(product_list):
                for j, product2 in enumerate(product_list):
                    if i != j and similarities[i][j] > 0.1:  # Only store meaningful similarities
                        self._store_product_similarity(product1, product2, similarities[i][j])
            
            print(f"Calculated similarities for {len(product_list)} products")
            
        except Exception as e:
            print(f"Error calculating product similarities: {e}")
    
    def _create_user_behavior_matrix(self, users):
        """
        Create a matrix of user behaviors for similarity calculation
        """
        try:
            # Get all products
            products = Product.objects.all()
            product_ids = list(products.values_list('uid', flat=True))
            
            # Create behavior matrix
            matrix = np.zeros((len(users), len(product_ids)))
            
            # Fill matrix with behavior data
            for i, user in enumerate(users):
                behaviors = UserBehavior.objects.filter(user=user)
                
                for behavior in behaviors:
                    if behavior.product.uid in product_ids:
                        product_idx = product_ids.index(behavior.product.uid)
                        
                        # Weight based on behavior type
                        behavior_weight = {
                            'purchase': 3.0,
                            'wishlist': 2.0,
                            'cart_add': 1.5,
                            'review': 1.0,
                            'view': 0.5
                        }.get(behavior.behavior_type, 0.5)
                        
                        matrix[i][product_idx] += behavior_weight * behavior.weight
            
            return matrix
            
        except Exception as e:
            print(f"Error creating user behavior matrix: {e}")
            return np.zeros((len(users), 1))
    
    def _create_product_feature_matrix(self, products):
        """
        Create a matrix of product features for similarity calculation
        """
        try:
            # Define features for products
            features = []
            
            for product in products:
                feature_vector = []
                
                # Category features (one-hot encoding)
                categories = Category.objects.all()
                for category in categories:
                    feature_vector.append(1.0 if product.category == category else 0.0)
                
                # Brand features (one-hot encoding)
                brands = Brand.objects.all()
                for brand in brands:
                    feature_vector.append(1.0 if product.brand == brand else 0.0)
                
                # Price features (normalized)
                max_price = Product.objects.aggregate(max_price=Max('price'))['max_price'] or 1
                feature_vector.append(product.price / max_price)
                
                # Discount features
                if product.discounted_price:
                    discount_percent = (product.price - product.discounted_price) / product.price
                    feature_vector.append(discount_percent)
                else:
                    feature_vector.append(0.0)
                
                # Boolean features
                feature_vector.append(1.0 if product.is_trending else 0.0)
                feature_vector.append(1.0 if product.newest_product else 0.0)
                feature_vector.append(1.0 if product.is_men else 0.0)
                feature_vector.append(1.0 if product.is_women else 0.0)
                
                # Rating features
                avg_rating = product.reviews.aggregate(avg_rating=Avg('stars'))['avg_rating'] or 0
                feature_vector.append(avg_rating / 5.0)  # Normalize to 0-1
                
                # Review count features
                review_count = product.reviews.count()
                max_reviews = Product.objects.annotate(review_count=Count('reviews')).aggregate(
                    max_reviews=Max('review_count')
                )['max_reviews'] or 1
                feature_vector.append(review_count / max_reviews)
                
                features.append(feature_vector)
            
            return np.array(features)
            
        except Exception as e:
            print(f"Error creating product feature matrix: {e}")
            return np.zeros((len(products), 1))
    
    def _store_user_similarity(self, user1, user2, similarity_score):
        """
        Store user similarity in database
        """
        try:
            # Ensure user1 < user2 to avoid duplicates
            if user1.id > user2.id:
                user1, user2 = user2, user1
            
            similarity, created = UserSimilarity.objects.get_or_create(
                user1=user1,
                user2=user2,
                defaults={'similarity_score': similarity_score}
            )
            
            if not created:
                similarity.similarity_score = similarity_score
                similarity.save()
                
        except Exception as e:
            print(f"Error storing user similarity: {e}")
    
    def _store_product_similarity(self, product1, product2, similarity_score):
        """
        Store product similarity in database
        """
        try:
            # Ensure product1 < product2 to avoid duplicates
            if product1.uid > product2.uid:
                product1, product2 = product2, product1
            
            similarity, created = ProductSimilarity.objects.get_or_create(
                product1=product1,
                product2=product2,
                defaults={'similarity_score': similarity_score}
            )
            
            if not created:
                similarity.similarity_score = similarity_score
                similarity.save()
                
        except Exception as e:
            print(f"Error storing product similarity: {e}")


class RatingCalculator:
    """Calculate user ratings for products based on behavior"""
    
    def __init__(self):
        self.behavior_weights = {
            'purchase': 5.0,  # Highest weight for purchases
            'wishlist': 4.0,  # High weight for wishlist
            'cart_add': 3.0,  # Medium weight for cart
            'review': 2.0,    # Lower weight for reviews (already have rating)
            'view': 1.0       # Lowest weight for views
        }
    
    def calculate_user_ratings(self, user=None):
        """
        Calculate implicit ratings for users based on their behavior
        """
        try:
            if user:
                users = [user]
            else:
                users = User.objects.filter(behaviors__isnull=False).distinct()
            
            for user in users:
                self._calculate_ratings_for_user(user)
                
        except Exception as e:
            print(f"Error calculating user ratings: {e}")
    
    def _calculate_ratings_for_user(self, user):
        """
        Calculate ratings for a specific user
        """
        try:
            behaviors = UserBehavior.objects.filter(user=user)
            
            for behavior in behaviors:
                # Calculate implicit rating based on behavior
                implicit_rating = self.behavior_weights.get(behavior.behavior_type, 0.5)
                
                # Adjust based on behavior weight
                implicit_rating *= behavior.weight
                
                # Normalize to 0-5 scale
                implicit_rating = min(5.0, max(0.0, implicit_rating))
                
                # Calculate confidence based on behavior type
                confidence = {
                    'purchase': 1.0,
                    'wishlist': 0.8,
                    'cart_add': 0.6,
                    'review': 0.4,
                    'view': 0.2
                }.get(behavior.behavior_type, 0.3)
                
                # Store or update rating
                rating, created = UserRating.objects.get_or_create(
                    user=user,
                    product=behavior.product,
                    defaults={
                        'rating': implicit_rating,
                        'confidence': confidence
                    }
                )
                
                if not created:
                    # Update existing rating (weighted average)
                    new_rating = (rating.rating * rating.confidence + implicit_rating * confidence) / (rating.confidence + confidence)
                    new_confidence = min(1.0, rating.confidence + confidence * 0.1)
                    
                    rating.rating = new_rating
                    rating.confidence = new_confidence
                    rating.save()
                    
        except Exception as e:
            print(f"Error calculating ratings for user {user.username}: {e}")


class SimilarityService:
    """Service class for similarity operations"""
    
    def __init__(self):
        self.calculator = SimilarityCalculator()
        self.rating_calculator = RatingCalculator()
    
    def update_all_similarities(self, force_recalculate=False):
        """
        Update all similarity calculations
        """
        print("Updating user similarities...")
        self.calculator.calculate_user_similarities(force_recalculate)
        
        print("Updating product similarities...")
        self.calculator.calculate_product_similarities(force_recalculate)
        
        print("Updating user ratings...")
        self.rating_calculator.calculate_user_ratings()
        
        print("Similarity update completed!")
    
    def get_similar_users(self, user, limit=5):
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
    
    def get_similar_products(self, product, limit=5):
        """
        Get products similar to the given product
        """
        try:
            similarities = ProductSimilarity.objects.filter(
                Q(product1=product) | Q(product2=product)
            ).order_by('-similarity_score')[:limit]
            
            similar_products = []
            for similarity in similarities:
                if similarity.product1 == product:
                    similar_product = similarity.product2
                else:
                    similar_product = similarity.product1
                
                similar_products.append((similar_product, similarity.similarity_score))
            
            return similar_products
            
        except Exception as e:
            print(f"Error getting similar products: {e}")
            return [] 