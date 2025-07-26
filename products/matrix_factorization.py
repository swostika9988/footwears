"""
Matrix Factorization for Advanced Collaborative Filtering
Implements SVD, NMF, and other matrix factorization techniques
"""

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF, TruncatedSVD
from sklearn.preprocessing import StandardScaler
from scipy.sparse import csr_matrix
from django.db.models import Q, Count, Avg
from django.contrib.auth.models import User
from .models import Product, UserBehavior


class MatrixFactorizationRecommender:
    """Matrix factorization based recommendation system"""
    
    def __init__(self, n_factors=50, n_iterations=100, learning_rate=0.01, regularization=0.1):
        self.n_factors = n_factors
        self.n_iterations = n_iterations
        self.learning_rate = learning_rate
        self.regularization = regularization
        self.user_factors = None
        self.item_factors = None
        self.user_mapping = {}
        self.item_mapping = {}
        self.reverse_user_mapping = {}
        self.reverse_item_mapping = {}
    
    def fit(self, rating_matrix):
        """
        Fit the matrix factorization model
        """
        try:
            if rating_matrix.empty:
                return False
            
            # Create mappings
            self._create_mappings(rating_matrix)
            
            # Convert to numpy array
            R = rating_matrix.values
            
            # Initialize factors
            n_users, n_items = R.shape
            
            # Determine appropriate number of factors
            max_factors = min(n_users, n_items, self.n_factors)
            if max_factors < 2:
                print(f"MF: Insufficient data (users: {n_users}, items: {n_items}), skipping")
                return False
            
            self.user_factors = np.random.normal(0, 0.1, (n_users, max_factors))
            self.item_factors = np.random.normal(0, 0.1, (n_items, max_factors))
            
            print(f"MF: Fitting with {max_factors} factors (users: {n_users}, items: {n_items})")
            
            # Gradient descent optimization
            for iteration in range(self.n_iterations):
                for i in range(n_users):
                    for j in range(n_items):
                        if R[i, j] > 0:  # Only for observed ratings
                            # Calculate prediction
                            prediction = np.dot(self.user_factors[i, :], self.item_factors[j, :])
                            
                            # Calculate error
                            error = R[i, j] - prediction
                            
                            # Update factors
                            for k in range(max_factors):
                                user_factor_old = self.user_factors[i, k]
                                item_factor_old = self.item_factors[j, k]
                                
                                self.user_factors[i, k] += self.learning_rate * (
                                    error * item_factor_old - self.regularization * user_factor_old
                                )
                                self.item_factors[j, k] += self.learning_rate * (
                                    error * user_factor_old - self.regularization * item_factor_old
                                )
                
                # Print progress
                if iteration % 20 == 0:
                    loss = self._calculate_loss(R)
                    print(f"Iteration {iteration}, Loss: {loss:.4f}")
            
            return True
            
        except Exception as e:
            print(f"Error fitting matrix factorization model: {e}")
            return False
    
    def predict(self, user_id, item_id):
        """
        Predict rating for user-item pair
        """
        try:
            if self.user_factors is None or self.item_factors is None:
                return 0.0
            
            if user_id not in self.user_mapping or item_id not in self.item_mapping:
                return 0.0
            
            user_idx = self.user_mapping[user_id]
            item_idx = self.item_mapping[item_id]
            
            prediction = np.dot(self.user_factors[user_idx, :], self.item_factors[item_idx, :])
            return max(0.0, prediction)  # Ensure non-negative
            
        except Exception as e:
            print(f"Error predicting rating: {e}")
            return 0.0
    
    def get_recommendations(self, user_id, limit=10):
        """
        Get recommendations for a user
        """
        try:
            if self.user_factors is None or self.item_factors is None:
                return []
            
            if user_id not in self.user_mapping:
                return []
            
            user_idx = self.user_mapping[user_id]
            user_vector = self.user_factors[user_idx, :]
            
            # Calculate scores for all items
            scores = np.dot(self.item_factors, user_vector)
            
            # Get top items
            top_indices = np.argsort(scores)[::-1][:limit]
            
            # Convert back to item IDs
            recommendations = []
            for idx in top_indices:
                item_id = self.reverse_item_mapping[idx]
                score = scores[idx]
                recommendations.append((item_id, score))
            
            return recommendations
            
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []
    
    def _create_mappings(self, rating_matrix):
        """
        Create user and item ID mappings
        """
        # User mappings
        user_ids = rating_matrix.index.tolist()
        for i, user_id in enumerate(user_ids):
            self.user_mapping[user_id] = i
            self.reverse_user_mapping[i] = user_id
        
        # Item mappings
        item_ids = rating_matrix.columns.tolist()
        for j, item_id in enumerate(item_ids):
            self.item_mapping[item_id] = j
            self.reverse_item_mapping[j] = item_id
    
    def _calculate_loss(self, R):
        """
        Calculate reconstruction loss
        """
        try:
            predictions = np.dot(self.user_factors, self.item_factors.T)
            mask = R > 0
            error = R[mask] - predictions[mask]
            loss = np.mean(error ** 2)
            return loss
        except Exception as e:
            print(f"Error calculating loss: {e}")
            return float('inf')


