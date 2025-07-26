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
            SentimentAnalysis.objects.filter(product=product).delete()
            AspectSentiment.objects.filter(product=product).delete()
            
            # Analyze overall sentiment
            overall_sentiment = self._analyze_overall_sentiment(reviews)
            
            # Create overall sentiment record
            SentimentAnalysis.objects.create(
                product=product,
                overall_sentiment=overall_sentiment['sentiment'],
                sentiment_score=overall_sentiment['score'],
                positive_reviews=overall_sentiment['positive_count'],
                negative_reviews=overall_sentiment['negative_count'],
                neutral_reviews=overall_sentiment['neutral_count'],
                total_reviews=overall_sentiment['total_count'],
                confidence_score=overall_sentiment['confidence']
            )
            
            # Analyze aspect-based sentiment
            aspect_sentiments = self._analyze_aspect_sentiments(reviews)
            
            # Create aspect sentiment records
            for aspect, sentiment_data in aspect_sentiments.items():
                AspectSentiment.objects.create(
                    product=product,
                    aspect=aspect,
                    sentiment_score=sentiment_data['score'],
                    positive_mentions=sentiment_data['positive_mentions'],
                    negative_mentions=sentiment_data['negative_mentions'],
                    total_mentions=sentiment_data['total_mentions'],
                    confidence_score=sentiment_data['confidence']
                )
            
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
            product=product,
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
            blob = TextBlob(review.review_text)
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
            text = review.review_text.lower()
            
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
        
        return aspect_sentiments
    
    def get_product_sentiment_summary(self, product):
        """
        Get sentiment summary for a product
        """
        try:
            sentiment_analysis = SentimentAnalysis.objects.filter(product=product).first()
            aspect_sentiments = AspectSentiment.objects.filter(product=product)
            
            if not sentiment_analysis:
                return None
            
            summary = {
                'overall_sentiment': sentiment_analysis.overall_sentiment,
                'sentiment_score': sentiment_analysis.sentiment_score,
                'confidence_score': sentiment_analysis.confidence_score,
                'review_stats': {
                    'total': sentiment_analysis.total_reviews,
                    'positive': sentiment_analysis.positive_reviews,
                    'negative': sentiment_analysis.negative_reviews,
                    'neutral': sentiment_analysis.neutral_reviews
                },
                'aspects': {}
            }
            
            # Add aspect sentiments
            for aspect_sentiment in aspect_sentiments:
                summary['aspects'][aspect_sentiment.aspect] = {
                    'sentiment_score': aspect_sentiment.sentiment_score,
                    'positive_mentions': aspect_sentiment.positive_mentions,
                    'negative_mentions': aspect_sentiment.negative_mentions,
                    'total_mentions': aspect_sentiment.total_mentions,
                    'confidence_score': aspect_sentiment.confidence_score
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
            
            # Save trend data
            SentimentTrend.objects.filter(product=product).delete()
            
            SentimentTrend.objects.create(
                product=product,
                trend_direction=trend_data['direction'],
                trend_strength=trend_data['strength'],
                average_sentiment=trend_data['average_sentiment'],
                sentiment_volatility=trend_data['volatility'],
                period_days=days,
                data_points=len(weekly_sentiments)
            )
            
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
            blob = TextBlob(review.review_text)
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
            
            # Get trend analysis
            trend = SentimentTrend.objects.filter(product=product).first()
            
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
                    'direction': trend.trend_direction if trend else 'unknown',
                    'strength': trend.trend_strength if trend else 0.0,
                    'volatility': trend.sentiment_volatility if trend else 0.0
                },
                'recent_reviews': []
            }
            
            # Add recent review insights
            for review in recent_reviews:
                blob = TextBlob(review.review_text)
                insights['recent_reviews'].append({
                    'id': review.id,
                    'text': review.review_text[:100] + '...' if len(review.review_text) > 100 else review.review_text,
                    'sentiment_score': blob.sentiment.polarity,
                    'subjectivity': blob.sentiment.subjectivity,
                    'rating': review.stars,
                    'date': review.created_at.strftime('%Y-%m-%d')
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
            if sentiment_type == 'positive':
                products = SentimentAnalysis.objects.filter(
                    overall_sentiment='positive'
                ).order_by('-sentiment_score')[:limit]
            elif sentiment_type == 'negative':
                products = SentimentAnalysis.objects.filter(
                    overall_sentiment='negative'
                ).order_by('sentiment_score')[:limit]
            else:
                products = SentimentAnalysis.objects.all().order_by('-sentiment_score')[:limit]
            
            return [analysis.product for analysis in products]
            
        except Exception as e:
            print(f"Error getting top sentiment products: {e}")
            return []
    
    def get_aspect_insights(self, aspect, limit=10):
        """
        Get insights for a specific aspect across all products
        """
        try:
            aspect_sentiments = AspectSentiment.objects.filter(
                aspect=aspect,
                total_mentions__gte=3  # Minimum mentions for reliability
            ).order_by('-sentiment_score')[:limit]
            
            insights = []
            for aspect_sentiment in aspect_sentiments:
                insights.append({
                    'product': aspect_sentiment.product,
                    'sentiment_score': aspect_sentiment.sentiment_score,
                    'positive_mentions': aspect_sentiment.positive_mentions,
                    'negative_mentions': aspect_sentiment.negative_mentions,
                    'total_mentions': aspect_sentiment.total_mentions,
                    'confidence': aspect_sentiment.confidence_score
                })
            
            return insights
            
        except Exception as e:
            print(f"Error getting aspect insights: {e}")
            return [] 