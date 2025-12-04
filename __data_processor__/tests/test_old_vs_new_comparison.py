"""
Comprehensive validation test comparing OLD vs OPTIMIZED zipcode removal transformation
Checks every record, every attribute, and all totals
"""
import os
import django
import time
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_data_project.settings')
django.setup()

from __data_processor__.transformers.removal_transformers import RemovalTransformers
from __data_processor__.models import ZipCodeLayerRemovalData

def get_record_signature(record):
    """Create a unique signature for a record"""
    return (
        record.layer,
        record.geoid,
        record.topic,
        record.stratification,
        record.period,
        record.value
    )

def run_comparison_test():
    print("=" * 100)
    print("COMPREHENSIVE COMPARISON TEST - OLD vs OPTIMIZED")
    print("=" * 100)
    
    transformer = RemovalTransformers(None)
    
    # ========================================
    # RUN OLD VERSION
    # ========================================
    print("\n" + "=" * 100)
    print("STEP 1: Running OLD version...")
    print("=" * 100)
    start = time.time()
    result_old = transformer.transform_Zipcode_Layer_Removal()
    time_old = time.time() - start
    
    if not result_old:
        print("FAIL: OLD version failed!")
        return
    
    # Fetch all records from OLD version
    old_records = list(ZipCodeLayerRemovalData.objects.all().order_by('geoid', 'stratification', 'period'))
    old_count = len(old_records)
    
    # Create lookup structures for OLD data
    old_by_signature = {}
    old_by_geoid = defaultdict(list)
    old_by_stratification = defaultdict(list)
    old_totals_by_geoid = defaultdict(int)
    old_totals_by_strat = defaultdict(int)
    
    for record in old_records:
        sig = get_record_signature(record)
        old_by_signature[sig] = record
        old_by_geoid[record.geoid].append(record)
        old_by_stratification[record.stratification].append(record)
        old_totals_by_geoid[record.geoid] += record.value
        old_totals_by_strat[record.stratification] += record.value
    
    print(f"PASS: OLD version completed in {time_old:.2f}s")
    print(f"   Records created: {old_count}")
    print(f"   Unique GEOIDs: {len(old_by_geoid)}")
    print(f"   Unique Stratifications: {len(old_by_stratification)}")
    print(f"   Total value sum: {sum(old_totals_by_geoid.values())}")
    
    # ========================================
    # RUN OPTIMIZED VERSION
    # ========================================
    print("\n" + "=" * 100)
    print("STEP 2: Running OPTIMIZED version...")
    print("=" * 100)
    start = time.time()
    result_new = transformer.transform_Zipcode_Layer_Removal_OPTIMIZED()
    time_new = time.time() - start
    
    if not result_new:
        print("FAIL: OPTIMIZED version failed!")
        return
    
    # Fetch all records from OPTIMIZED version
    new_records = list(ZipCodeLayerRemovalData.objects.all().order_by('geoid', 'stratification', 'period'))
    new_count = len(new_records)
    
    # Create lookup structures for NEW data
    new_by_signature = {}
    new_by_geoid = defaultdict(list)
    new_by_stratification = defaultdict(list)
    new_totals_by_geoid = defaultdict(int)
    new_totals_by_strat = defaultdict(int)
    
    for record in new_records:
        sig = get_record_signature(record)
        new_by_signature[sig] = record
        new_by_geoid[record.geoid].append(record)
        new_by_stratification[record.stratification].append(record)
        new_totals_by_geoid[record.geoid] += record.value
        new_totals_by_strat[record.stratification] += record.value
    
    print(f"PASS: OPTIMIZED version completed in {time_new:.2f}s")
    print(f"   Records created: {new_count}")
    print(f"   Unique GEOIDs: {len(new_by_geoid)}")
    print(f"   Unique Stratifications: {len(new_by_stratification)}")
    print(f"   Total value sum: {sum(new_totals_by_geoid.values())}")
    print(f"   Speedup: {time_old/time_new:.1f}x faster")
    
    # ========================================
    # DETAILED COMPARISON
    # ========================================
    print("\n" + "=" * 100)
    print("STEP 3: DETAILED COMPARISON")
    print("=" * 100)
    
    errors = []
    warnings = []
    
    # Check 1: Record count
    print("\nCHECK 1: Record Count")
    if old_count == new_count:
        print(f"   PASS - Both have {old_count} records")
    else:
        error = f"   FAIL - OLD: {old_count}, NEW: {new_count} (diff: {abs(old_count - new_count)})"
        print(error)
        errors.append(error)
    
    # Check 2: Exact record matching (attribute by attribute)
    print("\nCHECK 2: Exact Record Matching (All Attributes)")
    missing_in_new = []
    missing_in_old = []
    
    for sig, old_rec in old_by_signature.items():
        if sig not in new_by_signature:
            missing_in_new.append(sig)
    
    for sig, new_rec in new_by_signature.items():
        if sig not in old_by_signature:
            missing_in_old.append(sig)
    
    if not missing_in_new and not missing_in_old:
        print(f"   PASS - All {len(old_by_signature)} records match exactly")
    else:
        if missing_in_new:
            error = f"   FAIL - {len(missing_in_new)} records in OLD but missing in NEW"
            print(error)
            errors.append(error)
            print("   First 5 missing records:")
            for sig in missing_in_new[:5]:
                print(f"      {sig}")
        
        if missing_in_old:
            error = f"   FAIL - {len(missing_in_old)} records in NEW but missing in OLD"
            print(error)
            errors.append(error)
            print("   First 5 extra records:")
            for sig in missing_in_old[:5]:
                print(f"      {sig}")
    
    # Check 3: GEOID totals
    print("\nCHECK 3: GEOID Totals")
    geoid_mismatches = []
    
    all_geoids = set(old_totals_by_geoid.keys()) | set(new_totals_by_geoid.keys())
    for geoid in sorted(all_geoids):
        old_total = old_totals_by_geoid.get(geoid, 0)
        new_total = new_totals_by_geoid.get(geoid, 0)
        
        if old_total != new_total:
            geoid_mismatches.append((geoid, old_total, new_total))
    
    if not geoid_mismatches:
        print(f"   PASS - All {len(all_geoids)} GEOID totals match")
    else:
        error = f"   FAIL - {len(geoid_mismatches)} GEOIDs have different totals"
        print(error)
        errors.append(error)
        print("   Mismatched GEOIDs:")
        for geoid, old_t, new_t in geoid_mismatches[:10]:
            print(f"      GEOID {geoid}: OLD={old_t}, NEW={new_t}, DIFF={abs(old_t - new_t)}")
    
    # Check 4: Stratification totals
    print("\nCHECK 4: Stratification Totals")
    strat_mismatches = []
    
    all_strats = set(old_totals_by_strat.keys()) | set(new_totals_by_strat.keys())
    for strat in sorted(all_strats):
        old_total = old_totals_by_strat.get(strat, 0)
        new_total = new_totals_by_strat.get(strat, 0)
        
        if old_total != new_total:
            strat_mismatches.append((strat, old_total, new_total))
    
    if not strat_mismatches:
        print(f"   PASS - All {len(all_strats)} stratification totals match")
    else:
        error = f"   FAIL - {len(strat_mismatches)} stratifications have different totals"
        print(error)
        errors.append(error)
        print("   Mismatched Stratifications:")
        for strat, old_t, new_t in strat_mismatches[:10]:
            print(f"      {strat}: OLD={old_t}, NEW={new_t}, DIFF={abs(old_t - new_t)}")
    
    # Check 5: Grand total
    print("\nCHECK 5: Grand Total")
    old_grand_total = sum(r.value for r in old_records)
    new_grand_total = sum(r.value for r in new_records)
    
    if old_grand_total == new_grand_total:
        print(f"   PASS - Both have grand total: {old_grand_total}")
    else:
        error = f"   FAIL - OLD: {old_grand_total}, NEW: {new_grand_total}, DIFF: {abs(old_grand_total - new_grand_total)}"
        print(error)
        errors.append(error)
    
    # Check 6: Attribute-level validation for matching records
    print("\nCHECK 6: Attribute-Level Validation")
    attr_mismatches = 0
    
    for sig in old_by_signature:
        if sig in new_by_signature:
            old_rec = old_by_signature[sig]
            new_rec = new_by_signature[sig]
            
            # Check each attribute
            if old_rec.layer != new_rec.layer:
                attr_mismatches += 1
                print(f"   FAIL: Layer mismatch: {sig}")
            if old_rec.geoid != new_rec.geoid:
                attr_mismatches += 1
                print(f"   FAIL: GEOID mismatch: {sig}")
            if old_rec.topic != new_rec.topic:
                attr_mismatches += 1
                print(f"   FAIL: Topic mismatch: {sig}")
            if old_rec.stratification != new_rec.stratification:
                attr_mismatches += 1
                print(f"   FAIL: Stratification mismatch: {sig}")
            if old_rec.period != new_rec.period:
                attr_mismatches += 1
                print(f"   FAIL: Period mismatch: {sig}")
            if old_rec.value != new_rec.value:
                attr_mismatches += 1
                print(f"   FAIL: Value mismatch: {sig} - OLD: {old_rec.value}, NEW: {new_rec.value}")
    
    if attr_mismatches == 0:
        print(f"   PASS - All attributes match for all records")
    else:
        error = f"   FAIL - {attr_mismatches} attribute mismatches found"
        print(error)
        errors.append(error)
    
    # Check 7: Sample record inspection
    print("\nCHECK 7: Sample Record Inspection")
    print("   First 3 records from OLD:")
    for i, rec in enumerate(old_records[:3], 1):
        print(f"      {i}. GEOID={rec.geoid}, Strat={rec.stratification}, Period={rec.period}, Value={rec.value}")
    
    print("   First 3 records from NEW:")
    for i, rec in enumerate(new_records[:3], 1):
        print(f"      {i}. GEOID={rec.geoid}, Strat={rec.stratification}, Period={rec.period}, Value={rec.value}")
    
    # ========================================
    # FINAL SUMMARY
    # ========================================
    print("\n" + "=" * 100)
    print("FINAL SUMMARY")
    print("=" * 100)
    
    print(f"\nPerformance:")
    print(f"   OLD method:       {time_old:.2f}s")
    print(f"   OPTIMIZED method: {time_new:.2f}s")
    print(f"   Speedup:          {time_old/time_new:.1f}x faster")
    
    print(f"\nData Quality:")
    if not errors:
        print("   ALL CHECKS PASSED!")
        print("   The OPTIMIZED version produces IDENTICAL results to the OLD version")
        print("   Every record, every attribute, and all totals match perfectly!")
    else:
        print(f"   FAIL: {len(errors)} validation errors found:")
        for error in errors:
            print(f"      {error}")
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    run_comparison_test()
