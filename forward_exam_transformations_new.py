# New Forward Exam transformation methods to be added to transformers.py

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

            # Filter for tri-county area using geoid lookup
            forward_exam_data = ForwardExamData.objects.filter(
                **base_filters,
                geoid__county__in=['Outagamie', 'Winnebago', 'Calumet']
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
