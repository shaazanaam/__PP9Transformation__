"""
Quick test to compare OLD vs OPTIMIZED TriCounty Removal transformation
"""
import os
import sys
import django
import time

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_data_project.settings')
django.setup()

from __data_processor__.transformers.removal_transformers import RemovalTransformers
from __data_processor__.models import MetopioTriCountyRemovalDataTransformation

def test_tricounty_removal():
    print("=" * 80)
    print("TRICOUNTY REMOVAL TRANSFORMATION TEST")
    print("=" * 80)
    
    transformer = RemovalTransformers(None)
    
    # Test OLD version
    print("\n[1/3] Testing OLD version...")
    start = time.time()
    result_old = transformer.transform_Tri_County_Removal()
    time_old = time.time() - start
    
    if not result_old:
        print("❌ OLD version failed!")
        return
    
    old_count = MetopioTriCountyRemovalDataTransformation.objects.count()
    old_total = sum(r.value for r in MetopioTriCountyRemovalDataTransformation.objects.all())
    print(f"✓ OLD: {old_count} records, total value: {old_total}, time: {time_old:.2f}s")
    
    # Save old records for comparison
    old_records = {
        (r.layer, r.geoid, r.topic, r.stratification, r.period, r.value)
        for r in MetopioTriCountyRemovalDataTransformation.objects.all()
    }
    
    # Test OPTIMIZED version
    print("\n[2/3] Testing OPTIMIZED version...")
    start = time.time()
    result_new = transformer.transform_Tri_County_Removal_OPTIMIZED()
    time_new = time.time() - start
    
    if not result_new:
        print("❌ OPTIMIZED version failed!")
        return
    
    new_count = MetopioTriCountyRemovalDataTransformation.objects.count()
    new_total = sum(r.value for r in MetopioTriCountyRemovalDataTransformation.objects.all())
    print(f"✓ OPTIMIZED: {new_count} records, total value: {new_total}, time: {time_new:.2f}s")
    
    # Save new records for comparison
    new_records = {
        (r.layer, r.geoid, r.topic, r.stratification, r.period, r.value)
        for r in MetopioTriCountyRemovalDataTransformation.objects.all()
    }
    
    # Compare results
    print("\n[3/3] Comparing results...")
    print(f"   Record count: OLD={old_count}, NEW={new_count}")
    print(f"   Total value: OLD={old_total}, NEW={new_total}")
    print(f"   Speed: {time_old/time_new:.1f}x faster")
    
    if old_records == new_records:
        print("\n✅ ✅ ✅ PERFECT MATCH! All records identical.")
        print("The OPTIMIZED version produces IDENTICAL results!")
    else:
        missing_in_new = old_records - new_records
        extra_in_new = new_records - old_records
        if missing_in_new:
            print(f"\n⚠️  {len(missing_in_new)} records in OLD but not in NEW")
        if extra_in_new:
            print(f"⚠️  {len(extra_in_new)} records in NEW but not in OLD")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_tricounty_removal()
