"""
Advanced Collaborative Filtering System
Implements user-based and item-based collaborative filtering
"""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import pdist, squareform
from django.db.models import Q, Count, Avg, Sum, F
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import (
    Product, UserBehavior, UserSimilarity, ProductSimilarity, 
    UserRating, ProductReview, Category, Brand
)


class UserBasedCollaborativeFilter:
    """User-based collaborative filtering implementation"""
    
    def __init__(self):
        self.similarity_threshold = 0.1
        self.min_common_items = 2
        self.max_neighbors = 50
        
    def get_user_based_recommendations(self, user, limit=10):
        """
        Get user-based collaborative filtering recommendations
        """
        try:
            # Get user's rating matrix
            user_ratings = self._get_user_rating_matrix()
            
            if user_ratings.empty:
                return []
            
            # Find similar users
            similar_users = self._find_similar_users(user, user_ratings)
            
            if not similar_users:
                return []
            
            # Generate recommendations
            recommendations = self._generate_recommendations(user, similar_users, user_ratings, limit)
            
            return recommendations
            
        except Exception as e:
            print(f"Error in user-based collaborative filtering: {e}")
            return []
    
    def _get_user_rating_matrix(self):
        """
        Create user-item rating matrix from user behaviors
        """
        try:
            # Get all user behaviors
            behaviors = UserBehavior.objects.select_related('user', 'product').all()
            
            if not behaviors.exists():
                return pd.DataFrame()
            
            # Create rating matrix
            data = []
            for behavior in behaviors:
                # Convert behavior to implicit rating
                rating = self._behavior_to_rating(behavior)
                data.append({
                    'user_id': behavior.user.id,
                    'product_id': behavior.product.uid,
                    'rating': rating,
                    'timestamp': behavior.timestamp
                })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            if df.empty:
                return pd.DataFrame()
            
            # Create pivot table (user-item matrix)
            rating_matrix = df.pivot_table(
                index='user_id', 
                columns='product_id', 
                values='rating', 
                fill_value=0
            )
            
            return rating_matrix
            
        except Exception as e:
            print(f"Error creating rating matrix: {e}")
            return pd.DataFrame()
    
    def _behavior_to_rating(self, behavior):
        """
        Convert user behavior to implicit rating
        """
        behavior_weights = {
            'purchase': 5.0,
            'wishlist': 4.0,
            'cart_add': 3.0,
            'review': 2.5,
            'view': 1.0
        }
        
        base_rating = behavior_weights.get(behavior.behavior_type, 1.0)
        
        # Apply time decay
        days_old = (timezone.now() - behavior.timestamp).days
        time_decay = 0.95 ** days_old
        
        # Apply behavior weight
        final_rating = base_rating * behavior.weight * time_decay
        
        return final_rating
    
    def _find_similar_users(self, target_user, rating_matrix):
        """
        Find users similar to the target user
        """
        try:
            if target_user.id not in rating_matrix.index:
                return []
            
            # Get target user's ratings
            target_ratings = rating_matrix.loc[target_user.id]
            
            # Calculate similarities with all other users
            similarities = []
            
            for user_id in rating_matrix.index:
                if user_id == target_user.id:
                    continue
                
                other_ratings = rating_matrix.loc[user_id]
                
                # Find common items
                common_items = (target_ratings > 0) & (other_ratings > 0)
                
                if common_items.sum() < self.min_common_items:
                    continue
                
                # Calculate cosine similarity
                target_vector = target_ratings[common_items].values
                other_vector = other_ratings[common_items].values
                
                if len(target_vector) == 0 or len(other_vector) == 0:
                    continue
                
                # Normalize vectors
                target_norm = np.linalg.norm(target_vector)
                other_norm = np.linalg.norm(other_vector)
                
                if target_norm == 0 or other_norm == 0:
                    continue
                
                similarity = np.dot(target_vector, other_vector) / (target_norm * other_norm)
                
                if similarity > self.similarity_threshold:
                    similarities.append((user_id, similarity))
            
            # Sort by similarity and return top neighbors
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:self.max_neighbors]
            
        except Exception as e:
            print(f"Error finding similar users: {e}")
            return []
    
    def _generate_recommendations(self, target_user, similar_users, rating_matrix, limit):
        """
        Generate recommendations based on similar users
        """
        try:
            if not similar_users:
                return []
            
            # Get target user's rated items
            target_ratings = rating_matrix.loc[target_user.id]
            rated_items = target_ratings[target_ratings > 0].index.tolist()
            
            # Calculate predicted ratings for unrated items
            predictions = {}
            
            for product_id in rating_matrix.columns:
                if product_id in rated_items:
                    continue
                
                # Calculate weighted average rating from similar users
                weighted_sum = 0
                similarity_sum = 0
                
                for user_id, similarity in similar_users:
                    if user_id in rating_matrix.index:
                        user_rating = rating_matrix.loc[user_id, product_id]
                        if user_rating > 0:
                            weighted_sum += user_rating * similarity
                            similarity_sum += similarity
                
                if similarity_sum > 0:
                    predicted_rating = weighted_sum / similarity_sum
                    predictions[product_id] = predicted_rating
            
            # Sort by predicted rating
            sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
            
            # Get product objects
            recommended_products = []
            for product_id, predicted_rating in sorted_predictions[:limit]:
                try:
                    product = Product.objects.get(uid=product_id)
                    recommended_products.append(product)
                except Product.DoesNotExist:
                    continue
            
            return recommended_products
            
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return []


