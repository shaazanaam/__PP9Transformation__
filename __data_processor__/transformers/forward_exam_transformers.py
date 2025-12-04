"""
Forward Exam data transformations (PP-10a: 3rd Grade Reading Proficiency).

This module handles all Forward Exam transformations:
- ForwardExam-Statewide
- ForwardExam-TriCounty
- ForwardExam-County
- ForwardExam-Zipcode
- ForwardExam-City
- ForwardExam-Combined
"""

from ..models import (
    ForwardExamData,
    ForwardExamStateWideTransformation,
    ForwardExamTriCountyTransformation,
    ForwardExamCountyLayerTransformation,
    ForwardExamZipCodeLayerTransformation,
    ForwardExamCityLayerTransformation,
    ForwardExamCombinedTransformation,
    CountyGEOID,
    SchoolAddressFile,
    Stratification,
)

from django.db import transaction
from django.db.models import Q
from django.contrib import messages
import logging
import traceback
from collections import defaultdict

logger = logging.getLogger(__name__)


class ForwardExamTransformers:
    """
    Handles all Forward Exam (3rd Grade Reading) transformations.
    """
    
    def __init__(self, request):
        self.request = request

    def transform_ForwardExam_Statewide(self):
        """
        Transform Forward Exam data for PP-10a: 3rd Grade Reading Proficiency
        
        Filters:
        - Statewide, Grade 3, Forward test group, Reading subject
        - Proficient students only (Meeting or Advanced)
        - Excludes Migrant Status and duplicate records
        
        Output:
        - Percentage of proficient students by stratification
        - All Students group = 100% (baseline)
        """
        if not ForwardExamData.objects.exists():
            logger.warning("No Forward Exam records found.")
            messages.error(self.request, "No Forward Exam records found. Please upload Forward Exam files first.")
            return False
        
        try:
            logger.info("Starting Forward Exam Statewide transformation...")
            ForwardExamStateWideTransformation.objects.all().delete()
            
            # Base filter criteria
            base_filters = {
                'district_name': '[Statewide]',
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result__in': ['Meeting', 'Advanced']
            }
            
            # Calculate All Students proficient count (denominator for percentages)
            all_students_proficient = ForwardExamData.objects.filter(
                **base_filters,
                group_by='All Students'
            ).exclude(stratification__isnull=True)
            
            # Transform period format: 2024-25 → 2024-2025
            def format_period(school_year):
                if '-' in school_year:
                    start_year, end_year = school_year.split('-')
                    return f"{start_year}-20{end_year}"
                return school_year
            
            # Sum proficient counts by period
            all_students_total = {}
            for record in all_students_proficient:
                period = format_period(record.school_year)
                count = int(record.student_count) if record.student_count.isdigit() else 0
                all_students_total[period] = all_students_total.get(period, 0) + count
            
            logger.info(f"All Students proficient baseline: {all_students_total}")
            
            # Fetch proficient Reading students (exclude duplicates and Migrant Status)
            forward_exam_data = ForwardExamData.objects.filter(
                **base_filters
            ).exclude(group_by='Migrant Status').exclude(stratification__isnull=True)
            
            logger.info(f"Proficient records to process: {forward_exam_data.count()}")
            
            # Calculate group totals to identify missing data
            group_totals = defaultdict(int)
            all_students_by_period = {}
            
            for record in forward_exam_data:
                period = format_period(record.school_year)
                count = int(record.student_count) if record.student_count.isdigit() else 0
                group_totals[(record.group_by, period)] += count
                
                if record.group_by == "All Students":
                    all_students_by_period[period] = all_students_by_period.get(period, 0) + count
            
            # Create Unknown records for groups with missing data
            new_unknown_records = []
            for (group_by, period), total in group_totals.items():
                if period in all_students_by_period and total < all_students_by_period[period]:
                    difference = all_students_by_period[period] - total
                    
                    # Find sample record to clone structure
                    sample = forward_exam_data.filter(
                        group_by=group_by,
                        school_year__contains=period.split('-')[0]
                    ).first()
                    
                    if sample:
                        new_unknown_records.append(ForwardExamData(
                            school_year=sample.school_year,
                            district_name=sample.district_name,
                            grade_level=sample.grade_level,
                            test_group=sample.test_group,
                            test_subject=sample.test_subject,
                            test_result=sample.test_result,
                            group_by=group_by,
                            group_by_value="Unknown",
                            student_count=str(difference),
                            stratification=sample.stratification
                        ))
            
            logger.info(f"Created {len(new_unknown_records)} Unknown records for data completeness")
            
            # Combine original data with unknown records
            combined_data = list(forward_exam_data) + new_unknown_records
            
            # Group by stratification and aggregate proficient counts
            grouped_data = {}
            for record in combined_data:
                period = format_period(record.school_year)
                stratification = record.stratification.label_name if record.stratification else "Error"
                key = (stratification, period)
                count = int(record.student_count) if record.student_count.isdigit() else 0
                
                if key not in grouped_data:
                    grouped_data[key] = {
                        "layer": "State",
                        "geoid": "WI",
                        "topic": "FVDEHAAP",
                        "stratification": stratification,
                        "period": period,
                        "value": count
                    }
                else:
                    grouped_data[key]["value"] += count
            
            # Convert counts to percentages (rounded to nearest integer)
            # Formula: (stratification proficient count / All Students proficient count) * 100
            for data in grouped_data.values():
                period = data["period"]
                if period in all_students_total and all_students_total[period] > 0:
                    percentage = (data["value"] / all_students_total[period]) * 100
                    data["value"] = round(percentage)
                else:
                    data["value"] = 0
            
            # Create transformation records
            transformed_data = [
                ForwardExamStateWideTransformation(**data)
                for data in grouped_data.values()
            ]
            
            # Save to database
            with transaction.atomic():
                ForwardExamStateWideTransformation.objects.bulk_create(transformed_data)
            
            logger.info(f"Transformed {len(transformed_data)} Forward Exam Statewide records.")
            messages.success(self.request, f"Forward Exam transformation completed: {len(transformed_data)} records.")
            return True
            
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Forward Exam Statewide Transformation: {e} at line {line_number}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            messages.error(self.request, f"Forward Exam Statewide transformation failed: {e}")
            return False

    def transform_ForwardExam_TriCounty(self):
        """Apply Forward Exam Tri-County Layer Transformation for 3rd Grade Reading proficiency"""
        try:
            logger.info("Starting Forward Exam Tri-County Layer Transformation...")

            def format_period(school_year):
                """Convert school year format (e.g., '2024-25' to '2024-2025')"""
                if '-' in school_year:
                    start_year, end_year = school_year.split('-')
                    return f"{start_year}-20{end_year}"
                return school_year

            # Base filters for Forward Exam data (3rd Grade Reading proficiency)
            base_filters = {
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result__in': ['Meeting', 'Advanced']
            }

            # Filter for tri-county area (matching enrollment/removal pattern)
            forward_exam_data = ForwardExamData.objects.filter(
                **base_filters,
                county__in=['Outagamie', 'Winnebago', 'Calumet']
            ).exclude(
                group_by='Migrant Status'
            ).exclude(
                stratification__isnull=True
            )

            logger.info(f"Filtered Forward Exam data count: {forward_exam_data.count()}")

            # Calculate All Students proficient baseline for tri-county
            all_students_proficient = forward_exam_data.filter(
                group_by='All Students',
                group_by_value='All Students'
            )

            all_students_total = {}
            for record in all_students_proficient:
                period = format_period(record.school_year)
                count = int(record.student_count) if record.student_count.isdigit() else 0
                all_students_total[period] = all_students_total.get(period, 0) + count

            logger.info(f"All Students proficient baseline: {all_students_total}")

            # Handle unknown values (4-step pattern from removal transformations)
            combined_dataset = list(forward_exam_data)
            group_totals = defaultdict(int)

            # Compute totals per GROUP_BY
            for record in combined_dataset:
                period = format_period(record.school_year)
                group_totals[(period, record.group_by)] += int(record.student_count) if record.student_count.isdigit() else 0

            # Calculate missing (unknown) values
            new_unknown_records = []
            unique_records = set()

            for period, group_by in group_totals.keys():
                if group_by == "All Students":
                    continue
                if group_totals[(period, group_by)] < all_students_total.get(period, 0):
                    difference = all_students_total[period] - group_totals[(period, group_by)]
                    unique_key = (period, group_by, "Unknown")

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        # Find a reference record for this group_by
                        reference_record = next((r for r in combined_dataset if r.group_by == group_by), None)
                        if reference_record:
                            new_unknown_records.append(
                                ForwardExamData(
                                    school_year=reference_record.school_year,
                                    district_name=reference_record.district_name or "Unknown",
                                    group_by=group_by,
                                    group_by_value="Unknown",
                                    grade_level=reference_record.grade_level,
                                    test_group=reference_record.test_group,
                                    test_subject=reference_record.test_subject,
                                    test_result=reference_record.test_result,
                                    student_count=str(difference),
                                    stratification=reference_record.stratification,
                                    geoid=reference_record.geoid
                                )
                            )
                            logger.info(f"Added unknown record for {unique_key}")

            # Realign stratifications for unknown records
            if new_unknown_records:
                strat_map = {
                    f"{strat.group_by}{strat.group_by_value}": strat
                    for strat in Stratification.objects.all()
                }
                for record in new_unknown_records:
                    combined_key = record.group_by + record.group_by_value
                    stratification = strat_map.get(combined_key)
                    if stratification:
                        record.stratification = stratification
                    else:
                        logger.warning(f"No stratification found for {combined_key}")
                combined_dataset.extend(new_unknown_records)

            logger.info(f"Combined dataset count (with unknowns): {len(combined_dataset)}")

            # Group data by stratification and period
            grouped_data = {}
            for record in combined_dataset:
                period = format_period(record.school_year)
                strat_label = record.stratification.label_name if record.stratification else "Unknown"
                count = int(record.student_count) if record.student_count.isdigit() else 0

                strat_key = (strat_label, period)

                if strat_key not in grouped_data:
                    grouped_data[strat_key] = {
                        "layer": "Region",
                        "geoid": "fox-valley",
                        "topic": "FVDEHAAP",
                        "period": period,
                        "value": count,
                        "stratification": strat_label
                    }
                else:
                    grouped_data[strat_key]["value"] += count

            # Convert counts to percentages based on All Students proficient baseline
            for (strat_label, period), data in grouped_data.items():
                if period in all_students_total and all_students_total[period] > 0:
                    percentage = (data["value"] / all_students_total[period]) * 100
                    data["value"] = round(percentage)
                else:
                    data["value"] = 0

            # Bulk insert transformed data
            transformed_data = [
                ForwardExamTriCountyTransformation(**data)
                for data in grouped_data.values()
                if data["value"] != 0
            ]

            if transformed_data:
                with transaction.atomic():
                    ForwardExamTriCountyTransformation.objects.all().delete()
                    ForwardExamTriCountyTransformation.objects.bulk_create(transformed_data)
                logger.info(f"Successfully transformed {len(transformed_data)} tri-county records.")
            else:
                logger.info("No transformed data to insert.")

            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Forward Exam Tri-County Transformation: {e} at line number {line_number}")
            return False

    def transform_ForwardExam_CountyLayer(self):
        """Apply Forward Exam County Layer Transformation for 3rd Grade Reading proficiency"""
        try:
            logger.info("Starting Forward Exam County Layer Transformation...")

            def format_period(school_year):
                """Convert school year format (e.g., '2024-25' to '2024-2025')"""
                if '-' in school_year:
                    start_year, end_year = school_year.split('-')
                    return f"{start_year}-20{end_year}"
                return school_year

            # Fetch County GEOID entries
            county_geoid_entries = CountyGEOID.objects.filter(layer='County')
            county_geoid_map = {entry.name.split(" County, WI")[0].strip(): entry for entry in county_geoid_entries}
            logger.info(f"County GEOID entries count: {len(county_geoid_map)}")

            # Base filters for Forward Exam data (3rd Grade Reading proficiency)
            base_filters = {
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result__in': ['Meeting', 'Advanced']
            }

            # Filter for tri-county area (matching enrollment/removal pattern)
            forward_exam_data = ForwardExamData.objects.filter(
                **base_filters,
                county__in=['Outagamie', 'Winnebago', 'Calumet']
            ).exclude(
                group_by='Migrant Status'
            ).exclude(
                stratification__isnull=True
            )

            logger.info(f"Filtered Forward Exam data count: {forward_exam_data.count()}")

            # Handle unknown values per county
            combined_dataset = list(forward_exam_data)
            group_totals = defaultdict(int)
            all_students_totals = defaultdict(int)

            # Compute totals per GROUP_BY per county
            for record in combined_dataset:
                period = format_period(record.school_year)
                county = record.county if record.county else "Unknown"
                key = (period, county, record.group_by)
                group_totals[key] += int(record.student_count) if record.student_count.isdigit() else 0
                if record.group_by == "All Students":
                    all_students_totals[(period, county)] += int(record.student_count) if record.student_count.isdigit() else 0

            logger.info(f"All Students totals per county: {dict(all_students_totals)}")

            # Calculate missing (unknown) values per county
            new_unknown_records = []
            unique_records = set()

            for (period, county, group_by), total in group_totals.items():
                if group_by == "All Students":
                    continue
                if total < all_students_totals.get((period, county), 0):
                    difference = all_students_totals[(period, county)] - total
                    unique_key = (period, county, group_by, "Unknown")

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        # Find a reference record for this county and group_by
                        reference_record = next((r for r in combined_dataset if r.county == county and r.group_by == group_by), None)
                        if reference_record:
                            new_unknown_records.append(
                                ForwardExamData(
                                    school_year=reference_record.school_year,
                                    district_name=reference_record.district_name or "Unknown",
                                    group_by=group_by,
                                    group_by_value="Unknown",
                                    grade_level=reference_record.grade_level,
                                    test_group=reference_record.test_group,
                                    test_subject=reference_record.test_subject,
                                    test_result=reference_record.test_result,
                                    student_count=str(difference),
                                    stratification=reference_record.stratification,
                                    geoid=reference_record.geoid
                                )
                            )
                            logger.info(f"Added unknown record for {unique_key}")

            # Realign stratifications for unknown records
            if new_unknown_records:
                strat_map = {
                    f"{strat.group_by}{strat.group_by_value}": strat
                    for strat in Stratification.objects.all()
                }
                for record in new_unknown_records:
                    combined_key = record.group_by + record.group_by_value
                    stratification = strat_map.get(combined_key)
                    if stratification:
                        record.stratification = stratification
                    else:
                        logger.warning(f"No stratification found for {combined_key}")
                combined_dataset.extend(new_unknown_records)

            logger.info(f"Combined dataset count (with unknowns): {len(combined_dataset)}")

            # Group data by county, stratification, and period
            grouped_data = {}
            for record in combined_dataset:
                period = format_period(record.school_year)
                strat_label = record.stratification.label_name if record.stratification else "Unknown"
                county = record.county if record.county else "Unknown"
                geoid = county_geoid_map.get(county).geoid if county_geoid_map.get(county) else "Error"
                count = int(record.student_count) if record.student_count.isdigit() else 0

                strat_key = (county, strat_label, period)

                if strat_key not in grouped_data:
                    grouped_data[strat_key] = {
                        "layer": "County",
                        "geoid": geoid,
                        "topic": "FVDEHAAP",
                        "period": period,
                        "value": count,
                        "stratification": strat_label
                    }
                else:
                    grouped_data[strat_key]["value"] += count

            # Convert counts to percentages based on All Students proficient baseline per county
            for (county, strat_label, period), data in grouped_data.items():
                county_all_students = all_students_totals.get((period, county), 0)
                if county_all_students > 0:
                    percentage = (data["value"] / county_all_students) * 100
                    data["value"] = round(percentage)
                else:
                    data["value"] = 0

            # Bulk insert transformed data
            transformed_data = [
                ForwardExamCountyLayerTransformation(**data)
                for data in grouped_data.values()
                if data["value"] != 0 and data["geoid"] != "Error"
            ]

            if transformed_data:
                with transaction.atomic():
                    ForwardExamCountyLayerTransformation.objects.all().delete()
                    ForwardExamCountyLayerTransformation.objects.bulk_create(transformed_data)
                logger.info(f"Successfully transformed {len(transformed_data)} county records.")
            else:
                logger.info("No transformed data to insert.")

            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Forward Exam County Layer Transformation: {e} at line number {line_number}")
            return False

    def transform_ForwardExam_ZipcodeLayer(self):
        """Apply Forward Exam Zip Code Layer Transformation for 3rd Grade Reading proficiency"""
        try:
            logger.info("Starting Forward Exam Zip Code Layer Transformation...")

            def format_period(school_year):
                """Convert school year format (e.g., '2024-25' to '2024-2025')"""
                if '-' in school_year:
                    start_year, end_year = school_year.split('-')
                    return f"{start_year}-20{end_year}"
                return school_year

            # Fetch Zip Code GEOID entries
            zip_code_geoid_entries = CountyGEOID.objects.filter(layer="Zip code")
            zip_code_geoid_map = {entry.name: entry.geoid for entry in zip_code_geoid_entries}
            logger.info(f"Zip Code GEOID entries count: {len(zip_code_geoid_map)}")

            # Base filters for Forward Exam data (3rd Grade Reading proficiency)
            base_filters = {
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result__in': ['Meeting', 'Advanced']
            }

            # Filter for tri-county area (matching enrollment/removal pattern)
            forward_exam_data = ForwardExamData.objects.filter(
                **base_filters,
                county__in=['Outagamie', 'Winnebago', 'Calumet']
            ).exclude(
                group_by='Migrant Status'
            ).exclude(
                stratification__isnull=True
            ).exclude(
                district_name='[Statewide]'
            )

            logger.info(f"Filtered Forward Exam data count: {forward_exam_data.count()}")

            # Normalize district and school codes
            combined_dataset = list(forward_exam_data)
            for record in combined_dataset:
                if record.district_code:
                    record.district_code = str(record.district_code).strip().lstrip("0")
                if record.school_code:
                    record.school_code = str(record.school_code).strip().lstrip("0")

            # Create zip code map from SchoolAddressFile
            zip_code_map = {
                (d.lea_code.lstrip("0"), d.school_code.lstrip("0")): d.zip_code
                for d in SchoolAddressFile.objects.all()
            }

            # Assign zip codes to records
            for record in combined_dataset:
                combined_key = (record.district_code, record.school_code)
                zip_code = zip_code_map.get(combined_key, "Not Found")
                setattr(record, "zip_code", zip_code)

            # Handle unknown values per school
            group_totals = defaultdict(int)
            all_students_totals = defaultdict(int)

            # Compute totals per GROUP_BY per school
            for record in combined_dataset:
                if not record.school_code:
                    continue
                period = format_period(record.school_year)
                key = (period, record.district_code, record.school_code, record.group_by)
                group_totals[key] += int(record.student_count) if record.student_count.isdigit() else 0
                if record.group_by == "All Students":
                    all_students_totals[(period, record.district_code, record.school_code)] += int(record.student_count) if record.student_count.isdigit() else 0

            # Calculate missing (unknown) values per school
            new_unknown_records = []
            unique_records = set()

            for (period, district_code, school_code, group_by), total in group_totals.items():
                if group_by == "All Students":
                    continue
                school_total = all_students_totals.get((period, district_code, school_code), 0)
                if total < school_total:
                    difference = school_total - total
                    unique_key = (period, district_code, school_code, group_by, "Unknown")

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        # Find a reference record for this school and group_by
                        reference_record = next((r for r in combined_dataset if r.district_code == district_code and r.school_code == school_code and r.group_by == group_by), None)
                        if reference_record:
                            new_unknown_records.append(
                                ForwardExamData(
                                    school_year=reference_record.school_year,
                                    district_name=reference_record.district_name or "Unknown",
                                    district_code=district_code,
                                    school_code=school_code,
                                    group_by=group_by,
                                    group_by_value="Unknown",
                                    grade_level=reference_record.grade_level,
                                    test_group=reference_record.test_group,
                                    test_subject=reference_record.test_subject,
                                    test_result=reference_record.test_result,
                                    student_count=str(difference),
                                    stratification=reference_record.stratification,
                                    geoid=reference_record.geoid
                                )
                            )
                            setattr(new_unknown_records[-1], "zip_code", getattr(reference_record, "zip_code", "Not Found"))

            # Realign stratifications for unknown records
            if new_unknown_records:
                strat_map = {
                    f"{strat.group_by}{strat.group_by_value}": strat
                    for strat in Stratification.objects.all()
                }
                for record in new_unknown_records:
                    combined_key = record.group_by + record.group_by_value
                    stratification = strat_map.get(combined_key)
                    if stratification:
                        record.stratification = stratification
                    else:
                        logger.warning(f"No stratification found for {combined_key}")
                combined_dataset.extend(new_unknown_records)

            logger.info(f"Combined dataset count (with unknowns): {len(combined_dataset)}")

            # Group data by zip code, stratification, and period
            grouped_data = {}
            for record in combined_dataset:
                period = format_period(record.school_year)
                strat_label = record.stratification.label_name if record.stratification else "Unknown"
                zip_code = getattr(record, "zip_code", "Not Found")
                geoid = zip_code_geoid_map.get(zip_code, None)
                
                if not geoid or geoid == "Error":
                    continue

                count = int(record.student_count) if record.student_count.isdigit() else 0

                strat_key = (zip_code, strat_label, period)

                if strat_key not in grouped_data:
                    grouped_data[strat_key] = {
                        "layer": "Zip code",
                        "geoid": geoid,
                        "topic": "FVDEHAAP",
                        "period": period,
                        "value": count,
                        "stratification": strat_label
                    }
                else:
                    grouped_data[strat_key]["value"] += count

            # Calculate All Students totals per zip code for percentage calculation
            zip_all_students_totals = defaultdict(int)
            for record in combined_dataset:
                if record.group_by == "All Students":
                    period = format_period(record.school_year)
                    zip_code = getattr(record, "zip_code", "Not Found")
                    count = int(record.student_count) if record.student_count.isdigit() else 0
                    zip_all_students_totals[(period, zip_code)] += count

            # Convert counts to percentages based on All Students proficient baseline per zip code
            for (zip_code, strat_label, period), data in grouped_data.items():
                zip_total = zip_all_students_totals.get((period, zip_code), 0)
                if zip_total > 0:
                    percentage = (data["value"] / zip_total) * 100
                    data["value"] = round(percentage)
                else:
                    data["value"] = 0

            # Bulk insert transformed data
            transformed_data = [
                ForwardExamZipCodeLayerTransformation(**data)
                for data in grouped_data.values()
                if data["value"] != 0
            ]

            if transformed_data:
                with transaction.atomic():
                    ForwardExamZipCodeLayerTransformation.objects.all().delete()
                    ForwardExamZipCodeLayerTransformation.objects.bulk_create(transformed_data)
                logger.info(f"Successfully transformed {len(transformed_data)} zip code records.")
            else:
                logger.info("No transformed data to insert.")

            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Forward Exam Zip Code Layer Transformation: {e} at line number {line_number}")
            return False

    def transform_ForwardExam_CityLayer(self):
        """Apply Forward Exam City Layer Transformation for 3rd Grade Reading proficiency"""
        try:
            logger.info("Starting Forward Exam City Layer Transformation...")

            def format_period(school_year):
                """Convert school year format (e.g., '2024-25' to '2024-2025')"""
                if '-' in school_year:
                    start_year, end_year = school_year.split('-')
                    return f"{start_year}-20{end_year}"
                return school_year

            # Fetch City GEOID entries
            city_geoid_entries = CountyGEOID.objects.filter(layer="City or town")
            city_geoid_map = {entry.name: entry.geoid for entry in city_geoid_entries}
            logger.info(f"City GEOID entries count: {len(city_geoid_map)}")

            # Base filters for Forward Exam data (3rd Grade Reading proficiency)
            base_filters = {
                'grade_level': '3',
                'test_group': 'Forward',
                'test_subject': 'Reading',
                'test_result__in': ['Meeting', 'Advanced']
            }

            # Filter for tri-county area (matching enrollment/removal pattern)
            forward_exam_data = ForwardExamData.objects.filter(
                **base_filters,
                county__in=['Outagamie', 'Winnebago', 'Calumet']
            ).exclude(
                group_by='Migrant Status'
            ).exclude(
                stratification__isnull=True
            ).exclude(
                district_name__startswith='['
            )

            logger.info(f"Filtered Forward Exam data count: {forward_exam_data.count()}")

            # Normalize district and school codes
            combined_dataset = list(forward_exam_data)
            for record in combined_dataset:
                if record.district_code:
                    record.district_code = str(record.district_code).strip().lstrip("0")
                if record.school_code:
                    record.school_code = str(record.school_code).strip().lstrip("0")

            # Create city map from SchoolAddressFile
            city_map = {
                (d.lea_code.lstrip("0"), d.school_code.lstrip("0")): d.city
                for d in SchoolAddressFile.objects.all()
            }

            # Assign cities to records
            for record in combined_dataset:
                combined_key = (record.district_code, record.school_code)
                city = city_map.get(combined_key, "Not Found")
                setattr(record, "city", city)

            # Handle unknown values per school
            group_totals = defaultdict(int)
            all_students_totals = defaultdict(int)

            # Compute totals per GROUP_BY per school
            for record in combined_dataset:
                if not record.school_code:
                    continue
                period = format_period(record.school_year)
                key = (period, record.district_code, record.school_code, record.group_by)
                group_totals[key] += int(record.student_count) if record.student_count.isdigit() else 0
                if record.group_by == "All Students":
                    all_students_totals[(period, record.district_code, record.school_code)] += int(record.student_count) if record.student_count.isdigit() else 0

            # Calculate missing (unknown) values per school
            new_unknown_records = []
            unique_records = set()

            for (period, district_code, school_code, group_by), total in group_totals.items():
                if group_by == "All Students":
                    continue
                school_total = all_students_totals.get((period, district_code, school_code), 0)
                if total < school_total:
                    difference = school_total - total
                    unique_key = (period, district_code, school_code, group_by, "Unknown")

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        # Find a reference record for this school and group_by
                        reference_record = next((r for r in combined_dataset if r.district_code == district_code and r.school_code == school_code and r.group_by == group_by), None)
                        if reference_record:
                            new_unknown_records.append(
                                ForwardExamData(
                                    school_year=reference_record.school_year,
                                    district_name=reference_record.district_name or "Unknown",
                                    district_code=district_code,
                                    school_code=school_code,
                                    group_by=group_by,
                                    group_by_value="Unknown",
                                    grade_level=reference_record.grade_level,
                                    test_group=reference_record.test_group,
                                    test_subject=reference_record.test_subject,
                                    test_result=reference_record.test_result,
                                    student_count=str(difference),
                                    stratification=reference_record.stratification,
                                    geoid=reference_record.geoid
                                )
                            )
                            setattr(new_unknown_records[-1], "city", getattr(reference_record, "city", "Not Found"))

            # Realign stratifications for unknown records
            if new_unknown_records:
                strat_map = {
                    f"{strat.group_by}{strat.group_by_value}": strat
                    for strat in Stratification.objects.all()
                }
                for record in new_unknown_records:
                    combined_key = record.group_by + record.group_by_value
                    stratification = strat_map.get(combined_key)
                    if stratification:
                        record.stratification = stratification
                    else:
                        logger.warning(f"No stratification found for {combined_key}")
                combined_dataset.extend(new_unknown_records)

            logger.info(f"Combined dataset count (with unknowns): {len(combined_dataset)}")

            # Group data by city, stratification, and period
            grouped_data = {}
            for record in combined_dataset:
                period = format_period(record.school_year)
                strat_label = record.stratification.label_name if record.stratification else "Unknown"
                city = getattr(record, "city", "Not Found") + ", WI"  # Add ", WI" to match GEOID format
                geoid = city_geoid_map.get(city, None)
                
                if not geoid or geoid == "Error":
                    continue

                count = int(record.student_count) if record.student_count.isdigit() else 0

                strat_key = (city, strat_label, period)

                if strat_key not in grouped_data:
                    grouped_data[strat_key] = {
                        "layer": "City or town",
                        "geoid": geoid,
                        "topic": "FVDEHAAP",
                        "period": period,
                        "value": count,
                        "stratification": strat_label
                    }
                else:
                    grouped_data[strat_key]["value"] += count

            # Calculate All Students totals per city for percentage calculation
            city_all_students_totals = defaultdict(int)
            for record in combined_dataset:
                if record.group_by == "All Students":
                    period = format_period(record.school_year)
                    city = getattr(record, "city", "Not Found") + ", WI"
                    count = int(record.student_count) if record.student_count.isdigit() else 0
                    city_all_students_totals[(period, city)] += count

            # Convert counts to percentages based on All Students proficient baseline per city
            for (city, strat_label, period), data in grouped_data.items():
                city_total = city_all_students_totals.get((period, city), 0)
                if city_total > 0:
                    percentage = (data["value"] / city_total) * 100
                    data["value"] = round(percentage)
                else:
                    data["value"] = 0

            # Bulk insert transformed data
            transformed_data = [
                ForwardExamCityLayerTransformation(**data)
                for data in grouped_data.values()
                if data["value"] != 0
            ]

            if transformed_data:
                with transaction.atomic():
                    ForwardExamCityLayerTransformation.objects.all().delete()
                    ForwardExamCityLayerTransformation.objects.bulk_create(transformed_data)
                logger.info(f"Successfully transformed {len(transformed_data)} city records.")
            else:
                logger.info("No transformed data to insert.")

            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Forward Exam City Layer Transformation: {e} at line number {line_number}")
            return False

    def transform_ForwardExam_Combined(self):
        """Apply Combined Forward Exam Transformation by calling individual transformations and merging results"""
        try:
            logger.info("Starting Combined Forward Exam Transformation...")

            # Clear existing data in ForwardExamCombinedTransformation
            ForwardExamCombinedTransformation.objects.all().delete()

            # Initialize a list to hold all combined data
            combined_data = []

            # Call each individual Forward Exam transformation and collect data
            if not self.transform_ForwardExam_Statewide():
                logger.error("Forward Exam Statewide Transformation failed.")
                return False
            combined_data.extend(
                ForwardExamStateWideTransformation.objects.values(
                    "layer", "geoid", "topic", "stratification", "period", "value"
                )
            )

            if not self.transform_ForwardExam_TriCounty():
                logger.error("Forward Exam Tri-County Transformation failed.")
                return False
            combined_data.extend(
                ForwardExamTriCountyTransformation.objects.values(
                    "layer", "geoid", "topic", "stratification", "period", "value"
                )
            )

            if not self.transform_ForwardExam_CountyLayer():
                logger.error("Forward Exam County Layer Transformation failed.")
                return False
            combined_data.extend(
                ForwardExamCountyLayerTransformation.objects.values(
                    "layer", "geoid", "topic", "stratification", "period", "value"
                )
            )

            if not self.transform_ForwardExam_ZipcodeLayer():
                logger.error("Forward Exam Zip Code Layer Transformation failed.")
                return False
            combined_data.extend(
                ForwardExamZipCodeLayerTransformation.objects.values(
                    "layer", "geoid", "topic", "stratification", "period", "value"
                )
            )

            if not self.transform_ForwardExam_CityLayer():
                logger.error("Forward Exam City Layer Transformation failed.")
                return False
            combined_data.extend(
                ForwardExamCityLayerTransformation.objects.values(
                    "layer", "geoid", "topic", "stratification", "period", "value"
                )
            )

            # Bulk insert the combined data
            combined_instances = [
                ForwardExamCombinedTransformation(
                    layer=row["layer"],
                    geoid=row["geoid"],
                    topic=row["topic"],
                    stratification=row["stratification"],
                    period=row["period"],
                    value=row["value"],
                )
                for row in combined_data
            ]
            ForwardExamCombinedTransformation.objects.bulk_create(combined_instances)

            logger.info(f"Combined Forward Exam Transformation completed successfully with {len(combined_instances)} records.")
                
            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Combined Forward Exam Transformation: {e} at line number {line_number}")
            return False
