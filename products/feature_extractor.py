"""
Product Feature Extractor for Content-Based Filtering
Extracts and analyzes product features for recommendation system
"""

import re
import numpy as np
from textblob import TextBlob
from django.db.models import Q, Count, Avg
from django.utils.text import slugify
from .models import (
    Product, ProductFeature, Category, Brand, ColorVariant, 
    SizeVariant, ProductReview, UserBehavior
)


class ProductFeatureExtractor:
    """Extract and analyze product features for content-based filtering"""
    
    def __init__(self):
        # Define feature categories
        self.style_features = [
            'casual', 'formal', 'sporty', 'elegant', 'trendy', 'classic',
            'modern', 'vintage', 'minimalist', 'bold', 'sophisticated'
        ]
        
        self.occasion_features = [
            'work', 'party', 'casual', 'sports', 'outdoor', 'indoor',
            'travel', 'gym', 'running', 'walking', 'dancing', 'hiking'
        ]
        
        self.comfort_features = [
            'comfortable', 'cushioned', 'breathable', 'lightweight',
            'flexible', 'supportive', 'soft', 'durable', 'waterproof'
        ]
        
        self.color_features = [
            'black', 'white', 'brown', 'blue', 'red', 'green', 'yellow',
            'pink', 'purple', 'orange', 'gray', 'navy', 'beige', 'cream'
        ]
        
        self.material_features = [
            'leather', 'canvas', 'mesh', 'synthetic', 'rubber', 'suede',
            'nylon', 'polyester', 'cotton', 'wool', 'denim', 'velvet'
        ]
        
        self.price_ranges = [
            (0, 1000, 'budget'),
            (1000, 3000, 'affordable'),
            (3000, 7000, 'mid-range'),
            (7000, 15000, 'premium'),
            (15000, float('inf'), 'luxury')
        ]
    
    def extract_all_product_features(self, force_recalculate=False):
        """
        Extract features for all products
        """
        products = Product.objects.all()
        
        for product in products:
            if force_recalculate or not product.features.exists():
                self.extract_product_features(product)
        
        print(f"Feature extraction completed for {products.count()} products")
    
    def extract_product_features(self, product):
        """
        Extract comprehensive features for a single product
        """
        try:
            # Clear existing features
            product.features.all().delete()
            
            # Extract different types of features
            self._extract_text_based_features(product)
            self._extract_price_features(product)
            self._extract_category_features(product)
            self._extract_brand_features(product)
            self._extract_popularity_features(product)
            self._extract_review_features(product)
            self._extract_behavior_features(product)
            self._extract_temporal_features(product)
            
        except Exception as e:
            print(f"Error extracting features for product {product.product_name}: {e}")
    
    def _extract_text_based_features(self, product):
        """Extract features from product text (name, description)"""
        text = f"{product.product_name} {product.product_desription}".lower()
        
        # Style features
        for style in self.style_features:
            if style in text:
                self._create_feature(product, f"style_{style}", 1.0)
        
        # Occasion features
        for occasion in self.occasion_features:
            if occasion in text:
                self._create_feature(product, f"occasion_{occasion}", 1.0)
        
        # Comfort features
        for comfort in self.comfort_features:
            if comfort in text:
                self._create_feature(product, f"comfort_{comfort}", 1.0)
        
        # Material features
        for material in self.material_features:
            if material in text:
                self._create_feature(product, f"material_{material}", 1.0)
        
        # Color features
        for color in self.color_features:
            if color in text:
                self._create_feature(product, f"color_{color}", 1.0)
        
        # Sentiment analysis
        blob = TextBlob(text)
        sentiment_score = (blob.sentiment.polarity + 1) / 2  # Normalize to 0-1
        self._create_feature(product, "sentiment_positive", sentiment_score)
        
        # Text complexity
        word_count = len(text.split())
        complexity_score = min(word_count / 100, 1.0)  # Normalize
        self._create_feature(product, "text_complexity", complexity_score)
    
    def _extract_price_features(self, product):
        """Extract price-related features"""
        # Price range category
        for min_price, max_price, category in self.price_ranges:
            if min_price <= product.price <= max_price:
                self._create_feature(product, f"price_range_{category}", 1.0)
                break
        
        # Discount features
        if product.discounted_price:
            discount_percent = (product.price - product.discounted_price) / product.price
            self._create_feature(product, "has_discount", 1.0)
            self._create_feature(product, "discount_percent", discount_percent)
        else:
            self._create_feature(product, "has_discount", 0.0)
            self._create_feature(product, "discount_percent", 0.0)
        
        # Price competitiveness (normalized)
        avg_price = Product.objects.aggregate(avg_price=Avg('price'))['avg_price'] or product.price
        price_ratio = product.price / avg_price
        self._create_feature(product, "price_competitiveness", 1 / price_ratio)
    
    def _extract_category_features(self, product):
        """Extract category-related features"""
        # Category features
        self._create_feature(product, f"category_{slugify(product.category.category_name)}", 1.0)
        
        # Category popularity
        category_count = product.category.products.count()
        max_category_count = Category.objects.annotate(
            product_count=Count('products')
        ).aggregate(max_count=Avg('product_count'))['max_count'] or 1
        
        category_popularity = category_count / max_category_count
        self._create_feature(product, "category_popularity", category_popularity)
    
    def _extract_brand_features(self, product):
        """Extract brand-related features"""
        if product.brand:
            # Brand features
            self._create_feature(product, f"brand_{slugify(product.brand.name)}", 1.0)
            
            # Brand popularity
            brand_count = product.brand.products.count()
            max_brand_count = Brand.objects.annotate(
                product_count=Count('products')
            ).aggregate(max_count=Avg('product_count'))['max_count'] or 1
            
            brand_popularity = brand_count / max_brand_count
            self._create_feature(product, "brand_popularity", brand_popularity)
        else:
            self._create_feature(product, "brand_unknown", 1.0)
            self._create_feature(product, "brand_popularity", 0.0)
    
    def _extract_popularity_features(self, product):
        """Extract popularity-related features"""
        # Trending status
        self._create_feature(product, "is_trending", 1.0 if product.is_trending else 0.0)
        
        # Newest status
        self._create_feature(product, "is_newest", 1.0 if product.newest_product else 0.0)
        
        # Gender features
        self._create_feature(product, "is_men", 1.0 if product.is_men else 0.0)
        self._create_feature(product, "is_women", 1.0 if product.is_women else 0.0)
        
        # Variant features
        color_count = product.color_variant.count()
        size_count = product.size_variant.count()
        
        self._create_feature(product, "color_variants", min(color_count / 10, 1.0))
        self._create_feature(product, "size_variants", min(size_count / 10, 1.0))
    
    def _extract_review_features(self, product):
        """Extract review-related features"""
        reviews = product.reviews.all()
        
        if reviews.exists():
            # Average rating
            avg_rating = reviews.aggregate(avg_rating=Avg('stars'))['avg_rating'] or 0
            self._create_feature(product, "avg_rating", avg_rating / 5.0)
            
            # Review count
            review_count = reviews.count()
            max_reviews = Product.objects.annotate(
                review_count=Count('reviews')
            ).aggregate(max_reviews=Avg('review_count'))['max_reviews'] or 1
            
            review_popularity = min(review_count / max_reviews, 1.0)
            self._create_feature(product, "review_popularity", review_popularity)
            
            # Review sentiment
            positive_reviews = reviews.filter(stars__gte=4).count()
            negative_reviews = reviews.filter(stars__lte=2).count()
            
            if review_count > 0:
                positive_ratio = positive_reviews / review_count
                negative_ratio = negative_reviews / review_count
                
                self._create_feature(product, "positive_review_ratio", positive_ratio)
                self._create_feature(product, "negative_review_ratio", negative_ratio)
        else:
            self._create_feature(product, "avg_rating", 0.0)
            self._create_feature(product, "review_popularity", 0.0)
            self._create_feature(product, "positive_review_ratio", 0.0)
            self._create_feature(product, "negative_review_ratio", 0.0)
    
    def _extract_behavior_features(self, product):
        """Extract user behavior-related features"""
        behaviors = UserBehavior.objects.filter(product=product)
        
        if behaviors.exists():
            # Behavior counts by type
            behavior_types = ['view', 'cart_add', 'purchase', 'wishlist', 'review']
            
            for behavior_type in behavior_types:
                count = behaviors.filter(behavior_type=behavior_type).count()
                max_count = UserBehavior.objects.filter(
                    behavior_type=behavior_type
                ).values('product').annotate(
                    count=Count('uid')
                ).aggregate(max_count=Avg('count'))['max_count'] or 1
                
                popularity = min(count / max_count, 1.0)
                self._create_feature(product, f"behavior_{behavior_type}", popularity)
            
            # Total behavior popularity
            total_behaviors = behaviors.count()
            max_total = UserBehavior.objects.values('product').annotate(
                total=Count('uid')
            ).aggregate(max_total=Avg('total'))['max_total'] or 1
            
            total_popularity = min(total_behaviors / max_total, 1.0)
            self._create_feature(product, "total_behavior_popularity", total_popularity)
        else:
            # No behaviors yet
            for behavior_type in ['view', 'cart_add', 'purchase', 'wishlist', 'review']:
                self._create_feature(product, f"behavior_{behavior_type}", 0.0)
            self._create_feature(product, "total_behavior_popularity", 0.0)
    
    def _extract_temporal_features(self, product):
        """Extract time-related features"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        # Age of product
        age_days = (now - product.created_at).days
        age_score = max(0, 1 - (age_days / 365))  # Newer products get higher score
        self._create_feature(product, "product_age", age_score)
        
        # Seasonal features (basic implementation)
        month = now.month
        if month in [12, 1, 2]:  # Winter
            self._create_feature(product, "seasonal_winter", 1.0)
        elif month in [3, 4, 5]:  # Spring
            self._create_feature(product, "seasonal_spring", 1.0)
        elif month in [6, 7, 8]:  # Summer
            self._create_feature(product, "seasonal_summer", 1.0)
        else:  # Fall
            self._create_feature(product, "seasonal_fall", 1.0)
    
    def _create_feature(self, product, feature_name, feature_value):
        """Create a product feature"""
        try:
            ProductFeature.objects.create(
                product=product,
                feature_name=feature_name,
                feature_value=feature_value
            )
        except Exception as e:
            print(f"Error creating feature {feature_name} for product {product.product_name}: {e}")


class FeatureVectorBuilder:
    """Build feature vectors for similarity calculations"""
    
    def __init__(self):
        self.feature_extractor = ProductFeatureExtractor()
    
    def build_product_feature_vector(self, product):
        """
        Build a comprehensive feature vector for a product
        """
        features = product.features.all()
        feature_dict = {}
        
        for feature in features:
            feature_dict[feature.feature_name] = feature.feature_value
        
        return feature_dict
    
    def build_user_preference_vector(self, user):
        """
        Build a preference vector for a user based on their behavior
        """
        from .models import UserPreference, UserBehavior
        
        preference_vector = {}
        
        # Get user preferences
        preferences = UserPreference.objects.filter(user=user)
        for pref in preferences:
            category_key = f"pref_category_{slugify(pref.category.category_name)}"
            preference_vector[category_key] = pref.weight
            
            if pref.brand:
                brand_key = f"pref_brand_{slugify(pref.brand.name)}"
                preference_vector[brand_key] = pref.weight
        
        # Get user behavior patterns
        behaviors = UserBehavior.objects.filter(user=user)
        if behaviors.exists():
            # Analyze behavior patterns
            behavior_analysis = self._analyze_user_behavior(behaviors)
            preference_vector.update(behavior_analysis)
        
        return preference_vector
    
    def _analyze_user_behavior(self, behaviors):
        """
        Analyze user behavior to extract preference patterns
        """
        analysis = {}
        
        # Price preference
        prices = [behavior.product.price for behavior in behaviors]
        if prices:
            avg_price = sum(prices) / len(prices)
            price_range = max(prices) - min(prices)
            
            analysis['pref_avg_price'] = avg_price / 10000  # Normalize
            analysis['pref_price_range'] = price_range / 10000  # Normalize
        
        # Category preference
        category_counts = {}
        for behavior in behaviors:
            category = behavior.product.category.category_name
            category_counts[category] = category_counts.get(category, 0) + 1
        
        for category, count in category_counts.items():
            category_key = f"pref_category_{slugify(category)}"
            analysis[category_key] = count / len(behaviors)
        
        # Brand preference
        brand_counts = {}
        for behavior in behaviors:
            if behavior.product.brand:
                brand = behavior.product.brand.name
                brand_counts[brand] = brand_counts.get(brand, 0) + 1
        
        for brand, count in brand_counts.items():
            brand_key = f"pref_brand_{slugify(brand)}"
            analysis[brand_key] = count / len(behaviors)
        
        # Behavior type preference
        behavior_counts = {}
        for behavior in behaviors:
            behavior_counts[behavior.behavior_type] = behavior_counts.get(behavior.behavior_type, 0) + 1
        
        for behavior_type, count in behavior_counts.items():
            behavior_key = f"pref_behavior_{behavior_type}"
            analysis[behavior_key] = count / len(behaviors)
        
        return analysis


class ContentBasedRecommender:
    """Content-based recommendation engine"""
    
    def __init__(self):
        self.feature_extractor = ProductFeatureExtractor()
        self.vector_builder = FeatureVectorBuilder()
    
    def get_content_based_recommendations(self, user, limit=10):
        """
        Get content-based recommendations for a user
        """
        try:
            # Build user preference vector
            user_preferences = self.vector_builder.build_user_preference_vector(user)
            
            if not user_preferences:
                return self._get_popular_products(limit)
            
            # Get all products
            products = Product.objects.all()
            
            # Calculate similarity scores
            product_scores = []
            
            for product in products:
                # Skip if user already has this product
                if self._user_has_product(user, product):
                    continue
                
                # Build product feature vector
                product_features = self.vector_builder.build_product_feature_vector(product)
                
                # Calculate similarity
                similarity_score = self._calculate_similarity(user_preferences, product_features)
                
                if similarity_score > 0.1:  # Only include meaningful matches
                    product_scores.append((product, similarity_score))
            
            # Sort by similarity score
            product_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return top recommendations
            recommended_products = [product for product, score in product_scores[:limit]]
            
            return recommended_products
            
        except Exception as e:
            print(f"Error in content-based recommendations: {e}")
            return self._get_popular_products(limit)
    
    def _calculate_similarity(self, user_preferences, product_features):
        """
        Calculate similarity between user preferences and product features
        """
        if not user_preferences or not product_features:
            return 0.0
        
        # Get common features
        common_features = set(user_preferences.keys()) & set(product_features.keys())
        
        if not common_features:
            return 0.0
        
        # Calculate cosine similarity
        numerator = 0.0
        user_norm = 0.0
        product_norm = 0.0
        
        for feature in common_features:
            user_val = user_preferences[feature]
            product_val = product_features[feature]
            
            numerator += user_val * product_val
            user_norm += user_val ** 2
            product_norm += product_val ** 2
        
        # Calculate norms
        user_norm = user_norm ** 0.5
        product_norm = product_norm ** 0.5
        
        if user_norm == 0 or product_norm == 0:
            return 0.0
        
        similarity = numerator / (user_norm * product_norm)
        return similarity
    
    def _user_has_product(self, user, product):
        """
        Check if user already has the product
        """
        return UserBehavior.objects.filter(
            user=user,
            product=product,
            behavior_type__in=['purchase', 'cart_add', 'wishlist']
        ).exists()
    
    def _get_popular_products(self, limit=10):
        """
        Get popular products as fallback
        """
        return Product.objects.filter(is_trending=True).order_by('-created_at')[:limit] 