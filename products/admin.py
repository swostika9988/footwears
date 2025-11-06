from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import *

# Register your models here.

# ============================================================================
# CORE PRODUCT MODELS
# ============================================================================

admin.site.register(Category)
admin.site.register(Coupon)

class ProductImageAdmin(admin.StackedInline):
    model = ProductImage

class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'price', 'category', 'brand', 'is_trending', 'newest_product', 'is_men', 'is_women', 'get_rating_display']
    list_filter = ['category', 'brand', 'is_trending', 'newest_product', 'is_men', 'is_women', 'created_at']
    search_fields = ['product_name', 'product_desription']
    list_editable = ['is_trending', 'newest_product', 'is_men', 'is_women']
    inlines = [ProductImageAdmin]
    
    def get_rating_display(self, obj):
        rating = obj.get_rating()
        if rating > 0:
            formatted_rating = "{:.1f}".format(rating)  # format the float first
            return format_html('<span style="color: green;">★ {}</span>', formatted_rating)
        return format_html('<span style="color: gray;">No ratings</span>')

    get_rating_display.short_description = 'Rating'

@admin.register(ColorVariant)
class ColorVariantAdmin(admin.ModelAdmin):
    list_display = ['color_name', 'price']
    search_fields = ['color_name']

@admin.register(SizeVariant)
class SizeVariantAdmin(admin.ModelAdmin):
    list_display = ['size_name', 'price', 'order']
    list_editable = ['price', 'order']
    ordering = ['order']

admin.site.register(ProductImage)
admin.site.register(Product, ProductAdmin)

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_product_count']
    search_fields = ['name']
    
    def get_product_count(self, obj):
        return obj.products.count()
    get_product_count.short_description = 'Products'

# ============================================================================
# AI SYSTEM MODELS - USER BEHAVIOR & PREFERENCES
# ============================================================================

@admin.register(UserBehavior)
class UserBehaviorAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'behavior_type', 'weight', 'timestamp', 'get_days_ago']
    list_filter = ['behavior_type', 'timestamp', 'weight']
    search_fields = ['user__username', 'user__email', 'product__product_name']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    
    def get_days_ago(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.timestamp
        return f"{delta.days} days ago"
    get_days_ago.short_description = 'Days Ago'

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'brand', 'price_range_min', 'price_range_max', 'weight', 'last_updated']
    list_filter = ['category', 'brand', 'last_updated']
    search_fields = ['user__username', 'user__email', 'category__category_name', 'brand__name']
    readonly_fields = ['last_updated']

@admin.register(ProductFeature)
class ProductFeatureAdmin(admin.ModelAdmin):
    list_display = ['product', 'feature_name', 'feature_value', 'get_feature_strength']
    list_filter = ['feature_name', 'feature_value']
    search_fields = ['product__product_name', 'feature_name']
    
    def get_feature_strength(self, obj):
        if obj.feature_value >= 0.8:
            color = 'green'
        elif obj.feature_value >= 0.5:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {};">{:.2f}</span>', color, obj.feature_value)
    get_feature_strength.short_description = 'Strength'

# ============================================================================
# COLLABORATIVE FILTERING MODELS
# ============================================================================

@admin.register(UserSimilarity)
class UserSimilarityAdmin(admin.ModelAdmin):
    list_display = ['user1', 'user2', 'similarity_score', 'last_calculated', 'get_similarity_color']
    list_filter = ['similarity_score', 'last_calculated']
    search_fields = ['user1__username', 'user2__username']
    readonly_fields = ['last_calculated']
    
    def get_similarity_color(self, obj):
        if obj.similarity_score >= 0.7:
            color = 'green'
        elif obj.similarity_score >= 0.4:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {};">{:.3f}</span>', color, obj.similarity_score)
    get_similarity_color.short_description = 'Similarity'

@admin.register(ProductSimilarity)
class ProductSimilarityAdmin(admin.ModelAdmin):
    list_display = ['product1', 'product2', 'similarity_score', 'last_calculated', 'get_similarity_color']
    list_filter = ['similarity_score', 'last_calculated']
    search_fields = ['product1__product_name', 'product2__product_name']
    readonly_fields = ['last_calculated']
    
    def get_similarity_color(self, obj):
        if obj.similarity_score >= 0.7:
            color = 'green'
        elif obj.similarity_score >= 0.4:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {};">{:.3f}</span>', color, obj.similarity_score)
    get_similarity_color.short_description = 'Similarity'

@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'confidence', 'last_updated', 'get_rating_color']
    list_filter = ['rating', 'confidence', 'last_updated']
    search_fields = ['user__username', 'product__product_name']
    readonly_fields = ['last_updated']
    
    def get_rating_color(self, obj):
        if obj.rating >= 4.0:
            color = 'green'
        elif obj.rating >= 3.0:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {};">{:.2f}</span>', color, obj.rating)
    get_rating_color.short_description = 'Rating'