class ItemBasedCollaborativeFilter:
    """Item-based collaborative filtering implementation"""
    
    def __init__(self):
        self.similarity_threshold = 0.1
        self.min_common_users = 2
        self.max_similar_items = 20
        
    def get_item_based_recommendations(self, user, limit=10):
        """
        Get item-based collaborative filtering recommendations
        """
        try:
            # Get item-item similarity matrix
            item_similarity = self._get_item_similarity_matrix()
            
            if item_similarity.empty:
                return []
            
            # Get user's rated items
            user_ratings = self._get_user_ratings(user)
            
            if not user_ratings:
                return []
            
            # Generate recommendations
            recommendations = self._generate_item_recommendations(user, user_ratings, item_similarity, limit)
            
            return recommendations
            
        except Exception as e:
            print(f"Error in item-based collaborative filtering: {e}")
            return []
    
    def _get_item_similarity_matrix(self):
        """
        Create item-item similarity matrix
        """
        try:
            # Get all user behaviors
            behaviors = UserBehavior.objects.select_related('user', 'product').all()
            
            if not behaviors.exists():
                return pd.DataFrame()
            
            # Create rating matrix
            data = []
            for behavior in behaviors:
                rating = self._behavior_to_rating(behavior)
                data.append({
                    'user_id': behavior.user.id,
                    'product_id': behavior.product.uid,
                    'rating': rating
                })
            
            df = pd.DataFrame(data)
            
            if df.empty:
                return pd.DataFrame()
            
            # Create pivot table (item-user matrix)
            rating_matrix = df.pivot_table(
                index='product_id', 
                columns='user_id', 
                values='rating', 
                fill_value=0
            )
            
            # Calculate item-item similarity
            item_similarity = cosine_similarity(rating_matrix)
            
            # Create DataFrame with product IDs
            similarity_df = pd.DataFrame(
                item_similarity,
                index=rating_matrix.index,
                columns=rating_matrix.index
            )
            
            return similarity_df
            
        except Exception as e:
            print(f"Error creating item similarity matrix: {e}")
            return pd.DataFrame()
    
    def _behavior_to_rating(self, behavior):
        """
        Convert user behavior to implicit rating
        """
        behavior_weights = {
            'purchase': 5.0,
            'wishlist': 4.0,
            'cart_add': 3.0,
            'review': 2.5,
            'view': 1.0
        }
        
        base_rating = behavior_weights.get(behavior.behavior_type, 1.0)
        return base_rating * behavior.weight
    
    def _get_user_ratings(self, user):
        """
        Get user's ratings for items
        """
        try:
            behaviors = UserBehavior.objects.filter(user=user)
            
            ratings = {}
            for behavior in behaviors:
                rating = self._behavior_to_rating(behavior)
                ratings[behavior.product.uid] = rating
            
            return ratings
            
        except Exception as e:
            print(f"Error getting user ratings: {e}")
            return {}
    
    def _generate_item_recommendations(self, user, user_ratings, item_similarity, limit):
        """
        Generate recommendations based on item similarities
        """
        try:
            if not user_ratings:
                return []
            
            # Calculate predicted ratings for unrated items
            predictions = {}
            
            for product_id in item_similarity.index:
                if product_id in user_ratings:
                    continue
                
                # Calculate weighted average rating from similar items
                weighted_sum = 0
                similarity_sum = 0
                
                for rated_item, user_rating in user_ratings.items():
                    if rated_item in item_similarity.index:
                        similarity = item_similarity.loc[product_id, rated_item]
                        if similarity > self.similarity_threshold:
                            weighted_sum += user_rating * similarity
                            similarity_sum += similarity
                
                if similarity_sum > 0:
                    predicted_rating = weighted_sum / similarity_sum
                    predictions[product_id] = predicted_rating
            
            # Sort by predicted rating
            sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
            
            # Get product objects
            recommended_products = []
            for product_id, predicted_rating in sorted_predictions[:limit]:
                try:
                    product = Product.objects.get(uid=product_id)
                    recommended_products.append(product)
                except Product.DoesNotExist:
                    continue
            
            return recommended_products
            
        except Exception as e:
            print(f"Error generating item recommendations: {e}")
            return []


