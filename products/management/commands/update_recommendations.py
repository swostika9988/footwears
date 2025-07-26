"""
Django management command to update recommendation data
Usage: python manage.py update_recommendations
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from products.similarity_calculator import SimilarityService
from products.recommendation_engine import UserPreferenceLearner


class Command(BaseCommand):
    help = 'Update recommendation data including similarities and user preferences'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation of all similarities',
        )
        parser.add_argument(
            '--users-only',
            action='store_true',
            help='Only update user similarities and preferences',
        )
        parser.add_argument(
            '--products-only',
            action='store_true',
            help='Only update product similarities',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting recommendation data update...')
        )

        similarity_service = SimilarityService()
        preference_learner = UserPreferenceLearner()

        try:
            if options['users_only']:
                # Update only user-related data
                self.stdout.write('Updating user similarities...')
                similarity_service.calculator.calculate_user_similarities(
                    force_recalculate=options['force']
                )
                
                self.stdout.write('Updating user preferences...')
                users = User.objects.filter(behaviors__isnull=False).distinct()
                for user in users:
                    preference_learner.update_user_preferences(user)
                
            elif options['products_only']:
                # Update only product similarities
                self.stdout.write('Updating product similarities...')
                similarity_service.calculator.calculate_product_similarities(
                    force_recalculate=options['force']
                )
                
            else:
                # Update all recommendation data
                similarity_service.update_all_similarities(
                    force_recalculate=options['force']
                )
                
                # Update user preferences
                self.stdout.write('Updating user preferences...')
                users = User.objects.filter(behaviors__isnull=False).distinct()
                for user in users:
                    preference_learner.update_user_preferences(user)

            self.stdout.write(
                self.style.SUCCESS('Recommendation data update completed successfully!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating recommendation data: {e}')
            ) 