"""
Simple comparison test - OLD vs OPTIMIZED (no emoji to avoid encoding issues)
"""
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_data_project.settings')
django.setup()

from __data_processor__.transformers.removal_transformers import RemovalTransformers
from __data_processor__.models import ZipCodeLayerRemovalData

transformer = RemovalTransformers(None)

print("="*80)
print("RUNNING OLD VERSION")
print("="*80)
start = time.time()
transformer.transform_Zipcode_Layer_Removal()
time_old = time.time() - start
old_records = list(ZipCodeLayerRemovalData.objects.all().order_by('geoid', 'stratification', 'period'))
old_count = len(old_records)
old_total = sum(r.value for r in old_records)
print(f"OLD: {old_count} records, total value: {old_total}, time: {time_old:.2f}s")

print("\n" + "="*80)
print("RUNNING OPTIMIZED VERSION")
print("="*80)
start = time.time()
transformer.transform_Zipcode_Layer_Removal_OPTIMIZED()
time_new = time.time() - start
new_records = list(ZipCodeLayerRemovalData.objects.all().order_by('geoid', 'stratification', 'period'))
new_count = len(new_records)
new_total = sum(r.value for r in new_records)
print(f"NEW: {new_count} records, total value: {new_total}, time: {time_new:.2f}s")

print("\n" + "="*80)
print("COMPARISON")
print("="*80)
print(f"Record count match: {old_count == new_count} (OLD: {old_count}, NEW: {new_count})")
print(f"Total value match: {old_total == new_total} (OLD: {old_total}, NEW: {new_total})")
print(f"Speedup: {time_old/time_new:.1f}x faster")

# Check individual records
print("\n" + "="*80)
print("RECORD-BY-RECORD COMPARISON")
print("="*80)

old_sigs = {(r.layer, r.geoid, r.topic, r.stratification, r.period, r.value) for r in old_records}
new_sigs = {(r.layer, r.geoid, r.topic, r.stratification, r.period, r.value) for r in new_records}

missing_in_new = old_sigs - new_sigs
missing_in_old = new_sigs - old_sigs

if not missing_in_new and not missing_in_old:
    print("PERFECT MATCH! All records identical.")
else:
    print(f"Records in OLD but missing in NEW: {len(missing_in_new)}")
    if missing_in_new:
        for sig in list(missing_in_new)[:5]:
            print(f"  {sig}")
    print(f"Records in NEW but missing in OLD: {len(missing_in_old)}")
    if missing_in_old:
        for sig in list(missing_in_old)[:5]:
            print(f"  {sig}")

print("\n" + "="*80)
if old_count == new_count and old_total == new_total and not missing_in_new and not missing_in_old:
    print("SUCCESS: OPTIMIZED version produces IDENTICAL results!")
else:
    print("FAILURE: Results differ between OLD and OPTIMIZED")
print("="*80)
