"""
Django management command to learn user preferences
Usage: python manage.py learn_preferences
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from products.preference_learner import PreferenceService


class Command(BaseCommand):
    help = 'Learn user preferences for content-based filtering'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation of all preferences',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Learn preferences for a specific user',
        )
        parser.add_argument(
            '--show-summary',
            action='store_true',
            help='Show preference summary after learning',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting user preference learning...')
        )

        preference_service = PreferenceService()

        try:
            if options['username']:
                # Learn preferences for a specific user
                try:
                    user = User.objects.get(username=options['username'])
                    self.stdout.write(f'Learning preferences for user: {user.username}')
                    
                    preference_service.update_user_preferences(
                        user, 
                        force_recalculate=options['force']
                    )
                    
                    if options['show_summary']:
                        summary = preference_service.get_user_preferences(user)
                        if summary:
                            self._display_preference_summary(summary, user.username)
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Preferences learned for {user.username}')
                    )
                except User.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'User {options["username"]} not found')
                    )
            else:
                # Learn preferences for all users
                self.stdout.write('Learning preferences for all users...')
                preference_service.update_all_user_preferences(
                    force_recalculate=options['force']
                )
                self.stdout.write(
                    self.style.SUCCESS('User preference learning completed successfully!')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during preference learning: {e}')
            )
    
    def _display_preference_summary(self, summary, username):
        """Display preference summary for a user"""
        self.stdout.write(f'\nPreference Summary for {username}:')
        self.stdout.write(f'Total Preferences: {summary["total_preferences"]}')
        self.stdout.write(f'Confidence Score: {summary["confidence_score"]:.2f}')
        
        if summary['price_range']:
            self.stdout.write(
                f'Price Range: Rs. {summary["price_range"]["min"]} - Rs. {summary["price_range"]["max"]}'
            )
        
        if summary['categories']:
            self.stdout.write('\nTop Categories:')
            for category in summary['categories'][:3]:
                self.stdout.write(f'  - {category["name"]}: {category["weight"]:.2f}')
        
        if summary['brands']:
            self.stdout.write('\nTop Brands:')
            for brand in summary['brands'][:3]:
                self.stdout.write(f'  - {brand["name"]}: {brand["weight"]:.2f}')
        
        self.stdout.write('') 