"""
Advanced User Preference Learning System
Analyzes user behavior and builds detailed preference profiles
"""

import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from django.contrib.auth.models import User
from .models import (
    UserPreference, UserBehavior, Product, Category, Brand,
    ProductReview, Wishlist
)


class AdvancedPreferenceLearner:
    """Advanced user preference learning system"""
    
    def __init__(self):
        self.behavior_weights = {
            'purchase': 5.0,      # Highest weight for purchases
            'wishlist': 4.0,      # High weight for wishlist
            'cart_add': 3.0,      # Medium weight for cart
            'review': 2.5,        # Medium-high weight for reviews
            'view': 1.0           # Lowest weight for views
        }
        
        self.time_decay_factor = 0.95  # Decay factor for older behaviors
        self.min_confidence = 0.1      # Minimum confidence threshold
    
    def learn_user_preferences(self, user, force_recalculate=False):
        """
        Learn comprehensive user preferences from behavior
        """
        try:
            # Check if preferences need updating
            if not force_recalculate and self._preferences_are_recent(user):
                return
            
            # Clear existing preferences
            UserPreference.objects.filter(user=user).delete()
            
            # Analyze different aspects of user behavior
            self._learn_category_preferences(user)
            self._learn_brand_preferences(user)
            self._learn_price_preferences(user)
            self._learn_style_preferences(user)
            self._learn_occasion_preferences(user)
            self._learn_comfort_preferences(user)
            self._learn_material_preferences(user)
            self._learn_color_preferences(user)
            
            print(f"Preference learning completed for user {user.username}")
            
        except Exception as e:
            print(f"Error learning preferences for user {user.username}: {e}")
    
    def _preferences_are_recent(self, user):
        """
        Check if user preferences are recent (within 7 days)
        """
        recent_preference = UserPreference.objects.filter(
            user=user,
            last_updated__gte=timezone.now() - timedelta(days=7)
        ).first()
        
        return recent_preference is not None
    
    def _learn_category_preferences(self, user):
        """Learn category preferences from user behavior"""
        behaviors = self._get_user_behaviors(user)
        
        if not behaviors:
            return
        
        # Analyze category interactions
        category_scores = {}
        
        for behavior in behaviors:
            category = behavior.product.category
            weight = self.behavior_weights.get(behavior.behavior_type, 1.0)
            time_weight = self._calculate_time_weight(behavior.timestamp)
            
            if category.category_name not in category_scores:
                category_scores[category.category_name] = {
                    'category': category,
                    'score': 0.0,
                    'count': 0
                }
            
            category_scores[category.category_name]['score'] += weight * time_weight
            category_scores[category.category_name]['count'] += 1
        
        # Create preferences for top categories
        sorted_categories = sorted(
            category_scores.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )
        
        for category_name, data in sorted_categories[:5]:  # Top 5 categories
            if data['score'] > self.min_confidence:
                self._create_category_preference(
                    user, data['category'], data['score'], data['count']
                )
    
    def _learn_brand_preferences(self, user):
        """Learn brand preferences from user behavior"""
        behaviors = self._get_user_behaviors(user)
        
        if not behaviors:
            return
        
        # Analyze brand interactions
        brand_scores = {}
        
        for behavior in behaviors:
            if not behavior.product.brand:
                continue
                
            brand = behavior.product.brand
            weight = self.behavior_weights.get(behavior.behavior_type, 1.0)
            time_weight = self._calculate_time_weight(behavior.timestamp)
            
            if brand.name not in brand_scores:
                brand_scores[brand.name] = {
                    'brand': brand,
                    'score': 0.0,
                    'count': 0
                }
            
            brand_scores[brand.name]['score'] += weight * time_weight
            brand_scores[brand.name]['count'] += 1
        
        # Create preferences for top brands
        sorted_brands = sorted(
            brand_scores.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )
        
        for brand_name, data in sorted_brands[:3]:  # Top 3 brands
            if data['score'] > self.min_confidence:
                self._create_brand_preference(
                    user, data['brand'], data['score'], data['count']
                )
    
    def _learn_price_preferences(self, user):
        """Learn price range preferences from user behavior"""
        behaviors = self._get_user_behaviors(user)
        
        if not behaviors:
            return
        
        prices = []
        weights = []
        
        for behavior in behaviors:
            price = behavior.product.price
            weight = self.behavior_weights.get(behavior.behavior_type, 1.0)
            time_weight = self._calculate_time_weight(behavior.timestamp)
            
            prices.append(price)
            weights.append(weight * time_weight)
        
        if not prices:
            return
        
        # Calculate weighted average price
        total_weight = sum(weights)
        weighted_avg_price = sum(p * w for p, w in zip(prices, weights)) / total_weight
        
        # Calculate price range
        price_range = max(prices) - min(prices)
        
        # Update existing preferences with price information
        preferences = UserPreference.objects.filter(user=user)
        for preference in preferences:
            preference.price_range_min = max(0, int(weighted_avg_price - price_range/2))
            preference.price_range_max = int(weighted_avg_price + price_range/2)
            preference.save()
    
    def _learn_style_preferences(self, user):
        """Learn style preferences from product interactions"""
        behaviors = self._get_user_behaviors(user)
        
        if not behaviors:
            return
        
        style_scores = {}
        
        for behavior in behaviors:
            product = behavior.product
            weight = self.behavior_weights.get(behavior.behavior_type, 1.0)
            time_weight = self._calculate_time_weight(behavior.timestamp)
            
            # Extract style features from product
            product_text = f"{product.product_name} {product.product_desription}".lower()
            
            styles = ['casual', 'formal', 'sporty', 'elegant', 'trendy', 'classic']
            for style in styles:
                if style in product_text:
                    if style not in style_scores:
                        style_scores[style] = 0.0
                    style_scores[style] += weight * time_weight
        
        # Store style preferences in user profile or preferences
        if style_scores:
            # You could store this in a separate model or user profile
            pass
    
    def _learn_occasion_preferences(self, user):
        """Learn occasion preferences from product interactions"""
        behaviors = self._get_user_behaviors(user)
        
        if not behaviors:
            return
        
        occasion_scores = {}
        
        for behavior in behaviors:
            product = behavior.product
            weight = self.behavior_weights.get(behavior.behavior_type, 1.0)
            time_weight = self._calculate_time_weight(behavior.timestamp)
            
            # Extract occasion features from product
            product_text = f"{product.product_name} {product.product_desription}".lower()
            
            occasions = ['work', 'party', 'casual', 'sports', 'outdoor', 'gym']
            for occasion in occasions:
                if occasion in product_text:
                    if occasion not in occasion_scores:
                        occasion_scores[occasion] = 0.0
                    occasion_scores[occasion] += weight * time_weight
        
        # Store occasion preferences
        if occasion_scores:
            pass
    
    def _learn_comfort_preferences(self, user):
        """Learn comfort preferences from product interactions"""
        behaviors = self._get_user_behaviors(user)
        
        if not behaviors:
            return
        
        comfort_scores = {}
        
        for behavior in behaviors:
            product = behavior.product
            weight = self.behavior_weights.get(behavior.behavior_type, 1.0)
            time_weight = self._calculate_time_weight(behavior.timestamp)
            
            # Extract comfort features from product
            product_text = f"{product.product_name} {product.product_desription}".lower()
            
            comfort_features = ['comfortable', 'cushioned', 'breathable', 'lightweight']
            for feature in comfort_features:
                if feature in product_text:
                    if feature not in comfort_scores:
                        comfort_scores[feature] = 0.0
                    comfort_scores[feature] += weight * time_weight
        
        # Store comfort preferences
        if comfort_scores:
            pass
    
    def _learn_material_preferences(self, user):
        """Learn material preferences from product interactions"""
        behaviors = self._get_user_behaviors(user)
        
        if not behaviors:
            return
        
        material_scores = {}
        
        for behavior in behaviors:
            product = behavior.product
            weight = self.behavior_weights.get(behavior.behavior_type, 1.0)
            time_weight = self._calculate_time_weight(behavior.timestamp)
            
            # Extract material features from product
            product_text = f"{product.product_name} {product.product_desription}".lower()
            
            materials = ['leather', 'canvas', 'mesh', 'synthetic', 'rubber']
            for material in materials:
                if material in product_text:
                    if material not in material_scores:
                        material_scores[material] = 0.0
                    material_scores[material] += weight * time_weight
        
        # Store material preferences
        if material_scores:
            pass
    
    def _learn_color_preferences(self, user):
        """Learn color preferences from product interactions"""
        behaviors = self._get_user_behaviors(user)
        
        if not behaviors:
            return
        
        color_scores = {}
        
        for behavior in behaviors:
            product = behavior.product
            weight = self.behavior_weights.get(behavior.behavior_type, 1.0)
            time_weight = self._calculate_time_weight(behavior.timestamp)
            
            # Extract color features from product
            product_text = f"{product.product_name} {product.product_desription}".lower()
            
            colors = ['black', 'white', 'brown', 'blue', 'red', 'green']
            for color in colors:
                if color in product_text:
                    if color not in color_scores:
                        color_scores[color] = 0.0
                    color_scores[color] += weight * time_weight
        
        # Store color preferences
        if color_scores:
            pass
    
    def _get_user_behaviors(self, user):
        """Get all user behaviors with time weighting"""
        return UserBehavior.objects.filter(user=user).order_by('-timestamp')
    
    def _calculate_time_weight(self, timestamp):
        """
        Calculate time-based weight for behavior (newer behaviors get higher weight)
        """
        days_old = (timezone.now() - timestamp).days
        return self.time_decay_factor ** days_old
    
    def _create_category_preference(self, user, category, score, count):
        """Create a category preference"""
        try:
            UserPreference.objects.create(
                user=user,
                category=category,
                weight=min(score / 10, 1.0),  # Normalize to 0-1
                price_range_min=0,
                price_range_max=10000
            )
        except Exception as e:
            print(f"Error creating category preference: {e}")
    
    def _create_brand_preference(self, user, brand, score, count):
        """Create a brand preference"""
        try:
            # Find a category for this brand
            category = brand.products.first().category if brand.products.exists() else Category.objects.first()
            
            UserPreference.objects.create(
                user=user,
                category=category,
                brand=brand,
                weight=min(score / 10, 1.0),  # Normalize to 0-1
                price_range_min=0,
                price_range_max=10000
            )
        except Exception as e:
            print(f"Error creating brand preference: {e}")