class AdvancedCollaborativeFilter:
    """Advanced collaborative filtering with multiple approaches"""
    
    def __init__(self):
        self.user_based_filter = UserBasedCollaborativeFilter()
        self.item_based_filter = ItemBasedCollaborativeFilter()
        self.user_weight = 0.6  # Weight for user-based recommendations
        self.item_weight = 0.4  # Weight for item-based recommendations
    
    def get_hybrid_collaborative_recommendations(self, user, limit=10):
        """
        Get hybrid collaborative filtering recommendations
        """
        try:
            # Get user-based recommendations
            user_based_recs = self.user_based_filter.get_user_based_recommendations(user, limit)
            
            # Get item-based recommendations
            item_based_recs = self.item_based_filter.get_item_based_recommendations(user, limit)
            
            # Combine recommendations
            combined_recs = self._combine_recommendations(
                user_based_recs, item_based_recs, limit
            )
            
            return combined_recs
            
        except Exception as e:
            print(f"Error in hybrid collaborative filtering: {e}")
            return []
    
    def _combine_recommendations(self, user_based_recs, item_based_recs, limit):
        """
        Combine user-based and item-based recommendations
        """
        try:
            # Create scoring dictionary
            product_scores = {}
            
            # Score user-based recommendations
            for i, product in enumerate(user_based_recs):
                score = self.user_weight * (1.0 - i / len(user_based_recs))
                product_scores[product.uid] = product_scores.get(product.uid, 0) + score
            
            # Score item-based recommendations
            for i, product in enumerate(item_based_recs):
                score = self.item_weight * (1.0 - i / len(item_based_recs))
                product_scores[product.uid] = product_scores.get(product.uid, 0) + score
            
            # Sort by combined score
            sorted_products = sorted(
                product_scores.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
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
            print(f"Error combining recommendations: {e}")
            return []
    
    def get_user_similarity_matrix(self):
        """
        Get user similarity matrix for analysis
        """
        try:
            rating_matrix = self.user_based_filter._get_user_rating_matrix()
            
            if rating_matrix.empty:
                return pd.DataFrame()
            
            # Calculate user similarity matrix
            user_similarity = cosine_similarity(rating_matrix)
            
            # Create DataFrame
            similarity_df = pd.DataFrame(
                user_similarity,
                index=rating_matrix.index,
                columns=rating_matrix.index
            )
            
            return similarity_df
            
        except Exception as e:
            print(f"Error creating user similarity matrix: {e}")
            return pd.DataFrame()
    
    def get_item_similarity_matrix(self):
        """
        Get item similarity matrix for analysis
        """
        try:
            return self.item_based_filter._get_item_similarity_matrix()
        except Exception as e:
            print(f"Error getting item similarity matrix: {e}")
            return pd.DataFrame()


class CollaborativeFilteringService:
    """Service class for collaborative filtering operations"""
    
    def __init__(self):
        self.advanced_filter = AdvancedCollaborativeFilter()
        self.user_based_filter = UserBasedCollaborativeFilter()
        self.item_based_filter = ItemBasedCollaborativeFilter()
    
    def get_collaborative_recommendations(self, user, method='hybrid', limit=10):
        """
        Get collaborative filtering recommendations
        """
        try:
            if method == 'user_based':
                return self.user_based_filter.get_user_based_recommendations(user, limit)
            elif method == 'item_based':
                return self.item_based_filter.get_item_based_recommendations(user, limit)
            elif method == 'hybrid':
                return self.advanced_filter.get_hybrid_collaborative_recommendations(user, limit)
            else:
                return []
                
        except Exception as e:
            print(f"Error getting collaborative recommendations: {e}")
            return []
    
    def get_similar_users(self, user, limit=5):
        """
        Get users similar to the given user
        """
        try:
            user_similarity = self.advanced_filter.get_user_similarity_matrix()
            
            if user_similarity.empty or user.id not in user_similarity.index:
                return []
            
            # Get similarities for the user
            user_similarities = user_similarity.loc[user.id]
            
            # Sort by similarity
            similar_users = []
            for other_user_id, similarity in user_similarities.items():
                if other_user_id != user.id and similarity > 0.1:
                    try:
                        other_user = User.objects.get(id=other_user_id)
                        similar_users.append((other_user, similarity))
                    except User.DoesNotExist:
                        continue
            
            # Sort and return top matches
            similar_users.sort(key=lambda x: x[1], reverse=True)
            return similar_users[:limit]
            
        except Exception as e:
            print(f"Error finding similar users: {e}")
            return []
    
    def get_similar_products(self, product, limit=5):
        """
        Get products similar to the given product
        """
        try:
            item_similarity = self.advanced_filter.get_item_similarity_matrix()
            
            if item_similarity.empty or product.uid not in item_similarity.index:
                return []
            
            # Get similarities for the product
            product_similarities = item_similarity.loc[product.uid]
            
            # Sort by similarity
            similar_products = []
            for other_product_id, similarity in product_similarities.items():
                if other_product_id != product.uid and similarity > 0.1:
                    try:
                        other_product = Product.objects.get(uid=other_product_id)
                        similar_products.append((other_product, similarity))
                    except Product.DoesNotExist:
                        continue
            
            # Sort and return top matches
            similar_products.sort(key=lambda x: x[1], reverse=True)
            return similar_products[:limit]
            
        except Exception as e:
            print(f"Error finding similar products: {e}")
            return []
    
    def update_similarity_matrices(self):
        """
        Update similarity matrices (can be run periodically)
        """
        try:
            print("Updating user similarity matrix...")
            user_similarity = self.advanced_filter.get_user_similarity_matrix()
            
            print("Updating item similarity matrix...")
            item_similarity = self.advanced_filter.get_item_similarity_matrix()
            
            print("Similarity matrices updated successfully!")
            return True
            
        except Exception as e:
            print(f"Error updating similarity matrices: {e}")
            return False 