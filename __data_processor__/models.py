from django.db import models

class Stratification(models.Model):
    group_by = models.CharField(max_length=100, default="Default Group")
    group_by_value = models.CharField(max_length=200, default="Default Group")
    label_name = models.CharField(max_length=200, default="Default Group")

    def __str__(self):
        return f"{self.group_by} - {self.group_by_value}"

class CountyGEOID(models.Model):
    layer = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    geoid = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return f"{self.layer} - {self.name} - {self.geoid}"
#SchoolAddressFile model is being used for the ZipCodeLayerTransformation model   
class SchoolAddressFile(models.Model):
    lea_code = models.CharField(max_length=10, verbose_name="LEA Code")  # Unique constraint for one to many relationship
    district_name = models.CharField(max_length=255, verbose_name="District Name")
    school_code = models.CharField(max_length=10, verbose_name="School Code")  # Unique constraint for one to many relationship    
    school_name = models.CharField(max_length=255, verbose_name="School Name")
    organization_type = models.CharField(max_length=100, verbose_name="Organization Type")
    school_type = models.CharField(max_length=100, verbose_name="School Type")
    low_grade = models.CharField(max_length=10, verbose_name="Low Grade")
    high_grade = models.CharField(max_length=10, verbose_name="High Grade")
    address = models.CharField(max_length=255, verbose_name="Address")
    city = models.CharField(max_length=100, verbose_name="City")
    state = models.CharField(max_length=2, verbose_name="State")
    zip_code = models.CharField(max_length=10, verbose_name="Zip")
    cesa = models.CharField(max_length=10, verbose_name="CESA")
    locale = models.CharField(max_length=100, verbose_name="Locale")
    county = models.CharField(max_length=100, verbose_name="County")
    current_status = models.CharField(max_length=50, verbose_name="Current Status")
    categories_and_programs = models.TextField(null=True, blank=True, verbose_name="Categories And Programs")
    virtual_school = models.CharField(max_length=50, null=True, blank=True, verbose_name="Virtual School")
    ib_program = models.CharField(max_length=50, null=True, blank=True, verbose_name="IB Program")
    phone_number = models.CharField(max_length=20, verbose_name="Phone Number")
    fax_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="Fax Number")
    charter_status = models.BooleanField(verbose_name="Charter Status")
    website_url = models.URLField(max_length=255, null=True, blank=True, verbose_name="Website URL")

    def __str__(self):
        return f"{self.school_name} ({self.district_name})"
    
    def save(self, *args, **kwargs):
        self.school_code = self.school_code.lstrip("0")
        self.lea_code = self.lea_code.lstrip("0")
        super(SchoolAddressFile, self).save(*args, **kwargs)
    
