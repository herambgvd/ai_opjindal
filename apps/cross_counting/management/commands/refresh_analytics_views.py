from django.core.management.base import BaseCommand
from apps.cross_counting.utils import CrossCountingAnalytics


class Command(BaseCommand):
    help = 'Refresh materialized views for cross-counting analytics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--concurrent',
            action='store_true',
            help='Use CONCURRENTLY option for refresh (slower but non-blocking)',
        )

    def handle(self, *args, **options):
        try:
            if options['concurrent']:
                CrossCountingAnalytics.refresh_materialized_views()
                self.stdout.write(
                    self.style.SUCCESS('Successfully refreshed materialized views concurrently')
                )
            else:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("REFRESH MATERIALIZED VIEW cross_counting_hourly_aggregates;")
                    cursor.execute("REFRESH MATERIALIZED VIEW cross_counting_daily_peaks;")
                
                self.stdout.write(
                    self.style.SUCCESS('Successfully refreshed materialized views')
                )
        except Exception as e:
            self.stderr.write(f"Error refreshing views: {e}")