class SVDRecommender:
    """Singular Value Decomposition based recommender"""
    
    def __init__(self, n_components=50):
        self.n_components = n_components
        self.svd = None  # Will be initialized in fit method
        self.user_mapping = {}
        self.item_mapping = {}
        self.reverse_user_mapping = {}
        self.reverse_item_mapping = {}
        self.user_factors = None
        self.item_factors = None
    
    def fit(self, rating_matrix):
        """
        Fit SVD model
        """
        try:
            if rating_matrix.empty:
                return False
            
            # Create mappings
            self._create_mappings(rating_matrix)
            
            # Convert to numpy array
            R = rating_matrix.values
            
            # Determine appropriate number of components
            n_users, n_items = R.shape
            max_components = min(n_users, n_items, self.n_components)
            
            if max_components < 2:
                print(f"SVD: Insufficient data (users: {n_users}, items: {n_items}), skipping")
                return False
            
            # Initialize SVD with appropriate components
            self.svd = TruncatedSVD(n_components=max_components, random_state=42)
            
            # Apply SVD
            self.user_factors = self.svd.fit_transform(R)
            self.item_factors = self.svd.components_.T
            
            print(f"SVD: Fitted with {max_components} components (users: {n_users}, items: {n_items})")
            return True
            
        except Exception as e:
            print(f"Error fitting SVD model: {e}")
            return False
    
    def predict(self, user_id, item_id):
        """
        Predict rating for user-item pair
        """
        try:
            if self.user_factors is None or self.item_factors is None:
                return 0.0
            
            if user_id not in self.user_mapping or item_id not in self.item_mapping:
                return 0.0
            
            user_idx = self.user_mapping[user_id]
            item_idx = self.item_mapping[item_id]
            
            prediction = np.dot(self.user_factors[user_idx, :], self.item_factors[item_idx, :])
            return max(0.0, prediction)
            
        except Exception as e:
            print(f"Error predicting rating: {e}")
            return 0.0
    
    def get_recommendations(self, user_id, limit=10):
        """
        Get recommendations for a user
        """
        try:
            if self.user_factors is None or self.item_factors is None:
                return []
            
            if user_id not in self.user_mapping:
                return []
            
            user_idx = self.user_mapping[user_id]
            user_vector = self.user_factors[user_idx, :]
            
            # Calculate scores for all items
            scores = np.dot(self.item_factors, user_vector)
            
            # Get top items
            top_indices = np.argsort(scores)[::-1][:limit]
            
            # Convert back to item IDs
            recommendations = []
            for idx in top_indices:
                item_id = self.reverse_item_mapping[idx]
                score = scores[idx]
                recommendations.append((item_id, score))
            
            return recommendations
            
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []
    
    def _create_mappings(self, rating_matrix):
        """
        Create user and item ID mappings
        """
        # User mappings
        user_ids = rating_matrix.index.tolist()
        for i, user_id in enumerate(user_ids):
            self.user_mapping[user_id] = i
            self.reverse_user_mapping[i] = user_id
        
        # Item mappings
        item_ids = rating_matrix.columns.tolist()
        for j, item_id in enumerate(item_ids):
            self.item_mapping[item_id] = j
            self.reverse_item_mapping[j] = item_id