# Main Model is the School Data Model
class SchoolData(models.Model):
    school_year = models.CharField(max_length=7)
    agency_type = models.CharField(max_length=50)
    cesa = models.CharField(max_length=10)
    county = models.CharField(max_length=50)
    district_code = models.CharField(max_length=10)
    school_code = models.CharField(max_length=10)
    grade_group = models.CharField(max_length=50)
    charter_ind = models.CharField(max_length=4)
    district_name = models.CharField(max_length=100)
    school_name = models.CharField(max_length=100)
    group_by = models.CharField(max_length=50)
    group_by_value = models.CharField(max_length=200)
    student_count = models.CharField(max_length=20)
    percent_of_group = models.CharField(max_length=20)
    place = models.CharField(max_length=100, null=True, blank=True)
    stratification = models.ForeignKey(Stratification, on_delete=models.SET_NULL, null=True, blank=True)
    geoid = models.ForeignKey(CountyGEOID, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return f"{self.county} - {self.student_count}"

    #REMOVING LEADING ZEROS FROM THE SCHOOL_CODE AND DISTRICT_CODE
    def save(self, *args, **kwargs):
        self.school_code = self.school_code.lstrip("0")
        self.district_code = self.district_code.lstrip("0")
        super(SchoolData, self).save(*args, **kwargs)


class TransformedSchoolData(models.Model):
    year = models.CharField(max_length=7)
    year_range = models.CharField(max_length=50)
    place = models.CharField(max_length=100, null=True, blank=True)
    group_by = models.CharField(max_length=50)
    group_by_value = models.CharField(max_length=200)
    student_count = models.CharField(max_length=20)

    class Meta:
        ordering = ['year']  # Default ordering by 'year' field

# Metopio Data Transformation Models
class MetopioStateWideLayerTransformation(models.Model):
    layer = models.CharField(max_length=50, default='State')  # Constant value: 'State'
    geoid = models.CharField(max_length=50, default='WI')  # Constant value: 'wisconsin'
    topic = models.CharField(max_length=50, default='FVDEYLCV')  # Constant value: 'FVDEYLCV'
    stratification = models.TextField(blank=True)  # To store stratification notes
    period = models.CharField(max_length=20)  # Transformed SCHOOL_YEAR (e.g., 2023-24 → 2023-2024)
    value = models.PositiveIntegerField()  # Derived from STUDENT_COUNT

    class Meta:
        verbose_name = 'Metopio Statewide Data Transformation'
        verbose_name_plural = 'Metopio Statewide Data Transformations'
        ordering = ['period', 'stratification']  # Add this line

class MetopioStateWideRemovalDataTransformation(models.Model):
    layer = models.CharField(max_length=50, default='State')  # Constant value: 'State'
    geoid = models.CharField(max_length=50, default='WI')  # Constant value: 'wisconsin'
    topic = models.CharField(max_length=50, default='FVDEWVAR')  # Constant value: 'FVDEYLCV'
    stratification = models.TextField(blank=True)  # To store stratification notes
    period = models.CharField(max_length=20)  # Transformed SCHOOL_YEAR (e.g., 2023-24 → 2023-2024)
    value = models.PositiveIntegerField()  # Derived from STUDENT_COUNT

    class Meta:
        verbose_name = 'Metopio Statewide Removal Data Transformation'
        verbose_name_plural = 'Metopio Statewide Removal Data Transformations'
        ordering = ['period', 'stratification']  # Add this line

class MetopioTriCountyLayerTransformation(models.Model):
    layer = models.CharField(max_length=50, default='Region')  # Constant value: 'Region'
    geoid = models.CharField(max_length=50, default='fox-valley')  # Constant value: 'fox-valley'
    topic = models.CharField(max_length=50, default='FVDEYLCV')  # Constant value: 'FVDEYLCV'
    stratification = models.TextField(blank=True)  # To store stratification notes
    period = models.CharField(max_length=20)  # Transformed SCHOOL_YEAR (e.g., 2023-24 → 2023-2024)
    value = models.PositiveIntegerField()  # Derived from STUDENT_COUNT

    class Meta:
        verbose_name = 'Metopio Data Transformation'
        verbose_name_plural = 'Metopio Data Transformations'
        ordering = ['period', 'stratification']  # Add this line

class MetopioTriCountyRemovalDataTransformation(models.Model):
    layer = models.CharField(max_length=50, default='Region')  # Constant value: 'Region'
    geoid = models.CharField(max_length=50, default='fox-valley')  # Constant value: 'fox-valley'
    topic = models.CharField(max_length=50, default='FVDEWVAR')  # Constant value: 'FVDEWVAR'
    stratification = models.TextField(blank=True)  # To store stratification notes
    period = models.CharField(max_length=20)  # Transformed SCHOOL_YEAR (e.g., 2023-24 → 2023-2024)
    value = models.PositiveIntegerField()  # Derived from REMOVAL COUNT

    class Meta:
        verbose_name = 'Metopio Tri-County Removal Data Transformation'
        verbose_name_plural = 'Metopio Tri-County Removal Data Transformations'
        ordering = ['period', 'stratification']

class CountyLayerTransformation(models.Model):
    layer = models.CharField(max_length=50, default='County')
    geoid = models.CharField(max_length=50)  # Change this to CharField
    topic = models.CharField(max_length=50, default='FVDEYLCV')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'County Layer Transformation'
        verbose_name_plural = 'County Layer Transformations'
        ordering = ['period', 'stratification']

class CountyLayerRemovalData(models.Model):
    layer = models.CharField(max_length=50, default='County')
    geoid = models.CharField(max_length=50)  # Change this to CharField
    topic = models.CharField(max_length=50, default='FVDEWVAR')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'County Layer Removal Data'
        verbose_name_plural = 'County Layer Removal Data'
        ordering = ['period', 'stratification']        

class ZipCodeLayerTransformation(models.Model):
    layer = models.CharField(max_length=50, default='County')
    geoid = models.CharField(max_length=50)  # Change this to CharField
    topic = models.CharField(max_length=50, default='FVDEYLCV')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'County Layer Transformation'
        verbose_name_plural = 'County Layer Transformations'
        ordering = ['period','geoid', 'stratification']

class ZipCodeLayerRemovalData(models.Model):
    layer = models.CharField(max_length=50, default='County')
    geoid = models.CharField(max_length=50)  # Change this to CharField
    topic = models.CharField(max_length=50, default='FVDEWVAR')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'County Layer Removal Data'
        verbose_name_plural = 'County Layer Removal Data'
        ordering = ['period','geoid', 'stratification']

class MetopioCityLayerTransformation(models.Model):
    layer = models.CharField(max_length=50, default='City')
    geoid = models.CharField(max_length=50)  # Change this to CharField
    topic = models.CharField(max_length=50, default='FVDEYLCV')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'City Layer Transformation'
        verbose_name_plural = 'City Layer Transformations'
        ordering = ['period']

class MetopioCityRemovalData(models.Model):
    layer = models.CharField(max_length=50, default='City')
    geoid = models.CharField(max_length=50)  # Change this to CharField
    topic = models.CharField(max_length=50, default='FVDEWVAR')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'City Layer Removal Data'
        verbose_name_plural = 'City Layer Removal Data'
        ordering = ['period']

class CombinedRemovalData(models.Model):
    layer = models.CharField(max_length=50, default='Combined')
    geoid = models.CharField(max_length=50)  # Change this to CharField
    topic = models.CharField(max_length=50, default='FVDEWVAR')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Combined Removal Data'
        verbose_name_plural = 'Combined Removal Data'
        ordering = ['period']
class SchoolRemovalData(models.Model):
    school_year = models.CharField(max_length=7)
    agency_type = models.CharField(max_length=50)
    cesa = models.CharField(max_length=10)
    county = models.CharField(max_length=50)
    district_code = models.CharField(max_length=10)
    school_code = models.CharField(max_length=10)
    grade_group = models.CharField(max_length=50)
    charter_ind = models.CharField(max_length=4)
    district_name = models.CharField(max_length=100)
    school_name = models.CharField(max_length=100)
    group_by = models.CharField(max_length=50)
    group_by_value = models.CharField(max_length=200)
    removal_type_description = models.CharField(max_length=200)
    tfs_enrollment_count = models.CharField(max_length=20)
    removal_count = models.CharField(max_length=20)
    place = models.CharField(max_length=100, null=True, blank=True)
    stratification = models.ForeignKey(Stratification, on_delete=models.SET_NULL, null=True, blank=True)
    geoid = models.ForeignKey(CountyGEOID, on_delete=models.SET_NULL, null=True, blank=True)
    
    
    
    def __str__(self):
        return f"{self.county} - {self.student_count}"
    
    def save(self, *args, **kwargs):
        self.school_code = self.school_code.lstrip("0")
        self.district_code = self.district_code.lstrip("0")
        super(SchoolRemovalData, self).save(*args, **kwargs)


# Forward Exam Report Data Model (for ELA and MTH test results)
class ForwardExamData(models.Model):
    # Base school/district information (same as enrollment/removal)
    school_year = models.CharField(max_length=7, verbose_name="School Year")
    agency_type = models.CharField(max_length=50, blank=True, verbose_name="Agency Type")
    cesa = models.CharField(max_length=10, blank=True, verbose_name="CESA")
    county = models.CharField(max_length=50, blank=True, verbose_name="County")
    district_code = models.CharField(max_length=10, verbose_name="District Code")
    school_code = models.CharField(max_length=10, blank=True, verbose_name="School Code")
    grade_group = models.CharField(max_length=50, blank=True, verbose_name="Grade Group")
    charter_ind = models.CharField(max_length=4, blank=True, verbose_name="Charter Indicator")
    district_name = models.CharField(max_length=100, verbose_name="District Name")
    school_name = models.CharField(max_length=100, verbose_name="School Name")
    
    # Test-specific fields (unique to Forward Exam)
    test_subject = models.CharField(max_length=50, verbose_name="Test Subject")  # ELA, Math, Science, Social Studies
    grade_level = models.CharField(max_length=50, verbose_name="Grade Level")  # 3, 4, 5, 6, 7, 8, etc.
    test_result = models.CharField(max_length=50, verbose_name="Test Result")  # Below Basic, Basic, Proficient, Advanced
    test_result_code = models.CharField(max_length=50, verbose_name="Test Result Code")  # 1, 2, 3, 4
    test_group = models.CharField(max_length=100, verbose_name="Test Group")  # WKCE/WAA-SwD, DLM, etc.
    
    # Demographic grouping (same as enrollment/removal)
    group_by = models.CharField(max_length=50, verbose_name="Group By")  # Gender, Ethnicity, Disability, etc.
    group_by_value = models.CharField(max_length=200, verbose_name="Group By Value")  # Male, Female, Hispanic, etc.
    
    # Count and percentage fields
    student_count = models.CharField(max_length=20, verbose_name="Student Count")  # Number of students in this performance level
    percent_of_group = models.CharField(max_length=20, verbose_name="Percent of Group")  # Percentage of subgroup
    group_count = models.CharField(max_length=20, verbose_name="Group Count")  # Total count in the data group
    
    # Test performance metric
    forward_average_scale_score = models.CharField(max_length=10, blank=True, null=True, verbose_name="Forward Average Scale Score")
    
    # Additional fields for linking (same as enrollment/removal)
    place = models.CharField(max_length=100, null=True, blank=True, verbose_name="Place")
    stratification = models.ForeignKey(Stratification, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Stratification")
    geoid = models.ForeignKey(CountyGEOID, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="GEOID")
    
    class Meta:
        verbose_name = 'Forward Exam Data'
        verbose_name_plural = 'Forward Exam Data'
        ordering = ['school_year', 'test_subject', 'grade_level', 'test_result']
        indexes = [
            models.Index(fields=['school_year', 'test_subject']),
            models.Index(fields=['district_code', 'school_code']),
            models.Index(fields=['group_by', 'group_by_value']),
        ]
    
    def __str__(self):
        return f"{self.school_year} - {self.test_subject} - Grade {self.grade_level} - {self.school_name}"
    
    def save(self, *args, **kwargs):
        # Strip leading zeros from codes (same pattern as other models)
        if self.school_code:
            self.school_code = self.school_code.lstrip("0")
        if self.district_code:
            self.district_code = self.district_code.lstrip("0")
        super(ForwardExamData, self).save(*args, **kwargs)


# Forward Exam Transformation Models (PP-10a)
class ForwardExamStateWideTransformation(models.Model):
    layer = models.CharField(max_length=50, default='State')
    geoid = models.CharField(max_length=50, default='WI')
    topic = models.CharField(max_length=50, default='FVDEHAAP')  # Topic code from PP-10a spec
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)  # Format: 2023-2024
    value = models.IntegerField()  # Student count (raw aggregated counts)

    class Meta:
        verbose_name = 'Forward Exam Statewide Transformation'
        verbose_name_plural = 'Forward Exam Statewide Transformations'
        ordering = ['period', 'stratification']


class ForwardExamTriCountyTransformation(models.Model):
    layer = models.CharField(max_length=50, default='Region')
    geoid = models.CharField(max_length=50, default='fox-valley')
    topic = models.CharField(max_length=50, default='FVDEHAAP')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.IntegerField()

    class Meta:
        verbose_name = 'Forward Exam Tri-County Transformation'
        verbose_name_plural = 'Forward Exam Tri-County Transformations'
        ordering = ['period', 'stratification']


class ForwardExamCountyLayerTransformation(models.Model):
    layer = models.CharField(max_length=50, default='County')
    geoid = models.CharField(max_length=50)
    topic = models.CharField(max_length=50, default='FVDEHAAP')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.IntegerField()

    class Meta:
        verbose_name = 'Forward Exam County Layer Transformation'
        verbose_name_plural = 'Forward Exam County Layer Transformations'
        ordering = ['period', 'geoid', 'stratification']


class ForwardExamZipCodeLayerTransformation(models.Model):
    layer = models.CharField(max_length=50, default='Zip Code')
    geoid = models.CharField(max_length=50)
    topic = models.CharField(max_length=50, default='FVDEHAAP')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.IntegerField()

    class Meta:
        verbose_name = 'Forward Exam Zip Code Layer Transformation'
        verbose_name_plural = 'Forward Exam Zip Code Layer Transformations'
        ordering = ['period', 'geoid', 'stratification']


class ForwardExamCityLayerTransformation(models.Model):
    layer = models.CharField(max_length=50, default='City or town')
    geoid = models.CharField(max_length=50)
    topic = models.CharField(max_length=50, default='FVDEHAAP')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.IntegerField()

    class Meta:
        verbose_name = 'Forward Exam City Layer Transformation'
        verbose_name_plural = 'Forward Exam City Layer Transformations'
        ordering = ['period', 'geoid', 'stratification']


class ForwardExamCombinedTransformation(models.Model):
    layer = models.CharField(max_length=50)
    geoid = models.CharField(max_length=50)
    topic = models.CharField(max_length=50, default='FVDEHAAP')
    stratification = models.TextField(blank=True)
    period = models.CharField(max_length=20)
    value = models.IntegerField()

    class Meta:
        verbose_name = 'Forward Exam Combined Transformation'
        verbose_name_plural = 'Forward Exam Combined Transformations'
        ordering = ['period', 'layer', 'geoid', 'stratification']