#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'opjindal.settings')
django.setup()

from apps.cross_counting.utils import TablePartitioningManager

occupancy_data = TablePartitioningManager.get_current_occupancy_data()
print("Occupancy Data Test Results:")
for region in occupancy_data:
    print(f"Region: {region['region_name']}")
    print(f"  Current Count: {region['current_count']}")
    print(f"  Max Occupancy: {region['max_occupancy']}")
    print(f"  Occupancy %: {region['occupancy_percentage']}%")
    print(f"  Non-negative: {region['current_count'] >= 0}")
    print()
