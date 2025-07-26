"""
Django management command to setup demo data and AI systems
Usage: python manage.py setup_demo
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User
from products.models import Product, Category, Brand, ProductReview, UserBehavior
from accounts.models import Cart, CartItem
import random


class Command(BaseCommand):
    help = 'Setup demo data and AI systems for presentation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of all data',
        )
        parser.add_argument(
            '--skip-data',
            action='store_true',
            help='Skip data creation, only run AI setup',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Demo Setup...')
        )

        if not options['skip_data']:
            self.stdout.write('Creating demo data...')
            self.create_demo_data(options['force'])

        self.stdout.write('Setting up AI systems...')
        self.setup_ai_systems()

        self.stdout.write('Demo setup completed successfully!')
        self.show_summary()

    def create_demo_data(self, force=False):
        """Create demo data for the platform"""
        
        # Create categories
        categories = ['Men', 'Women', 'Kids', 'Sports', 'Casual', 'Formal', 'Outdoor']
        for cat_name in categories:
            Category.objects.get_or_create(category_name=cat_name)
        
        # Create brands
        brands = [
            'Nike', 'Adidas', 'Puma', 'Reebok', 'New Balance', 'Converse', 
            'Vans', 'Crocs', 'Bata', 'Woodland', 'Sparx', 'Liberty'
        ]
        for brand_name in brands:
            Brand.objects.get_or_create(name=brand_name)

        # Create users if needed
        if User.objects.count() < 20:
            for i in range(20):
                User.objects.get_or_create(
                    username=f'demo_user_{i}',
                    email=f'demo_user_{i}@example.com',
                    defaults={'password': 'demo123456'}
                )

        # Create reviews for products
        products = Product.objects.all()
        users = User.objects.all()

        if products.exists() and users.exists():
            # Clear existing reviews if force
            if force:
                ProductReview.objects.all().delete()
                UserBehavior.objects.all().delete()

            # Create reviews
            review_templates = {
                5: [
                    "Excellent product! Very comfortable and stylish. Perfect fit and great quality.",
                    "Amazing shoes! Super comfortable for long walks. Highly recommended!",
                    "Fantastic product! Great design and very durable. Worth every penny.",
                    "Outstanding quality! Very comfortable and looks great. Perfect for daily use."
                ],
                4: [
                    "Good product! Comfortable and stylish. Minor issues but overall satisfied.",
                    "Nice shoes! Comfortable for most activities. Good value for money.",
                    "Pretty good product. Comfort is decent and design is appealing.",
                    "Satisfactory product. Good quality and reasonable comfort."
                ],
                3: [
                    "Okay product. Comfort is average, could be better for the price.",
                    "Decent shoes. Not bad but not exceptional either.",
                    "Average product. Comfort is acceptable but nothing special.",
                    "Fair product. Meets basic expectations but could improve."
                ],
                2: [
                    "Disappointing product. Comfort is poor and quality is below average.",
                    "Not satisfied with this purchase. Comfort issues and poor quality.",
                    "Below expectations. Uncomfortable and not worth the price.",
                    "Poor product. Quality issues and uncomfortable fit."
                ],
                1: [
                    "Terrible product! Very uncomfortable and poor quality. Waste of money.",
                    "Awful shoes! Extremely uncomfortable and falls apart quickly.",
                    "Worst purchase ever! Poor quality and very uncomfortable.",
                    "Horrible product! Uncomfortable, poor quality, and overpriced."
                ]
            }

            for product in products:
                # Create 3-8 reviews per product
                for _ in range(random.randint(3, 8)):
                    user = random.choice(users)
                    stars = random.randint(1, 5)
                    review_text = random.choice(review_templates[stars])
                    
                    ProductReview.objects.get_or_create(
                        user=user,
                        product=product,
                        defaults={
                            'stars': stars,
                            'review_text': review_text
                        }
                    )

            # Create user behaviors
            behaviors = ['view', 'cart_add', 'purchase', 'wishlist', 'review']
            for user in users:
                # Each user interacts with 10-20 products
                user_products = random.sample(list(products), min(random.randint(10, 20), products.count()))
                
                for product in user_products:
                    # Create multiple behaviors per product
                    for behavior in random.sample(behaviors, random.randint(1, 3)):
                        UserBehavior.objects.get_or_create(
                            user=user,
                            product=product,
                            behavior_type=behavior,
                            defaults={'weight': random.uniform(0.5, 2.0)}
                        )

    def setup_ai_systems(self):
        """Setup AI systems and run analysis"""
        
        try:
            # Extract product features
            self.stdout.write('  Extracting product features...')
            call_command('extract_features', force=True)
            
            # Learn user preferences
            self.stdout.write('  Learning user preferences...')
            call_command('learn_preferences', force=True)
            
            # Update collaborative filtering
            self.stdout.write('  Updating collaborative filtering...')
            call_command('update_collaborative_filtering', force=True)
            
            # Analyze sentiment
            self.stdout.write('  Analyzing sentiment...')
            call_command('analyze_sentiment', force=True)
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Some AI setup steps failed: {e}')
            )

    def show_summary(self):
        """Show summary of created data"""
        
        from products.models import SentclimentAnalysis, AspectSentiment, SentimentTrend, UserSimilarity, ProductSimilarity
        
        self.stdout.write('\nDemo Data Summary:')
        self.stdout.write(f'  Users: {User.objects.count()}')
        self.stdout.write(f'  Products: {Product.objects.count()}')
        self.stdout.write(f'  Reviews: {ProductReview.objects.count()}')
        self.stdout.write(f'  User Behaviors: {UserBehavior.objects.count()}')
        self.stdout.write(f'  Sentiment Analysis: {SentimentAnalysis.objects.count()}')
        self.stdout.write(f'  Aspect Sentiments: {AspectSentiment.objects.count()}')
        self.stdout.write(f'  Sentiment Trends: {SentimentTrend.objects.count()}')
        self.stdout.write(f'  User Similarities: {UserSimilarity.objects.count()}')
        self.stdout.write(f'  Product Similarities: {ProductSimilarity.objects.count()}')
        
        self.stdout.write('\nDemo Features Available:')
        self.stdout.write('  Personalized Recommendations')
        self.stdout.write('  Sentiment Analysis')
        self.stdout.write('  Collaborative Filtering')
        self.stdout.write('  Content-Based Filtering')
        self.stdout.write('  User Behavior Tracking')
        self.stdout.write('  Aspect Analysis')
        self.stdout.write('  Sentiment Trends')
        
        self.stdout.write('\nReady for Demo!')
        self.stdout.write('  Start server: python manage.py runserver')
        self.stdout.write('  Login as: demo_user_0 (password: demo123456)')
        self.stdout.write('  Browse products to see AI features in action') 