# Forward Exam Data - Technical Implementation Guide

> **Status**: ✅ Database Model Created | 🔄 Upload/Processing Views Pending | ⏳ Transformations Not Started
> 
> **Created**: December 2025  
> **Migration**: 0028_forwardexamdata  
> **Database Table**: `__data_processor__forwardexamdata`

---

## 📋 Table of Contents

1. [Implementation Summary](#implementation-summary)
2. [Database Model](#database-model)
3. [What's Been Created](#whats-been-created)
4. [What's Next](#whats-next)
5. [Model Structure Details](#model-structure-details)
6. [Key Differences from Other Models](#key-differences-from-other-models)
7. [Sample Data Examples](#sample-data-examples)
8. [Usage Patterns](#usage-patterns)
9. [Next Steps Implementation Guide](#next-steps-implementation-guide)

---

## ✅ Implementation Summary

### Completed Work (December 2025)

**Database Infrastructure:**
- ✅ Created `ForwardExamData` model in `__data_processor__/models.py`
- ✅ Generated migration `0028_forwardexamdata.py`
- ✅ Applied migration successfully (table created in database)
- ✅ Registered model in Django admin with custom `ForwardExamDataAdmin` class
- ✅ Added database indexes for query optimization

**Files Modified:**
1. `__data_processor__/models.py` - Added ForwardExamData model (~70 lines)
2. `__data_processor__/admin.py` - Registered ForwardExamDataAdmin
3. `__data_processor__/migrations/0028_forwardexamdata.py` - Database migration

**Data Files Available:**
- `uploads/ForwardReport/2024-2025/forward_certified_2024-25/forward_certified_ELA_RDG_WRT_2024-25.csv`
- `uploads/ForwardReport/2024-2025/forward_certified_2024-25/forward_certified_MTH_SCN_SOC_2024-25.csv`

---

## 🗃️ Database Model

### ForwardExamData Model

The model follows the same pattern as `SchoolData` (enrollment) and `SchoolRemovalData` (discipline), extending the base structure with test-specific fields.

#### Base School/District Fields (Same as existing models)
```python
school_year = models.CharField(max_length=7)  # e.g., "2024-25"
agency_type = models.CharField(max_length=50, blank=True)
cesa = models.CharField(max_length=10, blank=True)
county = models.CharField(max_length=50, blank=True)
district_code = models.CharField(max_length=10)  # Leading zeros stripped in save()
school_code = models.CharField(max_length=10, blank=True)  # Leading zeros stripped
grade_group = models.CharField(max_length=50, blank=True)
charter_ind = models.CharField(max_length=4, blank=True)
district_name = models.CharField(max_length=100)
school_name = models.CharField(max_length=100)
```

#### Test-Specific Fields (Unique to ForwardExamData)
```python
test_subject = models.CharField(max_length=50)  # ELA, Math, Science, Social Studies
grade_level = models.CharField(max_length=50)  # 3, 4, 5, 6, 7, 8
test_result = models.CharField(max_length=50)  # Developing, Approaching, Meeting, Exceeding
test_result_code = models.CharField(max_length=50)  # 1, 2, 3, 4
test_group = models.CharField(max_length=100)  # Forward, DLM
forward_average_scale_score = models.CharField(max_length=10, blank=True, null=True)
```

#### Demographic Grouping Fields (Same as existing models)
```python
group_by = models.CharField(max_length=50)  # All Students, Gender, Ethnicity, etc.
group_by_value = models.CharField(max_length=200)  # All Students, Male, Female, etc.
```

#### Count and Metric Fields
```python
student_count = models.CharField(max_length=20)  # Students in this performance level
percent_of_group = models.CharField(max_length=20)  # Percentage of subgroup
group_count = models.CharField(max_length=20)  # Total students in group
```

#### Linking Fields for Transformations
```python
place = models.CharField(max_length=100, blank=True, null=True)
stratification = models.ForeignKey(Stratification, on_delete=models.SET_NULL, null=True, blank=True)
geoid = models.ForeignKey(CountyGEOID, on_delete=models.SET_NULL, null=True, blank=True)
```

#### Model Meta Configuration
```python
class Meta:
    ordering = ['school_year', 'test_subject', 'grade_level', 'district_name', 'school_name']
    indexes = [
        models.Index(fields=['school_year', 'test_subject']),
        models.Index(fields=['district_code', 'school_code']),
        models.Index(fields=['group_by', 'group_by_value']),
    ]
```

---

## 📦 What's Been Created

### 1. Database Table Structure

**Table Name**: `__data_processor__forwardexamdata`

**Columns** (21 total):
1. `id` - Primary key (auto-generated)
2-10. Base school fields (school_year through school_name)
11-16. Test-specific fields (test_subject through forward_average_scale_score)
17-18. Demographic fields (group_by, group_by_value)
19-21. Count fields (student_count, percent_of_group, group_count)
22-24. Linking fields (place, stratification_id, geoid_id)

**Indexes Created**:
- Primary key index on `id`
- Composite index on `(school_year, test_subject)` - For subject-specific queries
- Composite index on `(district_code, school_code)` - For school lookups
- Composite index on `(group_by, group_by_value)` - For demographic filtering

**Foreign Key Constraints**:
- `stratification_id` → `__data_processor__stratification.id` (SET_NULL)
- `geoid_id` → `__data_processor__countygeoid.id` (SET_NULL)

### 2. Admin Interface Configuration

**Admin Class**: `ForwardExamDataAdmin`

**Features**:
```python
list_display = (
    'school_year', 'test_subject', 'grade_level', 
    'district_name', 'school_name', 
    'test_result', 'student_count'
)

list_filter = (
    'school_year', 'test_subject', 'grade_level', 
    'test_result', 'test_group', 'group_by'
)

search_fields = (
    'district_name', 'school_name', 
    'county', 'test_result'
)
```

**Admin URL**: `http://localhost:8000/admin/__data_processor__/forwardexamdata/`

### 3. Custom Model Methods

**save() Method**:
```python
def save(self, *args, **kwargs):
    """Strip leading zeros from district and school codes"""
    if self.district_code:
        self.district_code = self.district_code.lstrip('0')
    if self.school_code:
        self.school_code = self.school_code.lstrip('0')
    super().save(*args, **kwargs)
```

**Purpose**: Ensures consistency with other models and lookup files

---

## 🔄 What's Next

### Immediate Next Steps (Required for functionality)

#### Step 1: Update Forms
**File**: `__data_processor__/forms.py`

Add Forward Exam file upload field:
```python
class UploadFileForm(forms.Form):
    # Existing fields...
    enrollment_file = forms.FileField(required=False, label="Enrollment Data")
    removal_file = forms.FileField(required=False, label="Removal Data")
    
    # NEW: Add this field
    forward_exam_file = forms.FileField(required=False, label="Forward Exam Data (ELA/MTH)")
```

#### Step 2: Create Upload Handler in Views
**File**: `__data_processor__/views.py`

Create function similar to `load_school_removal_data()`:
```python
def load_forward_exam_data(file):
    """Load Forward Exam data from CSV file"""
    # 1. Delete existing data
    ForwardExamData.objects.all().delete()
    
    # 2. Build stratification lookup map
    strat_map = {
        f"{strat.group_by}{strat.group_by_value}": strat
        for strat in Stratification.objects.all()
    }
    
    # 3. Read CSV and create ForwardExamData records
    with open(file, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        data = []
        
        for row in reader:
            # Skip suppressed values
            if row["STUDENT_COUNT"] in ["*", "0", ""]:
                continue
            
            # Map to stratification
            group_by = "Grade Level" if row["GROUP_BY"] == "Grade" else row["GROUP_BY"]
            combined_key = group_by + row["GROUP_BY_VALUE"]
            stratification = strat_map.get(combined_key)
            
            data.append(ForwardExamData(
                school_year=row["SCHOOL_YEAR"],
                agency_type=row["AGENCY_TYPE"],
                cesa=row["CESA"],
                county=row["COUNTY"],
                district_code=row["DISTRICT_CODE"],
                school_code=row["SCHOOL_CODE"],
                grade_group=row["GRADE_GROUP"],
                charter_ind=row["CHARTER_IND"],
                district_name=row["DISTRICT_NAME"],
                school_name=row["SCHOOL_NAME"],
                test_subject=row["TEST_SUBJECT"],
                grade_level=row["GRADE_LEVEL"],
                test_result=row["TEST_RESULT"],
                test_result_code=row["TEST_RESULT_CODE"],
                test_group=row["TEST_GROUP"],
                group_by=group_by,
                group_by_value=row["GROUP_BY_VALUE"],
                student_count=row["STUDENT_COUNT"],
                percent_of_group=row["PERCENT_OF_GROUP"],
                group_count=row["GROUP_COUNT"],
                forward_average_scale_score=row.get("FORWARD_AVERAGE_SCALE_SCORE", ""),
                stratification=stratification
            ))
        
        # 4. Bulk create records
        ForwardExamData.objects.bulk_create(data)
    
    return len(data)
```

#### Step 3: Update handle_uploaded_file() Function
Add Forward Exam processing:
```python
def handle_uploaded_file(form):
    # Existing enrollment and removal processing...
    
    # NEW: Add Forward Exam processing
    forward_exam_file = form.cleaned_data.get('forward_exam_file')
    if forward_exam_file:
        file_path = save_uploaded_file(forward_exam_file, 'forward_exam')
        records_loaded = load_forward_exam_data(file_path)
        messages.append(f"Forward Exam: {records_loaded} records loaded")
    
    return messages
```

#### Step 4: Create Transformation Functions
**File**: `__data_processor__/transformers.py`

Follow pattern from existing transformation functions:
- `transform_ForwardExam_Statewide()`
- `transform_ForwardExam_TriCounty()`
- `transform_ForwardExam_County()`
- `transform_ForwardExam_ZipCode()`
- `transform_ForwardExam_City()`

#### Step 5: Create Output Models
Create transformation output models similar to removal data:
```python
class ForwardExamStateWideTransformation(models.Model):
    school_year = models.CharField(max_length=7)
    test_subject = models.CharField(max_length=50)
    grade_level = models.CharField(max_length=50)
    test_result = models.CharField(max_length=50)
    stratification = models.ForeignKey(Stratification)
    layer = models.CharField(max_length=50)
    geoid = models.CharField(max_length=50)
    topic = models.CharField(max_length=50)
    period = models.CharField(max_length=9)
    value = models.CharField(max_length=20)
    # ... similar structure for other layers
```

---

## 🏗️ Model Structure Details

### Model Comparison Matrix

| Feature | SchoolData | SchoolRemovalData | **ForwardExamData** |
|---------|-----------|------------------|---------------------|
| **Base Fields** (school_year, district, school, etc.) | ✅ | ✅ | ✅ |
| **Demographic Fields** (group_by, group_by_value) | ✅ | ✅ | ✅ |
| **Stratification FK** | ✅ | ✅ | ✅ |
| **CountyGEOID FK** | ✅ | ✅ | ✅ |
| **Domain-Specific Fields** | student_count | removal_type, removal_count | **test_subject, grade_level, test_result, test_group, scale_score** |
| **Count Field** | student_count | removal_count | student_count (by performance level) |
| **Percentage Field** | percent_of_group | percent_of_group | percent_of_group |
| **Group Count** | group_count | group_count | group_count |

### Field Mappings: CSV → Model

| CSV Column | Model Field | Notes |
|------------|------------|-------|
| SCHOOL_YEAR | school_year | e.g., "2024-25" |
| AGENCY_TYPE | agency_type | School/district type |
| CESA | cesa | Cooperative Educational Service Agency |
| COUNTY | county | County of main district office |
| DISTRICT_CODE | district_code | **Leading zeros stripped in save()** |
| SCHOOL_CODE | school_code | **Leading zeros stripped in save()** |
| GRADE_GROUP | grade_group | School grade group |
| CHARTER_IND | charter_ind | Charter indicator |
| DISTRICT_NAME | district_name | District name |
| SCHOOL_NAME | school_name | School name |
| **TEST_SUBJECT** | **test_subject** | **ELA, Math, Science, Social Studies** |
| **GRADE_LEVEL** | **grade_level** | **3, 4, 5, 6, 7, 8** |
| **TEST_RESULT** | **test_result** | **Developing, Approaching, Meeting, Exceeding** |
| **TEST_RESULT_CODE** | **test_result_code** | **1, 2, 3, 4** |
| **TEST_GROUP** | **test_group** | **Forward, DLM** |
| GROUP_BY | group_by | **"Grade" mapped to "Grade Level"** |
| GROUP_BY_VALUE | group_by_value | Demographic value |
| STUDENT_COUNT | student_count | **Skip if "*", "0", or empty** |
| PERCENT_OF_GROUP | percent_of_group | Percentage |
| GROUP_COUNT | group_count | Total in group |
| **FORWARD_AVERAGE_SCALE_SCORE** | **forward_average_scale_score** | **Mean scale score** |

---

## 📊 Sample Data Examples

### Input CSV Sample (ELA File)
```csv
SCHOOL_YEAR,AGENCY_TYPE,CESA,COUNTY,DISTRICT_CODE,SCHOOL_CODE,GRADE_GROUP,CHARTER_IND,DISTRICT_NAME,SCHOOL_NAME,TEST_SUBJECT,GRADE_LEVEL,TEST_RESULT,TEST_RESULT_CODE,TEST_GROUP,GROUP_BY,GROUP_BY_VALUE,STUDENT_COUNT,PERCENT_OF_GROUP,GROUP_COUNT,FORWARD_AVERAGE_SCALE_SCORE
2024-25,,,,0,,[All],,[Statewide],[Statewide],ELA,3,Developing,1,DLM,All Students,All Students,313,74.52,420,
2024-25,,,,0,,[All],,[Statewide],[Statewide],ELA,3,Approaching,2,DLM,All Students,All Students,63,15,420,
2024-25,,,,0,,[All],,[Statewide],[Statewide],ELA,3,Meeting,3,DLM,All Students,All Students,41,9.76,420,
2024-25,,,,3619,1260,[PK-05],No,Appleton Area,Edison Elementary,ELA,3,Below Basic,1,Forward,Gender,Female,42,30.66,137,2305
2024-25,,,,3619,1260,[PK-05],No,Appleton Area,Edison Elementary,ELA,3,Basic,2,Forward,Gender,Female,45,32.85,137,2440
```

### Database Record Example
```python
# Statewide DLM result
ForwardExamData(
    school_year="2024-25",
    district_code="0",
    district_name="[Statewide]",
    school_name="[Statewide]",
    test_subject="ELA",
    grade_level="3",
    test_result="Developing",
    test_result_code="1",
    test_group="DLM",
    group_by="All Students",
    group_by_value="All Students",
    student_count="313",
    percent_of_group="74.52",
    group_count="420",
    stratification=<Stratification: All Students>
)

# School-level Forward Exam result
ForwardExamData(
    school_year="2024-25",
    district_code="3619",  # Leading zero stripped
    school_code="1260",
    district_name="Appleton Area",
    school_name="Edison Elementary",
    test_subject="ELA",
    grade_level="3",
    test_result="Below Basic",
    test_result_code="1",
    test_group="Forward",
    group_by="Gender",
    group_by_value="Female",
    student_count="42",
    percent_of_group="30.66",
    group_count="137",
    forward_average_scale_score="2305",
    stratification=<Stratification: FEM3 - Gender: Female>
)
```

---

## 🔍 Usage Patterns

### Understanding the Data Structure

**Important Notes on GROUP_COUNT and Percentages:**

The Forward Exam data has a hierarchical structure for calculating percentages:

1. **"All Students" Records**: When `GROUP_BY = "All Students"` AND `GROUP_BY_VALUE = "All Students"`, the `GROUP_COUNT` column contains the **total student count** for that test/grade combination.

2. **Stratified Records**: For other stratifications (e.g., `GROUP_BY = "Disability Status"`, `GROUP_BY_VALUE = "SwD"`), the `STUDENT_COUNT` represents students in that subgroup, and `GROUP_COUNT` is the total for that GROUP_BY category.

3. **Percentage Calculation**: The `PERCENT_OF_GROUP` column is calculated as:
   ```
   PERCENT_OF_GROUP = (STUDENT_COUNT / GROUP_COUNT from "All Students" record) × 100
   ```

4. **Transformation Output**: Our transformation outputs the **raw aggregated STUDENT_COUNT** (not percentages). Metopio handles percentage calculations on their end by dividing by the "All Students" total.

**Example from actual data:**
```csv
GROUP_BY,GROUP_BY_VALUE,TEST_RESULT,STUDENT_COUNT,PERCENT_OF_GROUP,GROUP_COUNT
All Students,All Students,Meeting,1500,35.5,4225        <- Total students
Disability Status,SwD,Meeting,250,5.9,4225              <- SwD students (250/4225 = 5.9%)
Gender,Female,Meeting,780,18.5,4225                     <- Female students (780/4225 = 18.5%)
```

### Admin Interface Queries

**View all Grade 3 ELA results:**
1. Go to http://localhost:8000/admin/__data_processor__/forwardexamdata/
2. Filter by:
   - Test subject: ELA
   - Grade level: 3

**Search for specific school:**
1. Use search box: "Edison Elementary"
2. Results show all test results for that school

**Filter by performance level:**
1. Use "Test result" filter: "Meeting"
2. Shows all students meeting proficiency standards

### Django ORM Query Examples

```python
# Get all ELA Grade 3 results
grade3_ela = ForwardExamData.objects.filter(
    test_subject="ELA",
    grade_level="3"
)

# Get proficient students (Meeting or Exceeding)
proficient = ForwardExamData.objects.filter(
    test_result__in=["Meeting", "Exceeding", "Proficient", "Advanced"]
)

# Get DLM alternate assessment results
dlm_results = ForwardExamData.objects.filter(test_group="DLM")

# Get results for specific county
outagamie_results = ForwardExamData.objects.filter(county="Outagamie")

# Calculate proficiency rate for a school
school_data = ForwardExamData.objects.filter(
    district_code="3619",
    school_code="1260",
    test_subject="ELA",
    grade_level="3",
    group_by="All Students"
)

proficient_count = school_data.filter(
    test_result__in=["Meeting", "Exceeding"]
).aggregate(Sum('student_count'))

total_count = school_data.first().group_count
proficiency_rate = (proficient_count / total_count) * 100
```

---

## 🚀 Next Steps Implementation Guide

### Phase 1: File Upload Functionality (Priority: HIGH)

**Estimated Time**: 2-3 hours

**Tasks**:
1. ✅ Create `ForwardExamData` model
2. ✅ Apply migration
3. ✅ Register in admin
4. 🔄 Add `forward_exam_file` field to `UploadFileForm`
5. 🔄 Create `load_forward_exam_data()` function in views.py
6. 🔄 Update `handle_uploaded_file()` to process Forward Exam files
7. 🔄 Test file upload with ELA and MTH files

**Testing Checklist**:
- [ ] Upload ELA file successfully
- [ ] Upload MTH file successfully
- [ ] Verify records in admin interface
- [ ] Check stratification mappings
- [ ] Validate leading zero stripping
- [ ] Confirm suppressed values (*) are skipped

### Phase 2: Data Transformation (Priority: MEDIUM)

**Estimated Time**: 4-6 hours

**Tasks**:
1. Create `transform_ForwardExam_Statewide()` function
2. Create `transform_ForwardExam_TriCounty()` function
3. Create `transform_ForwardExam_County()` function
4. Create `transform_ForwardExam_ZipCode()` function
5. Create `transform_ForwardExam_City()` function
6. Create output models for each layer
7. Test transformations with sample data

**Key Requirements**:
- Filter: `GRADE_LEVEL = 3`, `TEST_GROUP = 'Forward'`, `TEST_RESULT` in ['Meeting', 'Exceeding', 'Proficient', 'Advanced']
- Calculate: `value = STUDENT_COUNT / STUDENT_COUNT for "All Students" group` (proficiency rate)
- Period format: "2024-25" → "2023-2024" (insert '20' before second year)

### Phase 3: Display and Export (Priority: MEDIUM)

**Estimated Time**: 3-4 hours

**Tasks**:
1. Create view function to display Forward Exam data
2. Create template with pagination
3. Add filtering by subject, grade, test result
4. Implement CSV export functionality
5. Implement Excel export functionality
6. Add URL routing

### Phase 4: Integration and Testing (Priority: HIGH)

**Estimated Time**: 2-3 hours

**Tasks**:
1. Integration testing with all data types
2. Performance testing with large datasets
3. Validation against WISEdash source data
4. User acceptance testing
5. Documentation updates

---

## 📝 Notes and Considerations

### Data Quality Checks

1. **Suppressed Values**: Rows with `STUDENT_COUNT` = "*" or "0" should be skipped during upload
2. **Leading Zeros**: Automatically stripped from district/school codes in `save()` method
3. **Group_By Mapping**: "Grade" should be mapped to "Grade Level" to match stratification file
4. **Stratification Linking**: Some records may not have matching stratifications (FK set to NULL)
5. **Migrant Status Exclusion**: Records with `GROUP_BY = 'Migrant Status'` are excluded from transformations

### Performance Levels by Test Group

**Forward Exam (Regular Assessment)**:
- Below Basic (Code 1) - Not proficient
- Basic (Code 2) - Not proficient
- Advanced (Code 3) - **Proficient** ✅
- Meeting (Code 4) - **Proficient** ✅

**DLM (Alternate Assessment for students with significant cognitive disabilities)**:
- Developing (Code 1) - Not proficient
- Approaching (Code 2) - Not proficient
- Meeting (Code 3) - **Proficient** ✅

**Note**: The PP-10a spec specifies using only "Meeting" and "Advanced" test results for proficiency calculations. These are the students who met or exceeded grade-level standards.

### Value Field Explanation

**Important**: The `value` field in transformation models contains the **raw aggregated STUDENT_COUNT**, NOT a percentage.

**Why?**
- Metopio calculates percentages on their end
- The calculation formula: `(value / total_all_students) × 100`
- We provide the numerator (proficient student count)
- Metopio has the denominator (total "All Students" count)

**Example**:
```
Stratification: "Disability Status - SwD"
Value: 250  (250 SwD students scored Meeting/Advanced)
Metopio will calculate: 250 / 4225 (All Students) = 5.9%
```

This matches the pattern used in removal transformations where we sum `removal_count`, not calculate percentages.

### Test Subjects

- **ELA**: English Language Arts (Reading, Writing)
- **Math**: Mathematics
- **Science**: Science
- **Social Studies**: Social Studies

### Grade Levels

- Grades 3-8 (elementary and middle school)
- Specific grade, not just grade group

---

## 🔗 Related Documentation

- [Original Specification](PP-10a Publicschool Forward Exam.md) - Fox Valley Data Exchange requirements
- [Project Structure](PROJECT_STRUCTURE.md) - Complete project organization
- [User Guide](USER_GUIDE.md) - How to use the application
- [API Documentation](API.md) - Technical API reference
- [Roadmap](ROADMAP.md) - Future enhancements

---

## 📈 Database Statistics

**Migration**: 0028_forwardexamdata  
**Table**: `__data_processor__forwardexamdata`  
**Columns**: 24 (21 data fields + id + 2 foreign keys)  
**Indexes**: 4 (primary key + 3 composite indexes)  
**Foreign Keys**: 2 (stratification, geoid)  

**Expected Record Counts** (per year):
- ELA file: ~200,000+ records
- MTH file: ~600,000+ records (Math + Science + Social Studies)
- Total: ~800,000+ records per year

---

**Document Created**: December 2025  
**Last Updated**: December 2025  
**Author**: GitHub Copilot  
**Status**: Model Complete - Implementation Pending
