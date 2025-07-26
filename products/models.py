from django.db import models
from base.models import BaseModel
from django.utils.text import slugify
from django.utils.html import mark_safe
from django.contrib.auth.models import User

# ------------------------------
# New Brand model added here
# ------------------------------
class Brand(BaseModel):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)

    def __str__(self):
        return self.name

# ------------------------------

class Category(BaseModel):
    category_name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, null=True, blank=True)
    category_image = models.ImageField(upload_to="categories")

    def save(self, *args, **kwargs):
        self.slug = slugify(self.category_name)
        super(Category, self).save(*args, **kwargs)

    def __str__(self):
        return self.category_name


class ColorVariant(BaseModel):
    color_name = models.CharField(max_length=100)
    price = models.IntegerField(default=0)

    def __str__(self):
        return self.color_name


class SizeVariant(BaseModel):
    size_name = models.CharField(max_length=100)
    price = models.IntegerField(default=0)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.size_name


class Product(BaseModel):
    parent = models.ForeignKey('self', related_name='variants', on_delete=models.CASCADE, blank=True, null=True)
    product_name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")  # Added
    price = models.IntegerField()
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_desription = models.TextField()
    color_variant = models.ManyToManyField(ColorVariant, blank=True)
    size_variant = models.ManyToManyField(SizeVariant, blank=True)
    newest_product = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    # New fields
    is_men = models.BooleanField(default=False)
    is_women = models.BooleanField(default=False)

    @property
    def discount_percent(self):
        if self.price and self.discounted_price:
            return round(100 * (self.price - self.discounted_price) / self.price)
        return 0

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.product_name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return self.product_name

    def get_product_price_by_size(self, size):
        return self.price + SizeVariant.objects.get(size_name=size).price

    def get_rating(self):
        total = sum(int(review['stars']) for review in self.reviews.values())
        return total / self.reviews.count() if self.reviews.count() > 0 else 0


class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_images')
    image = models.ImageField(upload_to='product')

    def img_preview(self):
        return mark_safe(f'<img src="{self.image.url}" width="500"/>')


class Coupon(BaseModel):
    coupon_code = models.CharField(max_length=10)
    is_expired = models.BooleanField(default=False)
    discount_amount = models.IntegerField(default=100)
    minimum_amount = models.IntegerField(default=500)


