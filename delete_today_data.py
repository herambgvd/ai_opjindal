#!/usr/bin/env python3
"""
Script to delete all today's data from CrossCountingData model
Usage: python delete_today_data.py
"""

import os
import sys
import django
from datetime import date
from django.utils import timezone
from django.db import transaction

# Add the project root to Python path
sys.path.append('/Users/snowden/project/opjindal')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'opjindal.settings')
django.setup()

from apps.cross_counting.models import CrossCountingData


def delete_today_data():
    """Delete all CrossCountingData records for today's date"""

    # Get today's date
    today = date.today()

    print(f"Deleting all CrossCountingData records for {today}...")

    try:
        with transaction.atomic():
            # Count records before deletion
            count_before = CrossCountingData.objects.filter(
                created_at__date=today
            ).count()

            print(f"Found {count_before} records for today ({today})")

            if count_before == 0:
                print("No records found for today. Nothing to delete.")
                return

            # Confirm deletion
            confirm = input(f"Are you sure you want to delete {count_before} records? (yes/no): ")

            if confirm.lower() in ['yes', 'y']:
                # Delete all records for today
                deleted_count, _ = CrossCountingData.objects.filter(
                    created_at__date=today
                ).delete()

                print(f"Successfully deleted {deleted_count} records for {today}")

                # Verify deletion
                remaining_count = CrossCountingData.objects.filter(
                    created_at__date=today
                ).count()

                if remaining_count == 0:
                    print("✅ All today's records have been successfully deleted.")
                else:
                    print(f"⚠️  Warning: {remaining_count} records still remain for today.")

            else:
                print("Deletion cancelled.")

    except Exception as e:
        print(f"❌ Error occurred while deleting data: {e}")
        raise


def delete_today_data_by_time_range():
    """Alternative method: Delete by specific time range for today"""

    # Get today's start and end datetime
    today = date.today()
    start_of_day = timezone.make_aware(
        timezone.datetime.combine(today, timezone.datetime.min.time())
    )
    end_of_day = timezone.make_aware(
        timezone.datetime.combine(today, timezone.datetime.max.time())
    )

    print(f"Deleting CrossCountingData records between {start_of_day} and {end_of_day}...")

    try:
        with transaction.atomic():
            # Count records before deletion
            count_before = CrossCountingData.objects.filter(
                created_at__gte=start_of_day,
                created_at__lte=end_of_day
            ).count()

            print(f"Found {count_before} records for the time range")

            if count_before == 0:
                print("No records found for the specified time range.")
                return

            # Confirm deletion
            confirm = input(f"Are you sure you want to delete {count_before} records? (yes/no): ")

            if confirm.lower() in ['yes', 'y']:
                # Delete all records for the time range
                deleted_count, _ = CrossCountingData.objects.filter(
                    created_at__gte=start_of_day,
                    created_at__lte=end_of_day
                ).delete()

                print(f"Successfully deleted {deleted_count} records")

                # Verify deletion
                remaining_count = CrossCountingData.objects.filter(
                    created_at__gte=start_of_day,
                    created_at__lte=end_of_day
                ).count()

                if remaining_count == 0:
                    print("✅ All records in the time range have been successfully deleted.")
                else:
                    print(f"⚠️  Warning: {remaining_count} records still remain in the time range.")

            else:
                print("Deletion cancelled.")

    except Exception as e:
        print(f"❌ Error occurred while deleting data: {e}")
        raise


def delete_data_bulk_optimized():
    """Optimized bulk deletion for large datasets"""

    today = date.today()

    print(f"Performing optimized bulk deletion for {today}...")

    try:
        from django.db import connection

        with transaction.atomic():
            # Count records first
            count_before = CrossCountingData.objects.filter(
                created_at__date=today
            ).count()

            print(f"Found {count_before} records for today ({today})")

            if count_before == 0:
                print("No records found for today. Nothing to delete.")
                return

            # Confirm deletion
            confirm = input(f"Are you sure you want to delete {count_before} records? (yes/no): ")

            if confirm.lower() in ['yes', 'y']:
                # Use raw SQL for faster deletion on large datasets
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM cross_counting_data_timeseries 
                        WHERE DATE(created_at) = %s
                    """, [today])

                    deleted_count = cursor.rowcount

                print(f"Successfully deleted {deleted_count} records using optimized query")

                # Verify deletion
                remaining_count = CrossCountingData.objects.filter(
                    created_at__date=today
                ).count()

                if remaining_count == 0:
                    print("✅ All today's records have been successfully deleted.")
                else:
                    print(f"⚠️  Warning: {remaining_count} records still remain for today.")

            else:
                print("Deletion cancelled.")

    except Exception as e:
        print(f"❌ Error occurred while deleting data: {e}")
        raise


if __name__ == "__main__":
    print("CrossCountingData Today's Data Deletion Script")
    print("=" * 50)

    print("\nChoose deletion method:")
    print("1. Standard deletion by date (recommended)")
    print("2. Deletion by time range")
    print("3. Optimized bulk deletion (for large datasets)")
    print("4. Exit")

    choice = input("\nEnter your choice (1-4): ")

    if choice == "1":
        delete_today_data()
    elif choice == "2":
        delete_today_data_by_time_range()
    elif choice == "3":
        delete_data_bulk_optimized()
    elif choice == "4":
        print("Exiting...")
        sys.exit(0)
    else:
        print("Invalid choice. Exiting...")
        sys.exit(1)