# ============================================================================
# SENTIMENT ANALYSIS MODELS
# ============================================================================

@admin.register(SentimentAnalysis)
class SentimentAnalysisAdmin(admin.ModelAdmin):
    list_display = ['review', 'overall_sentiment', 'sentiment_score', 'confidence', 'processed_at', 'get_sentiment_color']
    list_filter = ['overall_sentiment', 'confidence', 'processed_at']
    search_fields = ['review__product__product_name', 'review__user__username']
    readonly_fields = ['processed_at']
    
    def get_sentiment_color(self, obj):
        if obj.overall_sentiment == 'positive':
            color = 'green'
        elif obj.overall_sentiment == 'negative':
            color = 'red'
        else:
            color = 'gray'
        return format_html('<span style="color: {};">{}</span>', color, obj.overall_sentiment.title())
    get_sentiment_color.short_description = 'Sentiment'

@admin.register(AspectSentiment)
class AspectSentimentAdmin(admin.ModelAdmin):
    list_display = ['review', 'aspect', 'sentiment', 'sentiment_score', 'confidence', 'get_sentiment_color']
    list_filter = ['aspect', 'sentiment', 'confidence']
    search_fields = ['review__product__product_name', 'review__user__username', 'aspect']
    
    def get_sentiment_color(self, obj):
        if obj.sentiment == 'positive':
            color = 'green'
        elif obj.sentiment == 'negative':
            color = 'red'
        else:
            color = 'gray'
        return format_html('<span style="color: {};">{}</span>', color, obj.sentiment.title())
    get_sentiment_color.short_description = 'Sentiment'

@admin.register(SentimentTrend)
class SentimentTrendAdmin(admin.ModelAdmin):
    list_display = ['product', 'date', 'total_reviews', 'positive_count', 'negative_count', 'neutral_count', 'average_sentiment', 'get_trend_color']
    list_filter = ['date', 'average_sentiment']
    search_fields = ['product__product_name']
    date_hierarchy = 'date'
    
    def get_trend_color(self, obj):
        if obj.average_sentiment >= 0.5:
            color = 'green'
        elif obj.average_sentiment >= 0.0:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {};">{:.2f}</span>', color, obj.average_sentiment)
    get_trend_color.short_description = 'Avg Sentiment'

# ============================================================================
# HASHING MODELS (FOR FUTURE PHASE 5)
# ============================================================================

@admin.register(ProductHash)
class ProductHashAdmin(admin.ModelAdmin):
    list_display = ['product', 'hash_type', 'hash_value', 'created_at']
    list_filter = ['hash_type', 'created_at']
    search_fields = ['product__product_name', 'hash_value']
    readonly_fields = ['created_at']

@admin.register(HashBucket)
class HashBucketAdmin(admin.ModelAdmin):
    list_display = ['bucket_id', 'hash_type', 'get_product_count', 'created_at']
    list_filter = ['hash_type', 'created_at']
    search_fields = ['bucket_id']
    readonly_fields = ['created_at']
    
    def get_product_count(self, obj):
        return obj.products.count()
    get_product_count.short_description = 'Products'

@admin.register(ProductHashBucket)
class ProductHashBucketAdmin(admin.ModelAdmin):
    list_display = ['product', 'bucket', 'hash_distance']
    list_filter = ['bucket__hash_type', 'hash_distance']
    search_fields = ['product__product_name', 'bucket__bucket_id']

# ============================================================================
# REVIEW MODELS
# ============================================================================

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'stars', 'get_stars_display', 'date_added', 'get_like_dislike_count']
    list_filter = ['stars', 'date_added']
    search_fields = ['product__product_name', 'user__username', 'content']
    readonly_fields = ['date_added']
    
    def get_stars_display(self, obj):
        return '★' * obj.stars
    get_stars_display.short_description = 'Stars'
    
    def get_like_dislike_count(self, obj):
        return f"👍 {obj.likes.count()} 👎 {obj.dislikes.count()}"
    get_like_dislike_count.short_description = 'Likes/Dislikes'

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'size_variant', 'added_on']
    list_filter = ['added_on', 'size_variant']
    search_fields = ['user__username', 'product__product_name']
    readonly_fields = ['added_on']

# ============================================================================
# ADMIN SITE CONFIGURATION
# ============================================================================

# Customize admin site
admin.site.site_header = "Footwear E-commerce AI Admin"
admin.site.site_title = "Footwear AI Admin"
admin.site.index_title = "AI-Powered E-commerce Management"

# All models are already registered with their respective admin classes above