class NMFRecommender:
    """Non-negative Matrix Factorization based recommender"""
    
    def __init__(self, n_components=50, max_iter=200):
        self.n_components = n_components
        self.max_iter = max_iter
        self.nmf = None  # Will be initialized in fit method
        self.user_mapping = {}
        self.item_mapping = {}
        self.reverse_user_mapping = {}
        self.reverse_item_mapping = {}
        self.user_factors = None
        self.item_factors = None
    
    def fit(self, rating_matrix):
        """
        Fit NMF model
        """
        try:
            if rating_matrix.empty:
                return False
            
            # Create mappings
            self._create_mappings(rating_matrix)
            
            # Convert to numpy array
            R = rating_matrix.values
            
            # Determine appropriate number of components
            n_users, n_items = R.shape
            max_components = min(n_users, n_items, self.n_components)
            
            if max_components < 2:
                print(f"NMF: Insufficient data (users: {n_users}, items: {n_items}), skipping")
                return False
            
            # Initialize NMF with appropriate components
            self.nmf = NMF(n_components=max_components, max_iter=self.max_iter, random_state=42)
            
            # Apply NMF
            self.user_factors = self.nmf.fit_transform(R)
            self.item_factors = self.nmf.components_.T
            
            print(f"NMF: Fitted with {max_components} components (users: {n_users}, items: {n_items})")
            return True
            
        except Exception as e:
            print(f"Error fitting NMF model: {e}")
            return False
    
    def predict(self, user_id, item_id):
        """
        Predict rating for user-item pair
        """
        try:
            if self.user_factors is None or self.item_factors is None:
                return 0.0
            
            if user_id not in self.user_mapping or item_id not in self.item_mapping:
                return 0.0
            
            user_idx = self.user_mapping[user_id]
            item_idx = self.item_mapping[item_id]
            
            prediction = np.dot(self.user_factors[user_idx, :], self.item_factors[item_idx, :])
            return max(0.0, prediction)
            
        except Exception as e:
            print(f"Error predicting rating: {e}")
            return 0.0
    
    def get_recommendations(self, user_id, limit=10):
        """
        Get recommendations for a user
        """
        try:
            if self.user_factors is None or self.item_factors is None:
                return []
            
            if user_id not in self.user_mapping:
                return []
            
            user_idx = self.user_mapping[user_id]
            user_vector = self.user_factors[user_idx, :]
            
            # Calculate scores for all items
            scores = np.dot(self.item_factors, user_vector)
            
            # Get top items
            top_indices = np.argsort(scores)[::-1][:limit]
            
            # Convert back to item IDs
            recommendations = []
            for idx in top_indices:
                item_id = self.reverse_item_mapping[idx]
                score = scores[idx]
                recommendations.append((item_id, score))
            
            return recommendations
            
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []
    
    def _create_mappings(self, rating_matrix):
        """
        Create user and item ID mappings
        """
        # User mappings
        user_ids = rating_matrix.index.tolist()
        for i, user_id in enumerate(user_ids):
            self.user_mapping[user_id] = i
            self.reverse_user_mapping[i] = user_id
        
        # Item mappings
        item_ids = rating_matrix.columns.tolist()
        for j, item_id in enumerate(item_ids):
            self.item_mapping[item_id] = j
            self.reverse_item_mapping[j] = item_id


