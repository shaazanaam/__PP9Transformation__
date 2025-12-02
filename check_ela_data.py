import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_data_project.settings')
django.setup()

from __data_processor__.models import ForwardExamData

# Check ELA data
ela_only = ForwardExamData.objects.filter(
    district_name='[Statewide]',
    grade_level='3',
    test_group='Forward',
    test_result__in=['Meeting', 'Advanced'],
    group_by='All Students',
    test_subject='ELA'
)

print(f'ELA records (Forward, Grade 3, Proficient, All Students): {ela_only.count()}')
if ela_only.exists():
    total = sum([int(r.student_count) for r in ela_only if r.student_count.isdigit()])
    print(f'Total ELA student count: {total}')
    for r in ela_only:
        print(f'  {r.test_result}: {r.student_count}')

# Check what test subjects exist for this criteria
all_subjects = ForwardExamData.objects.filter(
    district_name='[Statewide]',
    grade_level='3',
    test_group='Forward',
    test_result__in=['Meeting', 'Advanced'],
    group_by='All Students'
).values_list('test_subject', flat=True).distinct()

print(f'\nTest subjects with this criteria: {list(all_subjects)}')
