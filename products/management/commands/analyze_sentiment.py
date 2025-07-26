"""
Django management command to analyze sentiment
Usage: python manage.py analyze_sentiment
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from products.sentiment_analyzer import SentimentService


class Command(BaseCommand):
    help = 'Analyze sentiment for products and reviews'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation of all sentiment analysis',
        )
        parser.add_argument(
            '--product-id',
            type=str,
            help='Analyze sentiment for a specific product by ID',
        )
        parser.add_argument(
            '--trends',
            action='store_true',
            help='Analyze sentiment trends',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days for trend analysis (default: 30)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting sentiment analysis...')
        )

        sentiment_service = SentimentService()

        try:
            if options['product_id']:
                # Analyze sentiment for a specific product
                from products.models import Product
                try:
                    product = Product.objects.get(uid=options['product_id'])
                    self.stdout.write(f'Analyzing sentiment for product: {product.product_name}')
                    
                    # Analyze sentiment
                    sentiment_service.analyze_product_sentiment(
                        product, 
                        force_recalculate=options['force']
                    )
                    
                    # Get sentiment summary
                    summary = sentiment_service.get_product_sentiment(product)
                    if summary:
                        self._display_sentiment_summary(summary, product.product_name)
                    
                    # Analyze trends if requested
                    if options['trends']:
                        self.stdout.write('Analyzing sentiment trends...')
                        trend_data = sentiment_service.analyze_sentiment_trends(
                            product, 
                            options['days']
                        )
                        if trend_data:
                            self._display_trend_data(trend_data)
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Sentiment analysis completed for {product.product_name}')
                    )
                except Product.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'Product with ID {options["product_id"]} not found')
                    )
            else:
                # Analyze sentiment for all products
                self.stdout.write('Analyzing sentiment for all products...')
                sentiment_service.analyze_all_products_sentiment(
                    force_recalculate=options['force']
                )
                
                # Get top sentiment products
                self.stdout.write('\nTop positive sentiment products:')
                positive_products = sentiment_service.get_top_sentiment_products('positive', 5)
                for product in positive_products:
                    summary = sentiment_service.get_product_sentiment(product)
                    if summary:
                        self.stdout.write(f'  - {product.product_name}: {summary["sentiment_score"]:.3f}')
                
                self.stdout.write('\nTop negative sentiment products:')
                negative_products = sentiment_service.get_top_sentiment_products('negative', 5)
                for product in negative_products:
                    summary = sentiment_service.get_product_sentiment(product)
                    if summary:
                        self.stdout.write(f'  - {product.product_name}: {summary["sentiment_score"]:.3f}')
                
                self.stdout.write(
                    self.style.SUCCESS('Sentiment analysis completed successfully!')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during sentiment analysis: {e}')
            )
    
    def _display_sentiment_summary(self, summary, product_name):
        """Display sentiment summary for a product"""
        self.stdout.write(f'\nSentiment Summary for {product_name}:')
        self.stdout.write(f'Overall Sentiment: {summary["overall_sentiment"]}')
        self.stdout.write(f'Sentiment Score: {summary["sentiment_score"]:.3f}')
        self.stdout.write(f'Confidence: {summary["confidence_score"]:.3f}')
        
        stats = summary['review_stats']
        self.stdout.write(f'Total Reviews: {stats["total"]}')
        self.stdout.write(f'Positive Reviews: {stats["positive"]}')
        self.stdout.write(f'Negative Reviews: {stats["negative"]}')
        self.stdout.write(f'Neutral Reviews: {stats["neutral"]}')
        
        if summary['aspects']:
            self.stdout.write('\nAspect Sentiments:')
            for aspect, data in summary['aspects'].items():
                if data['total_mentions'] > 0:
                    self.stdout.write(f'  - {aspect}: {data["sentiment_score"]:.3f} ({data["total_mentions"]} mentions)')
        
        self.stdout.write('')
    
    def _display_trend_data(self, trend_data):
        """Display trend analysis data"""
        self.stdout.write(f'\nSentiment Trend Analysis:')
        self.stdout.write(f'Direction: {trend_data["direction"]}')
        self.stdout.write(f'Strength: {trend_data["strength"]:.3f}')
        self.stdout.write(f'Average Sentiment: {trend_data["average_sentiment"]:.3f}')
        self.stdout.write(f'Volatility: {trend_data["volatility"]:.3f}')
        self.stdout.write('') 