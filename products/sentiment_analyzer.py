"""
Advanced Sentiment Analysis System
Analyzes product reviews and user feedback for sentiment insights
"""

import re
import numpy as np
import pandas as pd
from textblob import TextBlob
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Count, Avg, Max, Min
from django.contrib.auth.models import User
from .models import (
    Product, ProductReview, SentimentAnalysis, AspectSentiment, 
    SentimentTrend, UserBehavior
)


class SentimentAnalyzer:
    """Advanced sentiment analysis for product reviews"""
    
    def __init__(self):
        # Define aspect categories for footwear
        self.aspects = {
            'comfort': ['comfort', 'comfortable', 'cushion', 'cushioned', 'soft', 'support', 'supportive'],
            'quality': ['quality', 'durable', 'durability', 'well-made', 'sturdy', 'solid', 'reliable'],
            'style': ['style', 'stylish', 'fashion', 'fashionable', 'look', 'appearance', 'design'],
            'fit': ['fit', 'fitting', 'size', 'sizing', 'tight', 'loose', 'perfect fit'],
            'price': ['price', 'expensive', 'cheap', 'affordable', 'value', 'worth', 'cost'],
            'material': ['material', 'leather', 'canvas', 'mesh', 'synthetic', 'fabric'],
            'performance': ['performance', 'performance', 'grip', 'traction', 'breathable', 'waterproof'],
            'brand': ['brand', 'nike', 'adidas', 'puma', 'reebok', 'brand quality'],
            'delivery': ['delivery', 'shipping', 'fast', 'slow', 'packaging', 'arrived'],
            'service': ['service', 'customer service', 'support', 'helpful', 'responsive']
        }
        
        # Sentiment words for aspect analysis
        self.positive_words = {
            'comfort': ['comfortable', 'soft', 'cushioned', 'supportive', 'cozy', 'pleasant'],
            'quality': ['excellent', 'great', 'good', 'durable', 'sturdy', 'reliable', 'solid'],
            'style': ['stylish', 'fashionable', 'beautiful', 'attractive', 'elegant', 'modern'],
            'fit': ['perfect', 'ideal', 'comfortable', 'well-fitting', 'snug', 'appropriate'],
            'price': ['affordable', 'reasonable', 'worth', 'value', 'cheap', 'inexpensive'],
            'material': ['premium', 'quality', 'durable', 'soft', 'breathable', 'comfortable'],
            'performance': ['excellent', 'great', 'effective', 'efficient', 'reliable', 'consistent'],
            'brand': ['trusted', 'reliable', 'quality', 'premium', 'famous', 'popular'],
            'delivery': ['fast', 'quick', 'efficient', 'on-time', 'prompt', 'reliable'],
            'service': ['helpful', 'responsive', 'friendly', 'professional', 'excellent', 'great']
        }
        
        self.negative_words = {
            'comfort': ['uncomfortable', 'hard', 'stiff', 'painful', 'rough', 'irritating'],
            'quality': ['poor', 'bad', 'cheap', 'flimsy', 'weak', 'unreliable', 'broken'],
            'style': ['ugly', 'unattractive', 'outdated', 'unfashionable', 'boring', 'plain'],
            'fit': ['loose', 'tight', 'uncomfortable', 'ill-fitting', 'wrong size', 'awkward'],
            'price': ['expensive', 'overpriced', 'costly', 'pricey', 'unaffordable', 'waste'],
            'material': ['cheap', 'poor', 'rough', 'uncomfortable', 'stiff', 'low-quality'],
            'performance': ['poor', 'bad', 'ineffective', 'unreliable', 'inconsistent', 'failing'],
            'brand': ['unreliable', 'poor', 'cheap', 'unknown', 'untrusted', 'bad'],
            'delivery': ['slow', 'late', 'delayed', 'poor', 'unreliable', 'problematic'],
            'service': ['unhelpful', 'unresponsive', 'rude', 'poor', 'bad', 'terrible']
        }
    
    def analyze_product_sentiment(self, product, force_recalculate=False):
        """
        Analyze sentiment for a specific product
        """
        try:
            # Check if analysis exists and is recent
            if not force_recalculate and self._sentiment_is_recent(product):
                return
            
            # Get all reviews for the product
            reviews = product.reviews.all()
            
            if not reviews.exists():
                return
            
            # Clear existing analysis
            SentimentAnalysis.objects.filter(review__product=product).delete()
            AspectSentiment.objects.filter(review__product=product).delete()
            
            # Analyze overall sentiment
            overall_sentiment = self._analyze_overall_sentiment(reviews)
            
            # Create overall sentiment record for each review
            for review in reviews:
                review_sentiment = self._analyze_single_review_sentiment(review)
                SentimentAnalysis.objects.get_or_create(
                    review=review,
                    defaults={
                        'overall_sentiment': review_sentiment['sentiment'],
                        'sentiment_score': review_sentiment['score'],
                        'confidence': review_sentiment['confidence']
                    }
                )
            
            # Analyze aspect-based sentiment for each review
            for review in reviews:
                aspect_sentiments = self._analyze_aspect_sentiments([review])
                for aspect, sentiment_data in aspect_sentiments.items():
                    AspectSentiment.objects.get_or_create(
                        review=review,
                        aspect=aspect,
                        defaults={
                            'sentiment': sentiment_data['sentiment'],
                            'sentiment_score': sentiment_data['score'],
                            'confidence': sentiment_data['confidence']
                        }
                    )
            
            # Update sentiment trends
            self._update_sentiment_trends(product)
            
            print(f"Sentiment analysis completed for product: {product.product_name}")
            
        except Exception as e:
            print(f"Error analyzing sentiment for product {product.product_name}: {e}")
    
    def analyze_all_products_sentiment(self, force_recalculate=False):
        """
        Analyze sentiment for all products with reviews
        """
        products = Product.objects.filter(reviews__isnull=False).distinct()
        
        for product in products:
            self.analyze_product_sentiment(product, force_recalculate)
        
        print(f"Sentiment analysis completed for {products.count()} products")
    
    def _sentiment_is_recent(self, product):
        """
        Check if sentiment analysis is recent (within 7 days)
        """
        recent_analysis = SentimentAnalysis.objects.filter(
            review__product=product,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).first()
        
        return recent_analysis is not None
    
    def _analyze_overall_sentiment(self, reviews):
        """
        Analyze overall sentiment from reviews
        """
        total_reviews = reviews.count()
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        total_score = 0
        
        for review in reviews:
            # Use TextBlob for sentiment analysis
            blob = TextBlob(review.content or '')
            sentiment_score = blob.sentiment.polarity
            
            total_score += sentiment_score
            
            # Categorize sentiment
            if sentiment_score > 0.1:
                positive_count += 1
            elif sentiment_score < -0.1:
                negative_count += 1
            else:
                neutral_count += 1
        
        # Calculate overall sentiment
        avg_score = total_score / total_reviews if total_reviews > 0 else 0
        
        if avg_score > 0.1:
            overall_sentiment = 'positive'
        elif avg_score < -0.1:
            overall_sentiment = 'negative'
        else:
            overall_sentiment = 'neutral'
        
        # Calculate confidence based on review count and consistency
        confidence = min(1.0, total_reviews / 10)  # More reviews = higher confidence
        
        return {
            'sentiment': overall_sentiment,
            'score': avg_score,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'total_count': total_reviews,
            'confidence': confidence
        }
    
    def _analyze_single_review_sentiment(self, review):
        """
        Analyze sentiment for a single review
        """
        blob = TextBlob(review.content or '')
        sentiment_score = blob.sentiment.polarity
        
        if sentiment_score > 0.1:
            sentiment = 'positive'
        elif sentiment_score < -0.1:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # Calculate confidence based on review length and subjectivity
        confidence = min(1.0, len(review.content or '') / 100)  # Longer reviews = higher confidence
        
        return {
            'sentiment': sentiment,
            'score': sentiment_score,
            'confidence': confidence
        }
    
    def _update_sentiment_trends(self, product):
        """
        Update sentiment trends for a product
        """
        from datetime import date
        
        # Get all reviews for the product
        reviews = product.reviews.all()
        
        # Group by date
        daily_sentiments = {}
        for review in reviews:
            review_date = review.date_added.date()
            if review_date not in daily_sentiments:
                daily_sentiments[review_date] = {
                    'positive': 0, 'negative': 0, 'neutral': 0,
                    'total_score': 0, 'count': 0
                }
            
            sentiment = self._analyze_single_review_sentiment(review)
            daily_sentiments[review_date][sentiment['sentiment']] += 1
            daily_sentiments[review_date]['total_score'] += sentiment['score']
            daily_sentiments[review_date]['count'] += 1
        
        # Create or update trend records
        for review_date, data in daily_sentiments.items():
            avg_sentiment = data['total_score'] / data['count'] if data['count'] > 0 else 0
            
            SentimentTrend.objects.get_or_create(
                product=product,
                date=review_date,
                defaults={
                    'positive_count': data['positive'],
                    'negative_count': data['negative'],
                    'neutral_count': data['neutral'],
                    'average_sentiment': avg_sentiment,
                    'total_reviews': data['count']
                }
            )
    
    def _analyze_aspect_sentiments(self, reviews):
        """
        Analyze sentiment for different aspects
        """
        aspect_sentiments = defaultdict(lambda: {
            'positive_mentions': 0,
            'negative_mentions': 0,
            'total_mentions': 0,
            'score': 0.0,
            'confidence': 0.0
        })
        
        for review in reviews:
            text = (review.content or '').lower()
            
            # Analyze each aspect
            for aspect, keywords in self.aspects.items():
                aspect_mentioned = False
                positive_count = 0
                negative_count = 0
                
                # Check if aspect is mentioned
                for keyword in keywords:
                    if keyword in text:
                        aspect_mentioned = True
                        break
                
                if aspect_mentioned:
                    aspect_sentiments[aspect]['total_mentions'] += 1
                    
                    # Count positive and negative words for this aspect
                    for word in self.positive_words.get(aspect, []):
                        if word in text:
                            positive_count += 1
                    
                    for word in self.negative_words.get(aspect, []):
                        if word in text:
                            negative_count += 1
                    
                    # Determine aspect sentiment
                    if positive_count > negative_count:
                        aspect_sentiments[aspect]['positive_mentions'] += 1
                    elif negative_count > positive_count:
                        aspect_sentiments[aspect]['negative_mentions'] += 1
        
        # Calculate sentiment scores for each aspect
        for aspect, data in aspect_sentiments.items():
            total_mentions = data['total_mentions']
            if total_mentions > 0:
                positive_ratio = data['positive_mentions'] / total_mentions
                negative_ratio = data['negative_mentions'] / total_mentions
                
                # Calculate sentiment score (-1 to 1)
                data['score'] = positive_ratio - negative_ratio
                
                # Calculate confidence based on mention count
                data['confidence'] = min(1.0, total_mentions / 5)
                
                # Determine sentiment category
                if data['score'] > 0.1:
                    data['sentiment'] = 'positive'
                elif data['score'] < -0.1:
                    data['sentiment'] = 'negative'
                else:
                    data['sentiment'] = 'neutral'
        
        return aspect_sentiments
    
    def get_product_sentiment_summary(self, product):
        """
        Get sentiment summary for a product
        """
        try:
            # Get all sentiment analyses for this product's reviews
            sentiment_analyses = SentimentAnalysis.objects.filter(review__product=product)
            aspect_sentiments = AspectSentiment.objects.filter(review__product=product)
            
            if not sentiment_analyses.exists():
                return None
            
            # Calculate overall stats
            total_reviews = sentiment_analyses.count()
            positive_count = sentiment_analyses.filter(overall_sentiment='positive').count()
            negative_count = sentiment_analyses.filter(overall_sentiment='negative').count()
            neutral_count = sentiment_analyses.filter(overall_sentiment='neutral').count()
            avg_score = sentiment_analyses.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0
            
            # Determine overall sentiment
            if positive_count > negative_count and positive_count > neutral_count:
                overall_sentiment = 'positive'
            elif negative_count > positive_count and negative_count > neutral_count:
                overall_sentiment = 'negative'
            else:
                overall_sentiment = 'neutral'
            
            summary = {
                'overall_sentiment': overall_sentiment,
                'sentiment_score': avg_score,
                'confidence_score': min(1.0, total_reviews / 10),
                'review_stats': {
                    'total': total_reviews,
                    'positive': positive_count,
                    'negative': negative_count,
                    'neutral': neutral_count
                },
                'aspects': {}
            }
            
            # Group aspect sentiments by aspect
            aspect_data = {}
            for aspect_sentiment in aspect_sentiments:
                aspect = aspect_sentiment.aspect
                if aspect not in aspect_data:
                    aspect_data[aspect] = {
                        'sentiment_score': 0,
                        'confidence': 0,
                        'count': 0
                    }
                
                aspect_data[aspect]['sentiment_score'] += aspect_sentiment.sentiment_score
                aspect_data[aspect]['confidence'] += aspect_sentiment.confidence
                aspect_data[aspect]['count'] += 1
            
            # Calculate averages for aspects
            for aspect, data in aspect_data.items():
                if data['count'] > 0:
                    summary['aspects'][aspect] = {
                        'sentiment_score': data['sentiment_score'] / data['count'],
                        'confidence': data['confidence'] / data['count'],
                        'total_mentions': data['count']
                    }
            
            return summary
            
        except Exception as e:
            print(f"Error getting sentiment summary: {e}")
            return None


