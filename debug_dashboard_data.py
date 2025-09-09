#!/usr/bin/env python
"""
Debug script to test dashboard data methods and see what's actually being returned
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'opjindal.settings')
django.setup()

from apps.cross_counting.utils import TablePartitioningManager
from apps.cross_counting.models import Region, Camera, CrossCountingData
from django.utils import timezone
from datetime import datetime

print("=== DEBUGGING DASHBOARD DATA ===")

# Check basic data
print("\nBasic Database Counts:")
regions_count = Region.objects.count()
cameras_count = Camera.objects.count()
active_cameras_count = Camera.objects.filter(status=True).count()
total_data_count = CrossCountingData.objects.count()

print(f"Regions: {regions_count}")
print(f"Total Cameras: {cameras_count}")
print(f"Active Cameras: {active_cameras_count}")
print(f"Total Data Records: {total_data_count}")

# Check today's data
today = timezone.now().date()
start_of_day = timezone.make_aware(datetime.combine(today, datetime.min.time().replace(hour=0, minute=1)))
end_of_day = timezone.make_aware(datetime.combine(today, datetime.max.time().replace(hour=23, minute=59)))

today_data_count = CrossCountingData.objects.filter(
    created_at__gte=start_of_day,
    created_at__lte=end_of_day
).count()

print(f"Today's Data Records: {today_data_count}")

# Test dashboard statistics
print("\n=== Testing get_dashboard_statistics ===")
try:
    dashboard_data = TablePartitioningManager.get_dashboard_statistics()
    print("Dashboard Data:", dashboard_data)
except Exception as e:
    print("ERROR in get_dashboard_statistics:", str(e))
    import traceback
    traceback.print_exc()

# Test enhanced dashboard data
print("\n=== Testing get_enhanced_dashboard_data ===")
try:
    enhanced_data = TablePartitioningManager.get_enhanced_dashboard_data()
    print(f"Enhanced Data - {len(enhanced_data)} regions returned")
    for i, region_data in enumerate(enhanced_data):
        print(f"Region {i+1}: {region_data}")
except Exception as e:
    print("ERROR in get_enhanced_dashboard_data:", str(e))
    import traceback
    traceback.print_exc()

# Test current occupancy data
print("\n=== Testing get_current_occupancy_data ===")
try:
    occupancy_data = TablePartitioningManager.get_current_occupancy_data()
    print(f"Occupancy Data - {len(occupancy_data)} regions returned")
    for i, region_data in enumerate(occupancy_data):
        print(f"Region {i+1}: {region_data}")
except Exception as e:
    print("ERROR in get_current_occupancy_data:", str(e))
    import traceback
    traceback.print_exc()

# Check if there are any regions with cameras
print("\n=== Checking Region/Camera Relationships ===")
regions = Region.objects.all()
for region in regions:
    cameras = Camera.objects.filter(region=region, status=True)
    print(f"Region '{region.name}': {cameras.count()} active cameras")

    # Check if any of these cameras have data today
    if cameras.exists():
        for camera in cameras[:3]:  # Show first 3 cameras
            data_count = CrossCountingData.objects.filter(
                camera=camera,
                created_at__gte=start_of_day,
                created_at__lte=end_of_day
            ).count()
            latest_data = CrossCountingData.objects.filter(
                camera=camera,
                created_at__gte=start_of_day,
                created_at__lte=end_of_day
            ).order_by('-created_at').first()

            if latest_data:
                print(f"  Camera '{camera.name}': {data_count} records today, latest: in={latest_data.cc_in_count}, out={latest_data.cc_out_count}")
            else:
                print(f"  Camera '{camera.name}': No data today")

print("\n=== Debug Complete ===")
