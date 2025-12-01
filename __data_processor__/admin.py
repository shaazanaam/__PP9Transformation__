from django.contrib import admin
from .models import (
    Stratification,
    CountyGEOID,
    SchoolAddressFile,
    SchoolData,
    SchoolRemovalData,
    ForwardExamData,
    TransformedSchoolData,
    MetopioStateWideLayerTransformation,
    MetopioStateWideRemovalDataTransformation,
    MetopioTriCountyLayerTransformation,
    MetopioTriCountyRemovalDataTransformation,
    CountyLayerTransformation,
    CountyLayerRemovalData,
    ZipCodeLayerTransformation,
    ZipCodeLayerRemovalData,
    MetopioCityLayerTransformation,
    MetopioCityRemovalData,
    CombinedRemovalData,
    ForwardExamStateWideTransformation,
    ForwardExamTriCountyTransformation,
    ForwardExamCountyLayerTransformation,
    ForwardExamZipCodeLayerTransformation,
    ForwardExamCityLayerTransformation,
)

# Register your models here.

@admin.register(Stratification)
class StratificationAdmin(admin.ModelAdmin):
    list_display = ('group_by', 'group_by_value', 'label_name')
    search_fields = ('group_by', 'group_by_value', 'label_name')
    list_filter = ('group_by',)

@admin.register(CountyGEOID)
class CountyGEOIDAdmin(admin.ModelAdmin):
    list_display = ('layer', 'name', 'geoid')
    search_fields = ('name', 'geoid')
    list_filter = ('layer',)

@admin.register(SchoolAddressFile)
class SchoolAddressFileAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'district_name', 'city', 'zip_code', 'county')
    search_fields = ('school_name', 'district_name', 'city', 'zip_code')
    list_filter = ('county', 'cesa', 'current_status')

@admin.register(SchoolData)
class SchoolDataAdmin(admin.ModelAdmin):
    list_display = ('school_year', 'district_name', 'school_name', 'group_by', 'group_by_value', 'student_count')
    search_fields = ('district_name', 'school_name', 'county')
    list_filter = ('school_year', 'group_by', 'county')

@admin.register(SchoolRemovalData)
class SchoolRemovalDataAdmin(admin.ModelAdmin):
    list_display = ('school_year', 'district_name', 'school_name', 'group_by', 'group_by_value', 'removal_count')
    search_fields = ('district_name', 'school_name', 'county')
    list_filter = ('school_year', 'group_by', 'county', 'removal_type_description')

@admin.register(ForwardExamData)
class ForwardExamDataAdmin(admin.ModelAdmin):
    list_display = ('school_year', 'test_subject', 'grade_level', 'district_name', 'school_name', 'test_result', 'student_count')
    search_fields = ('district_name', 'school_name', 'county')
    list_filter = ('school_year', 'test_subject', 'grade_level', 'test_result', 'test_group', 'group_by')
    ordering = ('-school_year', 'test_subject', 'grade_level')

@admin.register(TransformedSchoolData)
class TransformedSchoolDataAdmin(admin.ModelAdmin):
    list_display = ('year', 'place', 'group_by', 'group_by_value', 'student_count')
    search_fields = ('place', 'group_by', 'group_by_value')
    list_filter = ('year', 'group_by')

# Register all other transformation models
admin.site.register(MetopioStateWideLayerTransformation)
admin.site.register(MetopioStateWideRemovalDataTransformation)
admin.site.register(MetopioTriCountyLayerTransformation)
admin.site.register(MetopioTriCountyRemovalDataTransformation)
admin.site.register(CountyLayerTransformation)
admin.site.register(CountyLayerRemovalData)
admin.site.register(ZipCodeLayerTransformation)
admin.site.register(ZipCodeLayerRemovalData)
admin.site.register(MetopioCityLayerTransformation)
admin.site.register(MetopioCityRemovalData)
admin.site.register(CombinedRemovalData)

# Register Forward Exam transformation models
admin.site.register(ForwardExamStateWideTransformation)
admin.site.register(ForwardExamTriCountyTransformation)
admin.site.register(ForwardExamCountyLayerTransformation)
admin.site.register(ForwardExamZipCodeLayerTransformation)
admin.site.register(ForwardExamCityLayerTransformation)
