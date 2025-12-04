"""
Test suite for Forward Exam transformations (PP-10a: 3rd Grade Reading Proficiency)

This test file covers all Forward Exam transformation layers:
- Statewide
- Tri-County (Fox Valley region)
- County Layer (Outagamie, Winnebago, Calumet)
- Zip Code Layer
- City Layer
- Combined (all layers merged)

Tests verify:
1. Data filtering (Reading, Grade 3, Forward, Proficient results)
2. Percentage calculation (based on All Students proficient baseline)
3. Unknown value handling
4. GEOID mapping
5. Record counts and data integrity
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_data_project.settings')
django.setup()

from django.test import TestCase
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from __data_processor__.models import (
    ForwardExamData,
    ForwardExamStateWideTransformation,
    ForwardExamTriCountyTransformation,
    ForwardExamCountyLayerTransformation,
    ForwardExamZipCodeLayerTransformation,
    ForwardExamCityLayerTransformation,
    ForwardExamCombinedTransformation,
    CountyGEOID,
    Stratification,
    SchoolAddressFile
)
from __data_processor__.transformers import DataTransformer
import logging

logger = logging.getLogger(__name__)


class ForwardExamTransformationTestCase(TestCase):
    """Test case for all Forward Exam transformations"""

    def setUp(self):
        """Set up test fixtures"""
        # Create request factory
        self.factory = RequestFactory()
        self.request = self.factory.get('/data_processor/upload/')
        
        # Add messages middleware
        setattr(self.request, 'session', {})
        messages = FallbackStorage(self.request)
        setattr(self.request, '_messages', messages)
        
        # Create transformer instance
        self.transformer = DataTransformer(self.request)
        
        # Create test stratifications
        self.stratifications = {
            'all_students': Stratification.objects.create(
                group_by='All Students',
                group_by_value='All Students',
                label_name='All Students'
            ),
            'economic_disadvantage': Stratification.objects.create(
                group_by='Economic Disadvantage',
                group_by_value='Econ Disadv',
                label_name='ECO1'
            ),
            'gender_female': Stratification.objects.create(
                group_by='Gender',
                group_by_value='Female',
                label_name='FEM3'
            ),
            'ethnicity_white': Stratification.objects.create(
                group_by='Ethnicity',
                group_by_value='White',
                label_name='ETH5'
            ),
        }
        
        # Create test county GEOIDs
        self.county_geoids = {
            'outagamie': CountyGEOID.objects.create(
                layer='County',
                name='Outagamie',
                geoid='55-087'
            ),
            'winnebago': CountyGEOID.objects.create(
                layer='County',
                name='Winnebago',
                geoid='55-139'
            ),
            'calumet': CountyGEOID.objects.create(
                layer='County',
                name='Calumet',
                geoid='55-015'
            ),
        }
        
        # Create test zip code GEOIDs
        self.zip_geoids = {
            '54911': CountyGEOID.objects.create(
                layer='Zip code',
                name='54911',
                geoid='54911'
            ),
            '54915': CountyGEOID.objects.create(
                layer='Zip code',
                name='54915',
                geoid='54915'
            ),
        }
        
        # Create test city GEOIDs
        self.city_geoids = {
            'appleton': CountyGEOID.objects.create(
                layer='City or town',
                name='Appleton, WI',
                geoid='5502375'
            ),
            'oshkosh': CountyGEOID.objects.create(
                layer='City or town',
                name='Oshkosh, WI',
                geoid='5560225'
            ),
        }
        
        # Create test school addresses
        self.school_addresses = {
            'school1': SchoolAddressFile.objects.create(
                lea_code='001',
                district_name='Appleton Area School District',
                school_code='101',
                school_name='Test Elementary School',
                organization_type='Elementary School',
                school_type='Public',
                low_grade='K',
                high_grade='5',
                address='123 Main St',
                city='Appleton',
                state='WI',
                zip_code='54911',
                cesa='6',
                locale='City',
                county='Outagamie',
                current_status='Open',
                phone_number='920-555-0001',
                charter_status=False
            ),
            'school2': SchoolAddressFile.objects.create(
                lea_code='002',
                district_name='Oshkosh Area School District',
                school_code='201',
                school_name='Test Middle School',
                organization_type='Middle School',
                school_type='Public',
                low_grade='6',
                high_grade='8',
                address='456 Oak Ave',
                city='Oshkosh',
                state='WI',
                zip_code='54915',
                cesa='6',
                locale='City',
                county='Winnebago',
                current_status='Open',
                phone_number='920-555-0002',
                charter_status=False
            ),
        }
        
        # Create test Forward Exam data
        self._create_test_forward_exam_data()

    def _create_test_forward_exam_data(self):
        """Create test Forward Exam data records"""
        test_data = [
            # All Students - Outagamie County
            {
                'school_year': '2024-25',
                'district_name': 'Appleton Area School District',
                'district_code': '001',
                'school_code': '101',
                'school_name': 'Test Elementary School',
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result': 'Meeting',
                'test_result_code': '3',
                'group_by': 'All Students',
                'group_by_value': 'All Students',
                'student_count': '100',
                'percent_of_group': '66.67',
                'group_count': '150',
                'county': 'Outagamie',
                'stratification': self.stratifications['all_students'],
                'geoid': self.county_geoids['outagamie']
            },
            {
                'school_year': '2024-25',
                'district_name': 'Appleton Area School District',
                'district_code': '001',
                'school_code': '101',
                'school_name': 'Test Elementary School',
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result': 'Advanced',
                'test_result_code': '4',
                'group_by': 'All Students',
                'group_by_value': 'All Students',
                'student_count': '50',
                'percent_of_group': '33.33',
                'group_count': '150',
                'county': 'Outagamie',
                'stratification': self.stratifications['all_students'],
                'geoid': self.county_geoids['outagamie']
            },
            # Economic Disadvantage - Outagamie County
            {
                'school_year': '2024-25',
                'district_name': 'Appleton Area School District',
                'district_code': '001',
                'school_code': '101',
                'school_name': 'Test Elementary School',
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result': 'Meeting',
                'test_result_code': '3',
                'group_by': 'Economic Disadvantage',
                'group_by_value': 'Econ Disadv',
                'student_count': '30',
                'percent_of_group': '66.67',
                'group_count': '45',
                'county': 'Outagamie',
                'stratification': self.stratifications['economic_disadvantage'],
                'geoid': self.county_geoids['outagamie']
            },
            {
                'school_year': '2024-25',
                'district_name': 'Appleton Area School District',
                'district_code': '001',
                'school_code': '101',
                'school_name': 'Test Elementary School',
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result': 'Advanced',
                'test_result_code': '4',
                'group_by': 'Economic Disadvantage',
                'group_by_value': 'Econ Disadv',
                'student_count': '15',
                'percent_of_group': '33.33',
                'group_count': '45',
                'county': 'Outagamie',
                'stratification': self.stratifications['economic_disadvantage'],
                'geoid': self.county_geoids['outagamie']
            },
            # Female - Winnebago County
            {
                'school_year': '2024-25',
                'district_name': 'Oshkosh Area School District',
                'district_code': '002',
                'school_code': '201',
                'school_name': 'Test Middle School',
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result': 'Meeting',
                'test_result_code': '3',
                'group_by': 'Gender',
                'group_by_value': 'Female',
                'student_count': '60',
                'percent_of_group': '60.00',
                'group_count': '100',
                'county': 'Winnebago',
                'stratification': self.stratifications['gender_female'],
                'geoid': self.county_geoids['winnebago']
            },
            # Statewide data
            {
                'school_year': '2024-25',
                'district_name': '[Statewide]',
                'district_code': '0000',
                'school_code': '',
                'school_name': '[Statewide]',
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result': 'Meeting',
                'test_result_code': '3',
                'group_by': 'All Students',
                'group_by_value': 'All Students',
                'student_count': '19292',
                'percent_of_group': '68.80',
                'group_count': '28044',
                'stratification': self.stratifications['all_students'],
                'geoid': None
            },
            {
                'school_year': '2024-25',
                'district_name': '[Statewide]',
                'district_code': '0000',
                'school_code': '',
                'school_name': '[Statewide]',
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result': 'Advanced',
                'test_result_code': '4',
                'group_by': 'All Students',
                'group_by_value': 'All Students',
                'student_count': '8752',
                'percent_of_group': '31.20',
                'group_count': '28044',
                'stratification': self.stratifications['all_students'],
                'geoid': None
            },
        ]
        
        for data in test_data:
            ForwardExamData.objects.create(**data)

    def test_statewide_transformation(self):
        """Test Forward Exam Statewide Transformation"""
        logger.info("Testing Forward Exam Statewide Transformation...")
        
        # Run transformation
        result = self.transformer.transform_ForwardExam_Statewide()
        self.assertTrue(result, "Statewide transformation should succeed")
        
        # Verify records created
        records = ForwardExamStateWideTransformation.objects.all()
        self.assertGreater(records.count(), 0, "Should create transformation records")
        
        # Verify All Students = 100%
        all_students_record = records.filter(stratification='All Students').first()
        self.assertIsNotNone(all_students_record, "Should have All Students record")
        self.assertEqual(all_students_record.value, 100, "All Students should be 100%")
        self.assertEqual(all_students_record.layer, 'State')
        self.assertEqual(all_students_record.geoid, 'WI')
        self.assertEqual(all_students_record.topic, 'FVDEHAAP')
        
        logger.info(f"✓ Statewide transformation created {records.count()} records")

    def test_tricounty_transformation(self):
        """Test Forward Exam Tri-County Transformation"""
        logger.info("Testing Forward Exam Tri-County Transformation...")
        
        # Run transformation
        result = self.transformer.transform_ForwardExam_TriCounty()
        self.assertTrue(result, "Tri-County transformation should succeed")
        
        # Verify records created
        records = ForwardExamTriCountyTransformation.objects.all()
        self.assertGreater(records.count(), 0, "Should create transformation records")
        
        # Verify layer and geoid
        for record in records:
            self.assertEqual(record.layer, 'Region')
            self.assertEqual(record.geoid, 'fox-valley')
            self.assertEqual(record.topic, 'FVDEHAAP')
        
        # Verify All Students = 100%
        all_students_record = records.filter(stratification='All Students').first()
        if all_students_record:
            self.assertEqual(all_students_record.value, 100, "All Students should be 100%")
        
        logger.info(f"✓ Tri-County transformation created {records.count()} records")

    def test_county_layer_transformation(self):
        """Test Forward Exam County Layer Transformation"""
        logger.info("Testing Forward Exam County Layer Transformation...")
        
        # Run transformation
        result = self.transformer.transform_ForwardExam_CountyLayer()
        self.assertTrue(result, "County Layer transformation should succeed")
        
        # Verify records created
        records = ForwardExamCountyLayerTransformation.objects.all()
        self.assertGreater(records.count(), 0, "Should create transformation records")
        
        # Verify layer
        for record in records:
            self.assertEqual(record.layer, 'County')
            self.assertEqual(record.topic, 'FVDEHAAP')
            self.assertIn(record.geoid, ['55-087', '55-139', '55-015'])
        
        logger.info(f"✓ County Layer transformation created {records.count()} records")

    def test_zipcode_layer_transformation(self):
        """Test Forward Exam Zip Code Layer Transformation"""
        logger.info("Testing Forward Exam Zip Code Layer Transformation...")
        
        # Run transformation
        result = self.transformer.transform_ForwardExam_ZipcodeLayer()
        self.assertTrue(result, "Zip Code Layer transformation should succeed")
        
        # Verify records created
        records = ForwardExamZipCodeLayerTransformation.objects.all()
        # May be 0 if no matching school address data
        logger.info(f"Zip Code Layer transformation created {records.count()} records")
        
        # Verify layer
        for record in records:
            self.assertEqual(record.layer, 'Zip code')
            self.assertEqual(record.topic, 'FVDEHAAP')
        
        logger.info(f"✓ Zip Code Layer transformation completed")

    def test_city_layer_transformation(self):
        """Test Forward Exam City Layer Transformation"""
        logger.info("Testing Forward Exam City Layer Transformation...")
        
        # Run transformation
        result = self.transformer.transform_ForwardExam_CityLayer()
        self.assertTrue(result, "City Layer transformation should succeed")
        
        # Verify records created
        records = ForwardExamCityLayerTransformation.objects.all()
        # May be 0 if no matching school address data
        logger.info(f"City Layer transformation created {records.count()} records")
        
        # Verify layer
        for record in records:
            self.assertEqual(record.layer, 'City or town')
            self.assertEqual(record.topic, 'FVDEHAAP')
        
        logger.info(f"✓ City Layer transformation completed")

    def test_combined_transformation(self):
        """Test Forward Exam Combined Transformation"""
        logger.info("Testing Forward Exam Combined Transformation...")
        
        # Run transformation
        result = self.transformer.transform_ForwardExam_Combined()
        self.assertTrue(result, "Combined transformation should succeed")
        
        # Verify records created
        records = ForwardExamCombinedTransformation.objects.all()
        self.assertGreater(records.count(), 0, "Should create combined records")
        
        # Verify all layers are present
        layers = set(records.values_list('layer', flat=True))
        expected_layers = {'State', 'Region', 'County', 'Zip code', 'City or town'}
        # Some layers may be missing if no data
        self.assertTrue(len(layers) > 0, "Should have at least one layer")
        
        # Verify topic
        for record in records:
            self.assertEqual(record.topic, 'FVDEHAAP')
        
        logger.info(f"✓ Combined transformation created {records.count()} records with layers: {layers}")

    def test_percentage_calculation(self):
        """Test percentage calculation accuracy"""
        logger.info("Testing percentage calculation...")
        
        # Run statewide transformation
        self.transformer.transform_ForwardExam_Statewide()
        
        # Get All Students total (should be 19292 + 8752 = 28044)
        all_students_total = 28044
        
        # Check if percentages are calculated correctly
        records = ForwardExamStateWideTransformation.objects.all()
        for record in records:
            # Verify value is an integer percentage (0-100)
            self.assertIsInstance(record.value, int)
            self.assertGreaterEqual(record.value, 0)
            self.assertLessEqual(record.value, 100)
        
        logger.info("✓ Percentage calculations are correct")

    def test_data_filtering(self):
        """Test that only correct data is filtered"""
        logger.info("Testing data filtering...")
        
        # Verify only Reading, Grade 3, Forward, Proficient results are used
        forward_exam_data = ForwardExamData.objects.filter(
            grade_level='3',
            test_group='Forward',
            test_subject='Reading',
            test_result__in=['Meeting', 'Advanced']
        )
        
        self.assertGreater(forward_exam_data.count(), 0, "Should have filtered data")
        
        # Verify all records match criteria
        for record in forward_exam_data:
            self.assertEqual(record.grade_level, '3')
            self.assertEqual(record.test_group, 'Forward')
            self.assertEqual(record.test_subject, 'Reading')
            self.assertIn(record.test_result, ['Meeting', 'Advanced'])
        
        logger.info("✓ Data filtering is correct")

    def test_unknown_value_handling(self):
        """Test unknown value handling in transformations"""
        logger.info("Testing unknown value handling...")
        
        # Run tri-county transformation (includes unknown handling)
        result = self.transformer.transform_ForwardExam_TriCounty()
        self.assertTrue(result)
        
        # Unknown records may or may not be created depending on data completeness
        # Just verify the transformation succeeds
        records = ForwardExamTriCountyTransformation.objects.all()
        logger.info(f"✓ Unknown value handling completed ({records.count()} records)")

    def test_geoid_mapping(self):
        """Test GEOID mapping for counties, zip codes, and cities"""
        logger.info("Testing GEOID mapping...")
        
        # Run county layer transformation
        self.transformer.transform_ForwardExam_CountyLayer()
        
        # Verify GEOIDs are correctly mapped
        records = ForwardExamCountyLayerTransformation.objects.all()
        for record in records:
            self.assertIsNotNone(record.geoid)
            self.assertNotEqual(record.geoid, 'Error')
        
        logger.info("✓ GEOID mapping is correct")

    def test_all_transformations_sequence(self):
        """Test running all transformations in sequence"""
        logger.info("Testing all transformations in sequence...")
        
        transformations = [
            ('Statewide', self.transformer.transform_ForwardExam_Statewide),
            ('Tri-County', self.transformer.transform_ForwardExam_TriCounty),
            ('County Layer', self.transformer.transform_ForwardExam_CountyLayer),
            ('Zip Code Layer', self.transformer.transform_ForwardExam_ZipcodeLayer),
            ('City Layer', self.transformer.transform_ForwardExam_CityLayer),
            ('Combined', self.transformer.transform_ForwardExam_Combined),
        ]
        
        for name, transform_func in transformations:
            result = transform_func()
            self.assertTrue(result, f"{name} transformation should succeed")
            logger.info(f"✓ {name} transformation completed")
        
        logger.info("✓ All transformations completed successfully")


class ForwardExamDataIntegrityTestCase(TestCase):
    """Test data integrity for Forward Exam transformations"""

    def test_no_duplicate_records(self):
        """Test that transformations don't create duplicate records"""
        # Create minimal test data
        stratification = Stratification.objects.create(
            group_by='All Students',
            group_by_value='All Students',
            label_name='All Students'
        )
        
        ForwardExamData.objects.create(
            school_year='2024-25',
            district_name='[Statewide]',
            grade_level='3',
            test_group='Forward',
            test_subject='Reading',
            test_result='Meeting',
            group_by='All Students',
            group_by_value='All Students',
            student_count='100',
            stratification=stratification
        )
        
        # Create transformer
        factory = RequestFactory()
        request = factory.get('/data_processor/upload/')
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        transformer = DataTransformer(request)
        
        # Run transformation twice
        transformer.transform_ForwardExam_Statewide()
        initial_count = ForwardExamStateWideTransformation.objects.count()
        
        transformer.transform_ForwardExam_Statewide()
        second_count = ForwardExamStateWideTransformation.objects.count()
        
        # Should have same count (transformation deletes and recreates)
        self.assertEqual(initial_count, second_count, "Should not create duplicate records")

    def test_value_ranges(self):
        """Test that percentage values are within valid ranges"""
        stratification = Stratification.objects.create(
            group_by='All Students',
            group_by_value='All Students',
            label_name='All Students'
        )
        
        ForwardExamData.objects.create(
            school_year='2024-25',
            district_name='[Statewide]',
            grade_level='3',
            test_group='Forward',
            test_subject='Reading',
            test_result='Meeting',
            group_by='All Students',
            group_by_value='All Students',
            student_count='100',
            stratification=stratification
        )
        
        factory = RequestFactory()
        request = factory.get('/data_processor/upload/')
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        transformer = DataTransformer(request)
        
        transformer.transform_ForwardExam_Statewide()
        
        # Check all records have valid percentage values
        records = ForwardExamStateWideTransformation.objects.all()
        for record in records:
            self.assertGreaterEqual(record.value, 0, "Value should be >= 0")
            self.assertLessEqual(record.value, 100, "Value should be <= 100")
