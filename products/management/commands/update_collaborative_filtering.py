"""
Django management command to update collaborative filtering models
Usage: python manage.py update_collaborative_filtering
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from products.collaborative_filtering import CollaborativeFilteringService
from products.matrix_factorization import MatrixFactorizationService


class Command(BaseCommand):
    help = 'Update collaborative filtering models and similarity matrices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation of all similarities',
        )
        parser.add_argument(
            '--method',
            type=str,
            choices=['user_based', 'item_based', 'hybrid', 'matrix_factorization', 'svd', 'nmf', 'all'],
            default='all',
            help='Which collaborative filtering method to update',
        )
        parser.add_argument(
            '--fit-models',
            action='store_true',
            help='Fit matrix factorization models',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting collaborative filtering update...')
        )

        try:
            if options['method'] in ['user_based', 'item_based', 'hybrid', 'all']:
                # Update traditional collaborative filtering
                self.stdout.write('Updating collaborative filtering similarities...')
                collaborative_service = CollaborativeFilteringService()
                
                if options['method'] == 'all':
                    # Update all collaborative filtering methods
                    collaborative_service.update_similarity_matrices()
                else:
                    # Update specific method
                    self.stdout.write(f'Updating {options["method"]} collaborative filtering...')
                    # The service handles all methods together
                    collaborative_service.update_similarity_matrices()
                
                self.stdout.write(
                    self.style.SUCCESS('Collaborative filtering similarities updated!')
                )

            if options['method'] in ['matrix_factorization', 'svd', 'nmf', 'all'] or options['fit_models']:
                # Update matrix factorization models
                self.stdout.write('Updating matrix factorization models...')
                mf_service = MatrixFactorizationService()
                
                # Create rating matrix
                self.stdout.write('Creating rating matrix...')
                rating_matrix = mf_service.create_rating_matrix()
                
                if not rating_matrix.empty:
                    self.stdout.write(f'Rating matrix created with shape: {rating_matrix.shape}')
                    
                    # Fit models
                    self.stdout.write('Fitting matrix factorization models...')
                    success = mf_service.fit_models()
                    
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS('Matrix factorization models fitted successfully!')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING('Some matrix factorization models failed to fit')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING('No rating data available for matrix factorization')
                    )

            self.stdout.write(
                self.style.SUCCESS('Collaborative filtering update completed successfully!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating collaborative filtering: {e}')
            ) 