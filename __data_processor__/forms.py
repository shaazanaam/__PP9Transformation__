from django import forms

class UploadFileForm(forms.Form):
    # Main Data Files (choose one based on what you want to transform)
    enrollment_file = forms.FileField(
        label="Enrollment Data File",
        required=False,
        help_text="Upload enrollment_certified_YYYY-YY.csv for enrollment transformations"
    )
    discipline_file = forms.FileField(
        label="Discipline Actions Data File",
        required=False,
        help_text="Upload discipline_actions_certified_YYYY-YY.csv for removal/discipline transformations"
    )
    forward_exam_file = forms.FileField(
        label="Forward Exam Data File",
        required=False,
        help_text="Upload forward_certified_ELA_RDG_WRT_YYYY-YY.csv for Forward Exam transformations"
    )
    
    # Reference/Lookup Files (upload once, reused for all transformations)
    stratifications_file = forms.FileField(
        label="Stratifications Reference File",
        required=False,
        help_text="PP10 Normalized Stratifications.csv - Upload once if not already loaded"
    )
    county_geoid_file = forms.FileField(
        label="County GEOID Reference File",
        required=False,
        help_text="Fox Valley Data Exchange Places GEIODs.csv - Upload once if not already loaded"
    )
    school_address_file = forms.FileField(
        label="School Address Reference File",
        required=False,
        help_text="sd-export-public-schools-YYYYMMDD.HHMM.csv - Upload once if not already loaded"
    )
    