class MatrixFactorizationService:
    """Service class for matrix factorization operations"""
    
    def __init__(self):
        self.mf_recommender = MatrixFactorizationRecommender()
        self.svd_recommender = SVDRecommender()
        self.nmf_recommender = NMFRecommender()
        self.rating_matrix = None
    
    def create_rating_matrix(self):
        """
        Create user-item rating matrix from behaviors
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
            
            # Create pivot table
            rating_matrix = df.pivot_table(
                index='user_id', 
                columns='product_id', 
                values='rating', 
                fill_value=0
            )
            
            self.rating_matrix = rating_matrix
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
        return base_rating * behavior.weight
    
    def fit_models(self):
        """
        Fit all matrix factorization models
        """
        try:
            if self.rating_matrix is None:
                self.create_rating_matrix()
            
            if self.rating_matrix.empty:
                print("No rating data available")
                return False
            
            print("Fitting Matrix Factorization model...")
            mf_success = self.mf_recommender.fit(self.rating_matrix)
            
            print("Fitting SVD model...")
            svd_success = self.svd_recommender.fit(self.rating_matrix)
            
            print("Fitting NMF model...")
            nmf_success = self.nmf_recommender.fit(self.rating_matrix)
            
            # Return True if at least one model was fitted successfully
            success_count = sum([mf_success, svd_success, nmf_success])
            print(f"Successfully fitted {success_count}/3 models")
            return success_count > 0
            
        except Exception as e:
            print(f"Error fitting models: {e}")
            return False
    
    def get_recommendations(self, user, method='mf', limit=10):
        """
        Get recommendations using specified method
        """
        try:
            if method == 'mf':
                recommendations = self.mf_recommender.get_recommendations(user.id, limit)
            elif method == 'svd':
                recommendations = self.svd_recommender.get_recommendations(user.id, limit)
            elif method == 'nmf':
                recommendations = self.nmf_recommender.get_recommendations(user.id, limit)
            else:
                return []
            
            # Convert to product objects
            products = []
            for product_id, score in recommendations:
                try:
                    product = Product.objects.get(uid=product_id)
                    products.append(product)
                except Product.DoesNotExist:
                    continue
            
            return products
            
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []
    
    def get_hybrid_recommendations(self, user, limit=10):
        """
        Get hybrid recommendations from all models
        """
        try:
            # Get recommendations from all models (handle cases where models might not be fitted)
            mf_recs = self.mf_recommender.get_recommendations(user.id, limit) if hasattr(self.mf_recommender, 'user_factors') and self.mf_recommender.user_factors is not None else []
            svd_recs = self.svd_recommender.get_recommendations(user.id, limit) if hasattr(self.svd_recommender, 'user_factors') and self.svd_recommender.user_factors is not None else []
            nmf_recs = self.nmf_recommender.get_recommendations(user.id, limit) if hasattr(self.nmf_recommender, 'user_factors') and self.nmf_recommender.user_factors is not None else []
            
            # Combine recommendations
            all_recs = {}
            
            # Weight the recommendations
            for product_id, score in mf_recs:
                all_recs[product_id] = all_recs.get(product_id, 0) + score * 0.4
            
            for product_id, score in svd_recs:
                all_recs[product_id] = all_recs.get(product_id, 0) + score * 0.3
            
            for product_id, score in nmf_recs:
                all_recs[product_id] = all_recs.get(product_id, 0) + score * 0.3
            
            # Sort by combined score
            sorted_recs = sorted(all_recs.items(), key=lambda x: x[1], reverse=True)
            
            # Convert to product objects
            products = []
            for product_id, score in sorted_recs[:limit]:
                try:
                    product = Product.objects.get(uid=product_id)
                    products.append(product)
                except Product.DoesNotExist:
                    continue
            
            return products
            
        except Exception as e:
            print(f"Error getting hybrid recommendations: {e}")
            return [] 