class SentimentTrendAnalyzer:
    """Analyze sentiment trends over time"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
    
    def analyze_sentiment_trends(self, product, days=30):
        """
        Analyze sentiment trends for a product over time
        """
        try:
            # Get reviews from the specified time period
            start_date = timezone.now() - timedelta(days=days)
            reviews = product.reviews.filter(created_at__gte=start_date)
            
            if not reviews.exists():
                return None
            
            # Group reviews by week
            weekly_sentiments = self._group_reviews_by_week(reviews)
            
            # Calculate trend
            trend_data = self._calculate_trend(weekly_sentiments)
            
            # Save trend data (using the existing _update_sentiment_trends method)
            # The trend data is already being saved in _update_sentiment_trends
            
            return trend_data
            
        except Exception as e:
            print(f"Error analyzing sentiment trends: {e}")
            return None
    
    def _group_reviews_by_week(self, reviews):
        """
        Group reviews by week and calculate average sentiment
        """
        weekly_data = defaultdict(list)
        
        for review in reviews:
            # Get week start date
            week_start = review.created_at - timedelta(days=review.created_at.weekday())
            week_key = week_start.strftime('%Y-%W')
            
            # Calculate sentiment for this review
            blob = TextBlob(review.content or '')
            sentiment_score = blob.sentiment.polarity
            
            weekly_data[week_key].append(sentiment_score)
        
        # Calculate average sentiment for each week
        weekly_sentiments = {}
        for week, scores in weekly_data.items():
            weekly_sentiments[week] = np.mean(scores)
        
        return weekly_sentiments
    
    def _calculate_trend(self, weekly_sentiments):
        """
        Calculate trend direction and strength
        """
        if len(weekly_sentiments) < 2:
            return {
                'direction': 'stable',
                'strength': 0.0,
                'average_sentiment': 0.0,
                'volatility': 0.0
            }
        
        # Convert to lists for analysis
        weeks = list(weekly_sentiments.keys())
        sentiments = list(weekly_sentiments.values())
        
        # Calculate trend using linear regression
        x = np.arange(len(sentiments))
        y = np.array(sentiments)
        
        # Simple linear regression
        slope = np.polyfit(x, y, 1)[0]
        
        # Determine trend direction
        if slope > 0.01:
            direction = 'improving'
        elif slope < -0.01:
            direction = 'declining'
        else:
            direction = 'stable'
        
        # Calculate trend strength (absolute slope)
        strength = abs(slope)
        
        # Calculate average sentiment
        average_sentiment = np.mean(sentiments)
        
        # Calculate volatility (standard deviation)
        volatility = np.std(sentiments)
        
        return {
            'direction': direction,
            'strength': strength,
            'average_sentiment': average_sentiment,
            'volatility': volatility
        }
    
    def get_sentiment_insights(self, product):
        """
        Get comprehensive sentiment insights for a product
        """
        try:
            # Get sentiment analysis
            sentiment_summary = self.sentiment_analyzer.get_product_sentiment_summary(product)
            
            if not sentiment_summary:
                return None
            
            # Get trend analysis (get the most recent trend)
            trend = SentimentTrend.objects.filter(product=product).order_by('-date').first()
            
            # Get recent reviews for detailed analysis
            recent_reviews = product.reviews.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).order_by('-created_at')[:10]
            
            insights = {
                'overall_sentiment': sentiment_summary['overall_sentiment'],
                'sentiment_score': sentiment_summary['sentiment_score'],
                'confidence': sentiment_summary['confidence_score'],
                'review_stats': sentiment_summary['review_stats'],
                'aspects': sentiment_summary['aspects'],
                'trend': {
                    'direction': 'stable',  # Simplified for now
                    'strength': 0.0,
                    'volatility': 0.0
                },
                'recent_reviews': []
            }
            
            # Add recent review insights
            for review in recent_reviews:
                blob = TextBlob(review.content or '')
                insights['recent_reviews'].append({
                    'id': review.uid,
                    'text': (review.content or '')[:100] + '...' if len(review.content or '') > 100 else (review.content or ''),
                    'sentiment_score': blob.sentiment.polarity,
                    'subjectivity': blob.sentiment.subjectivity,
                    'rating': review.stars,
                    'date': review.date_added.strftime('%Y-%m-%d')
                })
            
            return insights
            
        except Exception as e:
            print(f"Error getting sentiment insights: {e}")
            return None


class SentimentService:
    """Service class for sentiment analysis operations"""
    
    def __init__(self):
        self.analyzer = SentimentAnalyzer()
        self.trend_analyzer = SentimentTrendAnalyzer()
    
    def analyze_product_sentiment(self, product, force_recalculate=False):
        """
        Analyze sentiment for a product
        """
        self.analyzer.analyze_product_sentiment(product, force_recalculate)
    
    def analyze_all_products_sentiment(self, force_recalculate=False):
        """
        Analyze sentiment for all products
        """
        self.analyzer.analyze_all_products_sentiment(force_recalculate)
    
    def get_product_sentiment(self, product):
        """
        Get sentiment summary for a product
        """
        return self.analyzer.get_product_sentiment_summary(product)
    
    def analyze_sentiment_trends(self, product, days=30):
        """
        Analyze sentiment trends for a product
        """
        return self.trend_analyzer.analyze_sentiment_trends(product, days)
    
    def get_sentiment_insights(self, product):
        """
        Get comprehensive sentiment insights
        """
        return self.trend_analyzer.get_sentiment_insights(product)
    
    def get_top_sentiment_products(self, sentiment_type='positive', limit=10):
        """
        Get products with highest sentiment scores
        """
        try:
            from django.db.models import Avg, Count
            
            # Get products with their average sentiment scores
            product_sentiments = SentimentAnalysis.objects.filter(
                review__product__isnull=False
            ).values('review__product').annotate(
                avg_sentiment=Avg('sentiment_score'),
                total_reviews=Count('uid')
            ).filter(total_reviews__gte=2)  # At least 2 reviews for reliability
            
            if sentiment_type == 'positive':
                product_sentiments = product_sentiments.filter(avg_sentiment__gt=0.1)
                product_sentiments = product_sentiments.order_by('-avg_sentiment')[:limit]
            elif sentiment_type == 'negative':
                product_sentiments = product_sentiments.filter(avg_sentiment__lt=-0.1)
                product_sentiments = product_sentiments.order_by('avg_sentiment')[:limit]
            else:
                product_sentiments = product_sentiments.order_by('-avg_sentiment')[:limit]
            
            # Get the actual products
            product_ids = [ps['review__product'] for ps in product_sentiments]
            products = Product.objects.filter(uid__in=product_ids)
            
            return list(products)
            
        except Exception as e:
            print(f"Error getting top sentiment products: {e}")
            return []
    
    def get_aspect_insights(self, aspect, limit=10):
        """
        Get insights for a specific aspect across all products
        """
        try:
            from django.db.models import Avg, Count
            
            # Get products with their average aspect sentiment scores
            aspect_sentiments = AspectSentiment.objects.filter(
                aspect=aspect,
                review__product__isnull=False
            ).values('review__product').annotate(
                avg_sentiment=Avg('sentiment_score'),
                total_mentions=Count('uid')
            ).filter(total_mentions__gte=2)  # At least 2 mentions for reliability
            
            aspect_sentiments = aspect_sentiments.order_by('-avg_sentiment')[:limit]
            
            insights = []
            for aspect_sentiment in aspect_sentiments:
                product = Product.objects.get(uid=aspect_sentiment['review__product'])
                insights.append({
                    'product': product,
                    'sentiment_score': aspect_sentiment['avg_sentiment'],
                    'total_mentions': aspect_sentiment['total_mentions']
                })
            
            return insights
            
        except Exception as e:
            print(f"Error getting aspect insights: {e}")
            return [] 