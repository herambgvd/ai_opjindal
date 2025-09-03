#!/usr/bin/env python
"""
Test script to verify the constant value correction logic
"""
import os
import sys
import django

# Setup Django
sys.path.append('/Users/snowden/project/opjindal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'opjindal.settings')
django.setup()

from apps.cross_counting.utils import TablePartitioningManager

def test_correction_logic():
    """Test the automatic correction logic"""
    print("🧪 Testing Constant Value Correction Logic")
    print("=" * 50)

    # Get current occupancy data
    occupancy_data = TablePartitioningManager.get_current_occupancy_data()

    print(f"📊 Found {len(occupancy_data)} regions")
    print()

    for region in occupancy_data:
        region_name = region['region_name']
        current_count = region['current_count']
        available_count = region['available_count']
        max_occupancy = region['max_occupancy']
        total_in = region['total_in_count']
        total_out = region['total_out_count']
        calc_method = region['calculation_method']
        correction_applied = region.get('correction_applied', False)

        print(f"🏢 Region: {region_name}")
        print(f"   👥 Current: {current_count}/{max_occupancy} ({region['occupancy_percentage']}%)")
        print(f"   🚪 Available: {available_count}")
        print(f"   📊 In/Out: {total_in}/{total_out} = {total_in - total_out}")
        print(f"   🔧 Method: {calc_method}")

        if correction_applied:
            original_in = region.get('original_in_count', total_in)
            print(f"   ⚠️  CORRECTION APPLIED!")
            print(f"   ➡️  Original In: {original_in} → Corrected: {total_in}")
            print(f"   ➡️  Correction Amount: +{total_in - original_in}")

        # Test logic explanation
        basic_occupancy = total_in - total_out
        if basic_occupancy < -32:
            print(f"   🚨 Would trigger correction (occupancy: {basic_occupancy} < -32)")
        elif basic_occupancy < 0:
            print(f"   ⚡ Negative but not severe (occupancy: {basic_occupancy})")
        else:
            print(f"   ✅ Normal calculation (occupancy: {basic_occupancy})")

        print()

def simulate_correction_scenario():
    """Simulate a severe negative scenario"""
    print("🎯 Simulating Correction Scenario")
    print("=" * 50)

    # Example: 8 cameras, severe negative occupancy
    cameras = 8
    in_count = 20
    out_count = 75  # Results in -55 occupancy
    basic_occupancy = in_count - out_count

    print(f"📝 Scenario: {cameras} cameras")
    print(f"📊 Total In: {in_count}, Total Out: {out_count}")
    print(f"⚖️  Basic Occupancy: {basic_occupancy}")

    if basic_occupancy < -32:
        correction_needed = abs(basic_occupancy) + 10
        correction_per_camera = correction_needed // cameras
        remaining_correction = correction_needed % cameras

        print(f"🚨 SEVERE NEGATIVE DETECTED!")
        print(f"🔧 Correction needed: {correction_needed}")
        print(f"📡 Per camera: {correction_per_camera}")
        print(f"📡 Remaining: {remaining_correction}")

        new_in_count = in_count + correction_needed
        new_occupancy = new_in_count - out_count

        print(f"➡️  New In Count: {in_count} + {correction_needed} = {new_in_count}")
        print(f"➡️  New Occupancy: {new_in_count} - {out_count} = {new_occupancy}")
        print(f"✅ Correction successful!")
    else:
        print(f"✅ No correction needed")

if __name__ == "__main__":
    test_correction_logic()
    print()
    simulate_correction_scenario()
