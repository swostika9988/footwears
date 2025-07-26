"""
Django management command to check AI system status
Usage: python manage.py check_ai_status
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from products.models import (
    Product, ProductReview, UserBehavior, SentimentAnalysis, 
    AspectSentiment, SentimentTrend, UserSimilarity, ProductSimilarity,
    ProductFeature, UserPreference
)


class Command(BaseCommand):
    help = 'Check status of AI systems and data'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 AI System Status Check')
        )
        
        self.check_basic_data()
        self.check_ai_data()
        self.check_system_health()
        self.show_recommendations()

    def check_basic_data(self):
        """Check basic data requirements"""
        self.stdout.write('\n📊 Basic Data Status:')
        
        user_count = User.objects.count()
        product_count = Product.objects.count()
        review_count = ProductReview.objects.count()
        behavior_count = UserBehavior.objects.count()
        
        self.stdout.write(f'  👥 Users: {user_count}')
        self.stdout.write(f'  👟 Products: {product_count}')
        self.stdout.write(f'  📝 Reviews: {review_count}')
        self.stdout.write(f'  🎯 User Behaviors: {behavior_count}')
        
        # Check minimum requirements
        if user_count < 20:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  Need more users (minimum: 20, current: {user_count})')
            )
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ User count sufficient'))
            
        if product_count < 50:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  Need more products (minimum: 50, current: {product_count})')
            )
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ Product count sufficient'))
            
        if review_count < 200:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  Need more reviews (minimum: 200, current: {review_count})')
            )
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ Review count sufficient'))

    def check_ai_data(self):
        """Check AI-specific data"""
        self.stdout.write('\n🤖 AI Data Status:')
        
        feature_count = ProductFeature.objects.count()
        preference_count = UserPreference.objects.count()
        sentiment_count = SentimentAnalysis.objects.count()
        aspect_count = AspectSentiment.objects.count()
        trend_count = SentimentTrend.objects.count()
        user_sim_count = UserSimilarity.objects.count()
        product_sim_count = ProductSimilarity.objects.count()
        
        self.stdout.write(f'  🔍 Product Features: {feature_count}')
        self.stdout.write(f'  🧠 User Preferences: {preference_count}')
        self.stdout.write(f'  📊 Sentiment Analysis: {sentiment_count}')
        self.stdout.write(f'  🎯 Aspect Sentiments: {aspect_count}')
        self.stdout.write(f'  📈 Sentiment Trends: {trend_count}')
        self.stdout.write(f'  👤 User Similarities: {user_sim_count}')
        self.stdout.write(f'  🎯 Product Similarities: {product_sim_count}')
        
        # Check AI system readiness
        if feature_count == 0:
            self.stdout.write(
                self.style.ERROR('  ❌ Product features not extracted - Run: python manage.py extract_features')
            )
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ Product features ready'))
            
        if preference_count == 0:
            self.stdout.write(
                self.style.ERROR('  ❌ User preferences not learned - Run: python manage.py learn_preferences')
            )
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ User preferences ready'))
            
        if sentiment_count == 0:
            self.stdout.write(
                self.style.ERROR('  ❌ Sentiment analysis not performed - Run: python manage.py analyze_sentiment')
            )
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ Sentiment analysis ready'))

    def check_system_health(self):
        """Check system health and performance"""
        self.stdout.write('\n🏥 System Health:')
        
        # Check data distribution
        products_with_reviews = Product.objects.filter(reviews__isnull=False).distinct().count()
        products_with_sentiment = SentimentAnalysis.objects.count()
        users_with_behaviors = User.objects.filter(behaviors__isnull=False).distinct().count()
        
        review_coverage = (products_with_reviews / Product.objects.count() * 100) if Product.objects.count() > 0 else 0
        sentiment_coverage = (products_with_sentiment / Product.objects.count() * 100) if Product.objects.count() > 0 else 0
        behavior_coverage = (users_with_behaviors / User.objects.count() * 100) if User.objects.count() > 0 else 0
        
        self.stdout.write(f'  📝 Review Coverage: {review_coverage:.1f}%')
        self.stdout.write(f'  📊 Sentiment Coverage: {sentiment_coverage:.1f}%')
        self.stdout.write(f'  🎯 Behavior Coverage: {behavior_coverage:.1f}%')
        
        # Performance indicators
        avg_reviews_per_product = ProductReview.objects.count() / Product.objects.count() if Product.objects.count() > 0 else 0
        avg_behaviors_per_user = UserBehavior.objects.count() / User.objects.count() if User.objects.count() > 0 else 0
        
        self.stdout.write(f'  📊 Avg Reviews/Product: {avg_reviews_per_product:.1f}')
        self.stdout.write(f'  🎯 Avg Behaviors/User: {avg_behaviors_per_user:.1f}')

    def show_recommendations(self):
        """Show recommendations for improvement"""
        self.stdout.write('\n💡 Recommendations:')
        
        if User.objects.count() < 20:
            self.stdout.write('  🔧 Run: python manage.py setup_demo --force')
            
        if ProductFeature.objects.count() == 0:
            self.stdout.write('  🔧 Run: python manage.py extract_features --force')
            
        if UserPreference.objects.count() == 0:
            self.stdout.write('  🔧 Run: python manage.py learn_preferences --force')
            
        if SentimentAnalysis.objects.count() == 0:
            self.stdout.write('  🔧 Run: python manage.py analyze_sentiment --force')
            
        if UserSimilarity.objects.count() == 0:
            self.stdout.write('  🔧 Run: python manage.py update_collaborative_filtering --force')
        
        # Check if all systems are ready
        if (User.objects.count() >= 20 and ProductFeature.objects.count() > 0 and 
            UserPreference.objects.count() > 0 and SentimentAnalysis.objects.count() > 0):
            self.stdout.write(
                self.style.SUCCESS('\n🎉 All AI systems are ready for demo!')
            )
            self.stdout.write('  🚀 Start server: python manage.py runserver')
            self.stdout.write('  👤 Login as: demo_user_0 (password: demo123456)')
        else:
            self.stdout.write(
                self.style.WARNING('\n⚠️  Some AI systems need setup before demo')
            )
            self.stdout.write('  🔧 Run: python manage.py setup_demo --force') 