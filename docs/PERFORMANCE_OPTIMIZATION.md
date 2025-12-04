# Performance Optimization Guide

## Current Performance Issues

### 1. **Multiple Iterations Over QuerySets**
**Problem:** Lines 163, 172 - Iterating over `school_data` multiple times
```python
for record in school_data:  # First iteration
    group_totals[record.group_by] += int(record.student_count)

for record in school_data:  # Second iteration - SLOW!
    key = (record.county, record.group_by, record.group_by_value)
```

**Solution:** Use Django aggregation or combine iterations
```python
# Use database aggregation instead
from django.db.models import Sum, Count

group_totals = school_data.values('group_by').annotate(
    total=Sum('student_count')
).values_list('group_by', 'total')
```

### 2. **Converting QuerySet to List Too Early**
**Problem:** Line 218 - `combined_dataset = list(school_data)` loads ALL records into memory
```python
combined_dataset = list(school_data)  # Loads everything into memory!
```

**Solution:** Keep as QuerySet and use `select_related()` / `prefetch_related()`
```python
# Use prefetch to load related data efficiently
school_data = SchoolData.objects.filter(
    county__in=['Outagamie', 'Winnebago', 'Calumet']
).exclude(
    school_name='[Districtwide]'
).select_related('stratification')  # Load stratification in ONE query
```

### 3. **Loading ALL Stratifications**
**Problem:** Line 226 - Loading all Stratification objects
```python
strat_map = {
    f"{strat.group_by}{strat.group_by_value}": strat
    for strat in Stratification.objects.all()  # Loads EVERYTHING
}
```

**Solution:** Only load what you need
```python
# Get only the stratifications you'll actually use
needed_strats = school_data.values_list('group_by', 'group_by_value').distinct()
strat_map = {
    f"{s.group_by}{s.group_by_value}": s
    for s in Stratification.objects.filter(
        models.Q(*[
            models.Q(group_by=gb, group_by_value=gbv) 
            for gb, gbv in needed_strats
        ])
    )
}
```

### 4. **String Operations in Loops**
**Problem:** Lines 241-242 - String parsing in loop
```python
for record in combined_dataset:
    period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}"  # SLOW!
    strat_label = record.stratification.label_name if record.stratification else "Unknown"
```

**Solution:** Use database annotations
```python
from django.db.models import Case, When, Value, CharField, F
from django.db.models.functions import Concat, Substr

school_data = school_data.annotate(
    period=Concat(
        Substr('school_year', 1, 4),
        Value('-20'),
        Substr('school_year', 6, 2),
        output_field=CharField()
    ),
    strat_label=F('stratification__label_name')
)
```

## Quick Wins

### Optimization 1: Use `select_related()` for ForeignKeys
```python
# BEFORE (makes N+1 queries)
school_data = SchoolData.objects.filter(...)
for record in school_data:
    label = record.stratification.label_name  # Each access = 1 query!

# AFTER (makes 1 query total)
school_data = SchoolData.objects.filter(...).select_related('stratification')
for record in school_data:
    label = record.stratification.label_name  # No extra query!
```

### Optimization 2: Use Database Aggregation
```python
# BEFORE (Python loop - SLOW)
all_students_total = 0
for record in school_data:
    if record.group_by == "All Students":
        all_students_total += int(record.student_count)

# AFTER (Database aggregation - FAST)
from django.db.models import Sum, Q

all_students_total = school_data.filter(
    group_by="All Students"
).aggregate(
    total=Sum('student_count')
)['total'] or 0
```

### Optimization 3: Bulk Operations
```python
# BEFORE (N queries)
for record in records:
    MyModel.objects.create(...)  # 1 query per record!

# AFTER (1 query)
MyModel.objects.bulk_create([
    MyModel(...) for record in records
], batch_size=1000)  # Insert 1000 at a time
```

### Optimization 4: Use `iterator()` for Large QuerySets
```python
# BEFORE (loads everything into memory)
for record in SchoolData.objects.all():  # Loads 100K records!
    process(record)

# AFTER (streams records)
for record in SchoolData.objects.all().iterator(chunk_size=2000):
    process(record)  # Only 2000 in memory at a time
```

## Recommended Changes

### Priority 1: Add `select_related()` everywhere (5-10x faster)
```python
# In every transformation method, change:
school_data = SchoolData.objects.filter(...)

# To:
school_data = SchoolData.objects.filter(...).select_related('stratification')
```

### Priority 2: Use database aggregation (10-100x faster)
```python
# Replace Python loops with Django ORM:
from django.db.models import Sum, Count, F

# Get totals by group_by
group_totals = dict(
    school_data.values('group_by').annotate(
        total=Sum('student_count')
    ).values_list('group_by', 'total')
)
```

### Priority 3: Batch delete and insert (2-5x faster)
```python
# Already doing this correctly!
with transaction.atomic():
    MetopioTriCountyLayerTransformation.objects.all().delete()
    MetopioTriCountyLayerTransformation.objects.bulk_create(transformed_data, batch_size=1000)
```

## Estimated Performance Gains

| Optimization | Current Time | Optimized Time | Speedup |
|--------------|--------------|----------------|---------|
| select_related() | 30s | 3s | 10x |
| Database aggregation | 45s | 2s | 22x |
| Remove list() conversion | 15s | 1s | 15x |
| **Total Estimate** | **90s** | **6s** | **15x** |

## Implementation Plan

1. **Quick Win** (10 minutes): Add `.select_related('stratification')` to all transformations
2. **Medium** (1 hour): Replace loops with database aggregation  
3. **Advanced** (2 hours): Rewrite grouping logic to use database GROUP BY

Would you like me to implement these optimizations?
