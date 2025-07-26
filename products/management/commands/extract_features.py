"""
Django management command to extract product features
Usage: python manage.py extract_features
"""

from django.core.management.base import BaseCommand
from products.feature_extractor import ProductFeatureExtractor


class Command(BaseCommand):
    help = 'Extract product features for content-based filtering'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation of all features',
        )
        parser.add_argument(
            '--product-id',
            type=str,
            help='Extract features for a specific product by ID',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting product feature extraction...')
        )

        feature_extractor = ProductFeatureExtractor()

        try:
            if options['product_id']:
                # Extract features for a specific product
                from products.models import Product
                try:
                    product = Product.objects.get(uid=options['product_id'])
                    self.stdout.write(f'Extracting features for product: {product.product_name}')
                    feature_extractor.extract_product_features(product)
                    self.stdout.write(
                        self.style.SUCCESS(f'Features extracted for {product.product_name}')
                    )
                except Product.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'Product with ID {options["product_id"]} not found')
                    )
            else:
                # Extract features for all products
                self.stdout.write('Extracting features for all products...')
                feature_extractor.extract_all_product_features(
                    force_recalculate=options['force']
                )
                self.stdout.write(
                    self.style.SUCCESS('Product feature extraction completed successfully!')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during feature extraction: {e}')
            ) 