class ProductReview(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    stars = models.IntegerField(default=3, choices=[(i, i) for i in range(1, 6)])
    content = models.TextField(blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name="liked_reviews", blank=True)
    dislikes = models.ManyToManyField(User, related_name="disliked_reviews", blank=True)

    def like_count(self):
        return self.likes.count()

    def dislike_count(self):
        return self.dislikes.count()


class Wishlist(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")
    size_variant = models.ForeignKey(SizeVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name="wishlist_items")
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'size_variant')

    def __str__(self):
        return f'{self.user.username} - {self.product.product_name} - {self.size_variant.size_name if self.size_variant else "No Size"}'


# ============================================================================
# RECOMMENDATION SYSTEM MODELS
# ============================================================================

class UserPreference(BaseModel):
    """Track user preferences for content-based filtering"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='preferences')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True)
    price_range_min = models.IntegerField(default=0)
    price_range_max = models.IntegerField(default=10000)
    weight = models.FloatField(default=1.0)  # Preference strength
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'category', 'brand')

    def __str__(self):
        return f'{self.user.username} - {self.category.category_name}'


class ProductFeature(BaseModel):
    """Extract and store product features for content-based filtering"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='features')
    feature_name = models.CharField(max_length=100)  # e.g., "sporty", "casual", "formal"
    feature_value = models.FloatField(default=0.0)  # Feature strength (0-1)
    
    class Meta:
        unique_together = ('product', 'feature_name')

    def __str__(self):
        return f'{self.product.product_name} - {self.feature_name}: {self.feature_value}'


class UserBehavior(BaseModel):
    """Track user behavior for collaborative filtering"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='behaviors')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='user_behaviors')
    behavior_type = models.CharField(max_length=20, choices=[
        ('view', 'Product View'),
        ('cart_add', 'Added to Cart'),
        ('purchase', 'Purchased'),
        ('wishlist', 'Added to Wishlist'),
        ('review', 'Reviewed'),
    ])
    timestamp = models.DateTimeField(auto_now_add=True)
    weight = models.FloatField(default=1.0)  # Behavior importance

    class Meta:
        unique_together = ('user', 'product', 'behavior_type')

    def __str__(self):
        return f'{self.user.username} - {self.product.product_name} - {self.behavior_type}'


class UserSimilarity(BaseModel):
    """Store user similarity scores for collaborative filtering"""
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='similarities_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='similarities_as_user2')
    similarity_score = models.FloatField(default=0.0)
    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user1', 'user2')

    def __str__(self):
        return f'{self.user1.username} ~ {self.user2.username}: {self.similarity_score:.3f}'


class ProductSimilarity(BaseModel):
    """Store product similarity scores for collaborative filtering"""
    product1 = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='similarities_as_product1')
    product2 = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='similarities_as_product2')
    similarity_score = models.FloatField(default=0.0)
    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product1', 'product2')

    def __str__(self):
        return f'{self.product1.product_name} ~ {self.product2.product_name}: {self.similarity_score:.3f}'


class UserRating(BaseModel):
    """Calculated user ratings for collaborative filtering"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calculated_ratings')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='user_ratings')
    rating = models.FloatField(default=0.0)  # Calculated from reviews, purchases, etc.
    confidence = models.FloatField(default=0.0)  # How confident we are in this rating
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f'{self.user.username} -> {self.product.product_name}: {self.rating:.2f}'


class ProductHash(BaseModel):
    """Store product hashes for efficient similarity search"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='hashes')
    hash_type = models.CharField(max_length=20, choices=[
        ('content', 'Content Hash'),
        ('feature', 'Feature Hash'),
        ('image', 'Image Hash'),
    ])
    hash_value = models.CharField(max_length=255)
    hash_metadata = models.JSONField(default=dict)  # Additional hash info
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'hash_type')

    def __str__(self):
        return f'{self.product.product_name} - {self.hash_type}'


class HashBucket(BaseModel):
    """Group similar products using hash buckets for fast retrieval"""
    bucket_id = models.CharField(max_length=100)
    hash_type = models.CharField(max_length=20)
    products = models.ManyToManyField(Product, through='ProductHashBucket')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Bucket {self.bucket_id} ({self.hash_type})'


class ProductHashBucket(BaseModel):
    """Many-to-many relationship between products and hash buckets"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    bucket = models.ForeignKey(HashBucket, on_delete=models.CASCADE)
    hash_distance = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('product', 'bucket')

    def __str__(self):
        return f'{self.product.product_name} in {self.bucket.bucket_id}'


class SentimentAnalysis(BaseModel):
    """Store sentiment analysis results for product reviews"""
    review = models.OneToOneField(ProductReview, on_delete=models.CASCADE, related_name='sentiment')
    overall_sentiment = models.CharField(max_length=10, choices=[
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ])
    sentiment_score = models.FloatField(default=0.0)  # -1 to 1
    confidence = models.FloatField(default=0.0)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.review.product.product_name} - {self.overall_sentiment}'


class AspectSentiment(BaseModel):
    """Store aspect-based sentiment analysis"""
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name='aspect_sentiments')
    aspect = models.CharField(max_length=50)  # e.g., "comfort", "style", "durability"
    sentiment = models.CharField(max_length=10, choices=[
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ])
    sentiment_score = models.FloatField(default=0.0)
    confidence = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('review', 'aspect')

    def __str__(self):
        return f'{self.review.product.product_name} - {self.aspect}: {self.sentiment}'


class SentimentTrend(BaseModel):
    """Track sentiment trends over time"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sentiment_trends')
    date = models.DateField()
    positive_count = models.IntegerField(default=0)
    negative_count = models.IntegerField(default=0)
    neutral_count = models.IntegerField(default=0)
    average_sentiment = models.FloatField(default=0.0)
    total_reviews = models.IntegerField(default=0)

    class Meta:
        unique_together = ('product', 'date')

    def __str__(self):
        return f'{self.product.product_name} - {self.date}: {self.average_sentiment:.2f}'