class PreferenceAnalyzer:
    """Analyze and visualize user preferences"""
    
    def __init__(self):
        self.learner = AdvancedPreferenceLearner()
    
    def get_user_preference_summary(self, user):
        """
        Get a summary of user preferences
        """
        try:
            preferences = UserPreference.objects.filter(user=user)
            
            summary = {
                'total_preferences': preferences.count(),
                'categories': [],
                'brands': [],
                'price_range': None,
                'confidence_score': 0.0
            }
            
            # Category preferences
            for pref in preferences:
                if pref.category:
                    summary['categories'].append({
                        'name': pref.category.category_name,
                        'weight': pref.weight
                    })
                
                if pref.brand:
                    summary['brands'].append({
                        'name': pref.brand.name,
                        'weight': pref.weight
                    })
            
            # Price range
            if preferences.exists():
                avg_min = preferences.aggregate(avg_min=Avg('price_range_min'))['avg_min'] or 0
                avg_max = preferences.aggregate(avg_max=Avg('price_range_max'))['avg_max'] or 10000
                summary['price_range'] = {
                    'min': avg_min,
                    'max': avg_max
                }
            
            # Confidence score
            if preferences.exists():
                avg_weight = preferences.aggregate(avg_weight=Avg('weight'))['avg_weight'] or 0
                summary['confidence_score'] = avg_weight
            
            return summary
            
        except Exception as e:
            print(f"Error getting preference summary: {e}")
            return None
    
    def get_similar_users(self, user, limit=5):
        """
        Find users with similar preferences
        """
        try:
            user_preferences = UserPreference.objects.filter(user=user)
            
            if not user_preferences.exists():
                return []
            
            # Get all other users with preferences
            other_users = User.objects.filter(
                preferences__isnull=False
            ).exclude(id=user.id).distinct()
            
            similarities = []
            
            for other_user in other_users:
                other_preferences = UserPreference.objects.filter(user=other_user)
                
                if not other_preferences.exists():
                    continue
                
                # Calculate similarity
                similarity = self._calculate_preference_similarity(
                    user_preferences, other_preferences
                )
                
                if similarity > 0.1:  # Only include meaningful similarities
                    similarities.append((other_user, similarity))
            
            # Sort by similarity and return top matches
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            print(f"Error finding similar users: {e}")
            return []
    
    def _calculate_preference_similarity(self, user_prefs, other_prefs):
        """
        Calculate similarity between two users' preferences
        """
        if not user_prefs.exists() or not other_prefs.exists():
            return 0.0
        
        # Create preference vectors
        user_vector = {}
        other_vector = {}
        
        # User preferences
        for pref in user_prefs:
            if pref.category:
                key = f"category_{pref.category.id}"
                user_vector[key] = pref.weight
            
            if pref.brand:
                key = f"brand_{pref.brand.id}"
                user_vector[key] = pref.weight
        
        # Other user preferences
        for pref in other_prefs:
            if pref.category:
                key = f"category_{pref.category.id}"
                other_vector[key] = pref.weight
            
            if pref.brand:
                key = f"brand_{pref.brand.id}"
                other_vector[key] = pref.weight
        
        # Calculate cosine similarity
        common_keys = set(user_vector.keys()) & set(other_vector.keys())
        
        if not common_keys:
            return 0.0
        
        numerator = sum(user_vector[key] * other_vector[key] for key in common_keys)
        user_norm = sum(val ** 2 for val in user_vector.values()) ** 0.5
        other_norm = sum(val ** 2 for val in other_vector.values()) ** 0.5
        
        if user_norm == 0 or other_norm == 0:
            return 0.0
        
        return numerator / (user_norm * other_norm)


class PreferenceService:
    """Service class for preference operations"""
    
    def __init__(self):
        self.learner = AdvancedPreferenceLearner()
        self.analyzer = PreferenceAnalyzer()
    
    def update_user_preferences(self, user, force_recalculate=False):
        """
        Update user preferences based on behavior
        """
        self.learner.learn_user_preferences(user, force_recalculate)
    
    def get_user_preferences(self, user):
        """
        Get user preference summary
        """
        return self.analyzer.get_user_preference_summary(user)
    
    def get_similar_users(self, user, limit=5):
        """
        Get users with similar preferences
        """
        return self.analyzer.get_similar_users(user, limit)
    
    def update_all_user_preferences(self, force_recalculate=False):
        """
        Update preferences for all users
        """
        users = User.objects.filter(behaviors__isnull=False).distinct()
        
        for user in users:
            self.update_user_preferences(user, force_recalculate)
        
        print(f"Updated preferences for {users.count()} users") 