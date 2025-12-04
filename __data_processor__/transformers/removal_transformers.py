"""
Removal/Discipline data transformations.

This module handles all removal-related transformations:
- Statewide-Removal
- Tricounty-Removal
- County-Removal
- Zipcode-Removal
- City-Removal
- Combined Removal
"""

from ..models import (
    SchoolRemovalData,
    MetopioStateWideRemovalDataTransformation,
    MetopioTriCountyRemovalDataTransformation,
    CountyLayerRemovalData,
    ZipCodeLayerRemovalData,
    MetopioCityRemovalData,
    CombinedRemovalData,
    CountyGEOID,
    SchoolAddressFile,
    Stratification,
)

from django.db import transaction
from django.db.models import Q
from django.contrib import messages
import logging
import traceback
import pandas as pd
from collections import defaultdict

logger = logging.getLogger(__name__)


class RemovalTransformers:
    """
    Handles all removal/discipline data transformations.
    """
    
    def __init__(self, request):
        self.request = request

    def transform_Statewide_Removal(self):
        """Apply Statewide Layer Transformation for the Removal Count"""
        if not SchoolRemovalData.objects.exists():
            logger.warning("No records found for Statewide Layer Removal.")
            messages.error(self.request, "No records found for Statewide Layer Removal.Please upload a file.")
            return False
        try:
            logger.info("Starting Statewide Layer Removal...")
            MetopioStateWideRemovalDataTransformation.objects.all().delete()
            logger.info("Successfully removed OLD Statewide Layer records.")

            #Define filter conditions
            district_name_filter ='[Statewide]'
            removal_type_description_filter = 'Out of School Suspension'

            #fetch filtered school data
            school_removal_data = []
            school_removal_data = SchoolRemovalData.objects.filter(district_name=district_name_filter,
                removal_type_description=removal_type_description_filter)
            logger.info(f"Filtered School Removal Data count: {school_removal_data.count()}")


            #Handle the unknown values
            #Construct a dictionary to store the  group totals
            group_totals = defaultdict(int)
            all_students_totals = 0

            #Compute totals per GROUP_BY and track "All Students" total
            for record in school_removal_data:
                key = record.group_by
                group_totals[key] += int(record.removal_count)
                if record.group_by == "All Students":
                    all_students_totals += int(record.removal_count)

            group_by_totals = {}

            for record in school_removal_data:
                key = (record.group_by, record.group_by_value)
                group_by_totals[key] = group_totals[record.group_by]

            new_unknown_records = []
            unique_records = set()
            for(record.group_by, record.group_by_value), total in group_by_totals.items():
                if record.group_by =="All Students":
                    continue

                if total <all_students_totals:
                    difference = all_students_totals - total
                    unique_key = ("Unknown", difference)

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        new_record = SchoolRemovalData(
                            school_year=record.school_year,
                            agency_type=record.agency_type or "Unknown",
                            cesa=record.cesa,
                            county=record.county,
                            district_code=record.district_code,
                            school_code=record.school_code,
                            grade_group=record.grade_group or "Unknown",
                            charter_ind=record.charter_ind or "Unknown",
                            district_name=record.district_name or "Unknown",
                            school_name=record.school_name or "Unknown",
                            group_by=record.group_by,
                            group_by_value="Unknown",
                            removal_type_description = record.removal_type_description,
                            tfs_enrollment_count = record.tfs_enrollment_count,
                            stratification=record.stratification,
                            removal_count=str(difference),
                        )
                        new_unknown_records.append(new_record)
            #Create a comnined data set in the memory
            combined_dataset = list(school_removal_data)   #Convert QuerySet to list

            #Add the new unknown records to the combined data set
            if new_unknown_records:
                strat_map ={
                    f"{strat.group_by}{strat.group_by_value}": strat
                    for strat in Stratification.objects.all()
                }

                for record in new_unknown_records:
                    combined_key = record.group_by + record.group_by_value
                    stratification = strat_map.get(combined_key)
                    if stratification:
                        record.stratification = stratification
                    else:
                        logger.error(f"Stratification not found for {combined_key}")
                    combined_dataset.append(record)


            # log_data_statewide = []
            # for record in combined_dataset:
                
            #     log_data_statewide.append({
            #         "school_name": record.school_name,
            #         "county": record.county,
            #         "group_by": record.group_by,
            #         "group_by_value": record.group_by_value,
            #         "Stratification": record.stratification.label_name if record.stratification else "",
            #         "removal_count": record.removal_count,
            #     })
            # df = pd.DataFrame(log_data_statewide)
            # df= df.sort_values(by="Stratification")
            # df.to_excel("statewide_data.xlsx", index=False)
            # logger.info("Statewide data exported to statewide_data.xlsx")


            #Group data by stratification and period
            grouped_data = {}
            for record in combined_dataset:
                #Transform the period field
                school_year = record.school_year
                if '-' in school_year:
                    start_year, end_year = school_year.split('-')  # unpacks the tuple
                    period = f"{start_year}-20{end_year}"  # Transform to 2023-2024 format
                else:
                    period = school_year

                # Default to "Error" if stratification is None
                stratification = record.stratification.label_name if record.stratification else "Error"

                # Group by stratification and period
                strat_key = (stratification, period)
                if strat_key not in grouped_data:
                    grouped_data[strat_key] = {
                        "layer": "State",
                        "geoid": "WI",
                        "topic": "FVDEWVAR",
                        "stratification": stratification,
                        "period": period,
                        "value": int(record.removal_count) if record.removal_count.isdigit() else 0,
                    }
                else:
                    grouped_data[strat_key]["value"] += int(record.removal_count) if record.removal_count.isdigit() else 0
                    
            # Prepare transformed data for bulk insertion
            transformed_data = [
                MetopioStateWideRemovalDataTransformation(
                    layer=data["layer"],
                    geoid=data["geoid"],
                    topic=data["topic"],
                    stratification=data["stratification"],
                    period=data["period"],
                    value=data["value"],
                )
                for data in grouped_data.values()
            ]
            
            # Insert transformed data in bulk
            with transaction.atomic():
                MetopioStateWideRemovalDataTransformation.objects.all().delete()  # Clear existing data
                MetopioStateWideRemovalDataTransformation.objects.bulk_create(transformed_data)
            logger.info(f"Successfully transformed {len(transformed_data)} records.")


            return True
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Statewide Layer Removal: {e} at line number {line_number}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def transform_Tri_County_Removal(self):
        """ Apply Tri-County Layer Transformation """
        try:
            logger.info("Starting Tri-County Layer Transformation...")

            # Fetch filtered school data, including 'Unknown' county and school_name
            school_data = SchoolRemovalData.objects.filter(
                county__in=['Outagamie', 'Winnebago', 'Calumet'],
                removal_type_description__in =['Out of School Suspension']
             ).exclude(school_name='[Districtwide]')
            logger.info(f"Filtered school data count: {school_data.count()}")

            #Add the UNKOWNN VALUES TO THE MAIN DATA SET

            #COnstruct a dictionary to store the group totals
            group_totals = defaultdict(int)
            all_students_totals = 0

            #Compute totals per GROUP_BY and track "All Students" total

            for record in school_data:
                group_totals[record.group_by] += int(record.removal_count)
                if record.group_by == "All Students":
                    all_students_totals += int(record.removal_count)
            #logger.info(f"All students totals: {all_students_totals}")
            
            group_by_totals = {}


            for record in school_data:
                key = (record.county, record.group_by, record.group_by_value)
                group_by_totals[key] = group_totals[record.group_by]
            #logger.info(f"Group totals: {group_totals}, group by totals: {group_by_totals}")

            new_unknown_records = []
            unique_records = set()

            for (record.county, record.group_by, record.group_by_value), total in group_by_totals.items():
                if record.group_by == "All Students":
                    continue
                if total < all_students_totals:
                    difference = all_students_totals - total
                    unique_key = ("Unknown",difference,record.group_by)

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        new_unknown_records.append(
                            SchoolRemovalData(
                                school_year=record.school_year,
                                agency_type=record.agency_type or "Unknown",
                                cesa=record.cesa,
                                county=record.county,
                                district_code=record.district_code,
                                school_code=record.school_code,
                                grade_group=record.grade_group or "Unknown",
                                charter_ind=record.charter_ind or "Unknown",
                                district_name=record.district_name or "Unknown",
                                school_name=record.school_name or "Unknown",
                                group_by=record.group_by,
                                group_by_value="Unknown",
                                removal_type_description = record.removal_type_description,
                                tfs_enrollment_count = record.tfs_enrollment_count,
                                stratification=record.stratification,
                                removal_count=str(difference),)
                            )
                        logger.info(f"Added new unique unknown record for {unique_key[1]} for {record.group_by}")
                    else:
                        logger.info(f"Duplicate unknown record for {unique_key[1]} for {record.group_by}")

            
            for record in new_unknown_records:
                logger.info(f"New unknown record: {record.county:<{15}} {record.group_by:<{20}} {record.group_by_value:<{35}} {record.removal_count:<{15}}")

            # Create a combined dataset in memory
            combined_dataset = list(school_data)  # Convert QuerySet to list

            # Add the new unknown records to the combined dataset
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
                    combined_dataset.append(record)
                logger.info(f"Combined dataset count: {len(combined_dataset)}")

            #logging the Try Country Data
            log_data_tri_county = []
            for record in combined_dataset:
                
                log_data_tri_county.append({
                    "school_name": record.school_name,
                    "county": record.county,
                    "group_by": record.group_by,
                    "group_by_value": record.group_by_value,
                    "Stratification": record.stratification.label_name if record.stratification else "Unknown",
                    "removal_count": record.removal_count,
                })
            df = pd.DataFrame(log_data_tri_county)
            df= df.sort_values(by="Stratification")
            df.to_excel("tri_county_data.xlsx", index=False)
            logger.info("Tri-County data exported to tri_county_data.xlsx")


            # Group Data
            grouped_data = {}
            for record in combined_dataset:
                period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}" if '-' in record.school_year else record.school_year
                strat_label = record.stratification.label_name if record.stratification else "Unknown"
                group_by, group_by_value = record.group_by, record.group_by_value
                
                # Convert student_count to integer if it is a digit, else default to 0
                total_value = int(float(record.removal_count)) if record.removal_count.replace('.', '', 1).isdigit() else 0
                
                # Group by stratification, period, group_by, and group_by_value    
                strat_key = (strat_label)
                
                
                # Group and aggregate by strat_label, period, group_by, and group_by_value
                grouped_data.setdefault(strat_key, {
                    "layer": "Region",
                    "geoid": "fox-valley", 
                    "topic": "FVDEWVAR",
                    "period": period, 
                    "value": 0, 
                    "stratification": strat_label
                })["value"] += total_value

            # Bulk Insert Transformed Data

            transformed_data = [MetopioTriCountyRemovalDataTransformation(**{
                "layer": data["layer"],
                "geoid": data["geoid"],
                "topic": data["topic"],
                "stratification": data["stratification"],
                "period": data["period"],
                "value": data["value"]
            }) for data in grouped_data.values() if data["value"]!=0] # Exclude zero values during bulk insertion

            if transformed_data:
                with transaction.atomic():
                    MetopioTriCountyRemovalDataTransformation.objects.all().delete()
                    MetopioTriCountyRemovalDataTransformation.objects.bulk_create(transformed_data)
                logger.info(f"Successfully transformed {len(transformed_data)} records.")
            else:
                logger.info("No transformed data to insert.")

            return True

        except Exception as e:
            tb= traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Tri-County Layer Transformation: {e} at line number {line_number}")  
            return False

    def transform_County_Layer_Removal(self):
      
        try:
            logger.info("Starting County Layer Transformation...")
             # Fetch County GEOID entries
            county_geoid_entries = CountyGEOID.objects.filter(layer='County')
            county_geoid_map = {entry.name.split(" County, WI")[0].strip(): entry for entry in county_geoid_entries}

            logger.info(f"County GEOID entries count: {len(county_geoid_map)}")

            # Fetch filtered school data, including 'Unknown' county and school_name
            school_data = SchoolRemovalData.objects.filter(
                county__in=['Outagamie', 'Winnebago', 'Calumet'],
                removal_type_description__in=['Out of School Suspension']
            ).exclude(school_name='[Districtwide]')
            logger.info(f"Filtered school data count: {school_data.count()}")

            # Add the UNKOWNN VALUES TO THE MAIN DATA SET
            combined_dataset = list(school_data)  # Convert QuerySet to list
            group_totals = defaultdict(int)
            all_students_totals = defaultdict(int)


            # Compute totals per GROUP_BY and track "All Students" total

            for record in combined_dataset:
               key = (record.county, record.group_by)
               group_totals[key] += int(record.removal_count)
               if record.group_by == "All Students":
                    all_students_totals[record.county] += int(record.removal_count) 
           


            group_by_totals = {}


            for record in combined_dataset:
                key = (record.county, record.group_by, record.group_by_value, record.stratification)
                group_by_totals[key] = group_totals[(record.county, record.group_by)]
            # logger.info(f"Group  totals : {group_totals}")
            # logger.info(f"All students totals : {all_students_totals}")
            # logger.info(f"Group by totals : {group_by_totals}")

            new_unknown_records = []
            unique_records = set()

            for key, total in group_by_totals.items():
                county, group_by, group_by_value, stratification = key
                if group_by == "All Students":
                    continue
                if total < all_students_totals[(county)]:
                    difference = all_students_totals[(county)] - total
                    unique_key = (county, group_by, "Unknown")

                    if key[2] =="Unknown":
                        group_by_totals[key] += difference
                        continue

                    #Only append if this combination hasnt been seen before

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        new_unknown_records.append(
                            SchoolRemovalData(
                                school_year=record.school_year,
                                agency_type=record.agency_type or "Unknown",
                                cesa=record.cesa,
                                county=county,
                                district_code=record.district_code,
                                school_code=record.school_code,
                                grade_group=record.grade_group or "Unknown",
                                charter_ind=record.charter_ind or "Unknown",
                                district_name=record.district_name or "Unknown",
                                school_name=record.school_name or "Unknown",
                                group_by=group_by,
                                group_by_value="Unknown",
                                removal_type_description = record.removal_type_description,
                                tfs_enrollment_count = record.tfs_enrollment_count,
                                stratification=stratification,
                                removal_count=str(difference),)
                            )
                        logger.info(f"Added new unique unknown record for {unique_key}")
                    else:
                        logger.info(f"Duplicate unknown record for {unique_key}")
            # Create a combined dataset in memory
            combined_dataset.extend(new_unknown_records)  # Convert QuerySet to list
            #REALIGN ALL THE STRATIFICATION
            strat_map = {
                f"{strat.group_by}{strat.group_by_value}": strat
                for strat in Stratification.objects.all()
            }

            for record in combined_dataset:
                combined_key = record.group_by + record.group_by_value
                stratification = strat_map.get(combined_key)
                if stratification:
                    record.stratification = stratification
                else:
                    logger.warning(f"No stratification found for {combined_key}")

            #Create the exel file for the data how it looks before the grouping
            log_data =[]
            for record in combined_dataset:
                cleaned_group_by = record.group_by.replace(" ", "_")
                cleaned_group_by_value = record.group_by_value.replace(" ", "_")
                cleaned_county = record.county.replace(" ", "_")
                log_data.append({
                    "school_name": record.school_name,
                    "county": cleaned_county,
                    "group_by": cleaned_group_by,
                    "group_by_value": cleaned_group_by_value,
                    "Stratification": record.stratification.label_name if record.stratification else "Unknown",
                    "removal_count": record.removal_count,
                    

                })

            # Create a DataFrame from the log data
            df = pd.DataFrame(log_data)
            df = df.sort_values(by="Stratification")
            df.to_excel("log_data_county.xlsx", index=False)
            
            #STEP 3: Group Data
            grouped_data = {}

            for record in combined_dataset:
                period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}" if "-" in record.school_year else record.school_year
                strat_label = record.stratification.label_name if record.stratification else "Unknown"
                group_by, group_by_value = record.group_by, record.group_by_value
                geoid = county_geoid_map.get(record.county).geoid if county_geoid_map.get(record.county) else "Error"
                county=record.county
             
                
                strat_key = (county,strat_label)

                # Add to grouped data
                if strat_key not in grouped_data:
                    grouped_data[strat_key] = {
                        "layer": "County",
                        "geoid": geoid,
                        "topic": "FVDEWVAR",
                        "period": period,
                        "stratification": strat_label,
                        "value": int(record.removal_count) if record.removal_count.isdigit() else 0,
                    }
                else:
                    grouped_data[strat_key]["value"] += int(record.removal_count) if record.removal_count.isdigit() else 0
            # STEP 4: Bulk Insert Transformed Data
            transformed_data = [
                CountyLayerRemovalData(
                    layer=data["layer"],
                    geoid=data["geoid"],
                    topic=data["topic"],
                    stratification=data["stratification"],
                    period=data["period"],
                    value=data["value"]
                ) for data in grouped_data.values() if data["value"] != 0
            ]

            # Insert transformed data
            if transformed_data:
                with transaction.atomic():
                    CountyLayerRemovalData.objects.all().delete()  # Consider using bulk_update
                    CountyLayerRemovalData.objects.bulk_create(transformed_data)
                logger.info(f"Successfully transformed {len(transformed_data)} records.")
            else:
                logger.info("No transformed data to insert.")

            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during County Layer Transformation: {e} at line number {line_number}")
            return False

    def transform_Zipcode_Layer_Removal(self):
        try:
            logger.info("Starting Zipcode Layer Transformation...")

            #Fetch and Filter the Country GEOID entries
            # Fetch and filter County GEOID entries
            county_geoid_entries = CountyGEOID.objects.filter(layer="Zip code")
            logger.info(f"Filtered County GEOID entries count: {county_geoid_entries.count()}")

            # Create a map to store the Zip Code and its corresponding GEOID from the CountyGEOID entries
            zip_code_geoid_map = {entry.name: entry.geoid for entry in county_geoid_entries}

            school_removal_data = SchoolRemovalData.objects.filter(
                county__in=["Outagamie", "Winnebago", "Calumet"],
                removal_type_description__in=["Out of School Suspension"]
            ).exclude(school_name="[Districtwide]")

            #HANDLE UNKNOWN VALUES

            combined_dataset = list(school_removal_data)  # Convert QuerySet to list
            group_totals = defaultdict(int)
            all_students_totals = defaultdict(int)


            #NORMALIZE AFTER FETCHING THE DATA
            for record in combined_dataset:
                record.district_code = str(record.district_code).strip().lstrip("0")
                record.school_code = str(record.school_code).strip().lstrip("0")
            
            #logger.info(f"# Normalized the school_code district_code for {len(combined_dataset)} records.")

            # Compute totals per GROUP_BY and track "All Students" total
            #We have to do this group by total for each school which is not null


            for record in combined_dataset:
                if record.school_code is None:
                    continue
                key = (record.district_code, record.school_code, record.group_by)
                group_totals[key] += int(record.removal_count)
                if record.group_by == "All Students":
                    all_students_totals[record.district_code, record.school_code] += int(record.removal_count)

            group_by_totals = {}

            for record in combined_dataset:
                key = (record.county, record.district_code, record.school_code, record.group_by, record.group_by_value,record.stratification, record.removal_count)
                group_by_totals[key] = group_totals[(record.district_code,record.school_code,record.group_by)]

            new_unknown_records = []
            unique_records = set()

            for key,total in group_by_totals.items():
                county, district_code, school_code, group_by, group_by_value, stratification, removal_count = key
                if total <all_students_totals[(district_code, school_code)]:
                    difference = all_students_totals[(district_code, school_code)] - total
                    unique_key = (county, district_code, school_code, group_by, "Unknown")

                    if group_by_value =="Unknown":
                        group_by_totals[key] += difference
                        continue

                    #Only append if this combination hasnt been seen before

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        #create new Unknown record
                        record = next((r for r in combined_dataset if r.district_code == district_code and r.school_code == school_code and r.group_by == group_by and r.removal_count==removal_count), None)
                        if record:
                            new_record =  SchoolRemovalData(
                                    school_year=record.school_year,
                                    agency_type=record.agency_type or "Unknown",
                                    cesa=record.cesa,
                                    county=record.county,
                                    district_code=str(record.district_code).lstrip("0"),
                                    school_code=str(record.school_code).lstrip("0"),
                                    grade_group=record.grade_group or "Unknown",
                                    charter_ind=record.charter_ind or "Unknown",
                                    district_name=record.district_name or "Unknown",
                                    school_name=record.school_name or "Unknown",
                                    group_by=record.group_by,
                                    group_by_value="Unknown",
                                    removal_type_description = record.removal_type_description,
                                    tfs_enrollment_count = record.tfs_enrollment_count,
                                    stratification=record.stratification,
                                    removal_count=str(difference),
                                )
                            
                            new_unknown_records.append(new_record)
                        else:
                            logger.error(f"Record not found for district_code: {district_code}, school_code: {school_code}, group_by: {group_by}")
                    else:
                        logger.info(f"Duplicate unknown record for {unique_key}")
            logger.info(f"New unknown records count: {len(new_unknown_records)}")


            combined_dataset.extend(new_unknown_records)  # Convert QuerySet to list
            logger.info(f"#3 Normalized the school_code and district_code for {len(combined_dataset)} records")  ##3560
            
            group_by_map= {
                f"{strat.group_by}": strat
                for strat in Stratification.objects.all()
            }
            #logger.info(f"Stratification Mapping: {group_by_map}")

            
            #Create a dictionary to group records by school code and district code 
            school_code_groups = defaultdict(list)
            for record in combined_dataset:
                school_code_groups[record.school_code,record.district_code].append(record) 

            for (school_code, district_code), records in school_code_groups.items():
                existing_group_by_keys = {record.group_by for record in records}
                missing_group_by_keys = set(group_by_map.keys()) - existing_group_by_keys

                for missing_group_by_key in missing_group_by_keys:
                    reference_record = next((r for r in records if r.group_by == "All Students"), None)
                    #Create a new record for themissing group_by_key
                    new_record = SchoolRemovalData(
                        school_year=reference_record.school_year,
                        agency_type=reference_record.agency_type or "Unknown",
                        cesa=reference_record.cesa,
                        county=reference_record.county,
                        district_code=str(district_code).lstrip("0"),
                        school_code=str(school_code).lstrip("0"),
                        grade_group=reference_record.grade_group or "Unknown",
                        charter_ind=reference_record.charter_ind or "Unknown",
                        district_name=reference_record.district_name or "Unknown",
                        school_name=reference_record.school_name or "Unknown",
                        group_by=missing_group_by_key,
                        group_by_value="Unknown",
                        removal_type_description = reference_record.removal_type_description,
                        tfs_enrollment_count = reference_record.tfs_enrollment_count,
                        stratification=reference_record.stratification,
                        removal_count=str(all_students_totals[reference_record.district_code, reference_record.school_code]),  # Default value for missing records
                    )

                    combined_dataset.append(new_record)
                    logger.info(f"Added new record for missing group_by_key: {missing_group_by_key}")

            #REALIGNING STRATIFICATIONS SINCE WE RE ADDED THE UNKNOWNS
            strat_map = {
                f"{strat.group_by}{strat.group_by_value}": strat
                for strat in Stratification.objects.all()
            }
           
            for record in combined_dataset:
                combined_key = record.group_by + record.group_by_value
                record.stratification = strat_map.get(combined_key)   #assigning the stratification for the data
            #logger.info(f"Stratification for {combined_key} is {record.stratification.label_name}")
            
            
            
            
            zip_Code_Map = {
                (d.lea_code.lstrip("0"), d.school_code.lstrip("0")): d.zip_code
                for d in SchoolAddressFile.objects.all()
            }

            # Convert zip_Code_Map to a list of dictionaries
            zip_code_map_list = [
                {"lea_code": key[0], "school_code": key[1], "zip_code": value}
                for key, value in zip_Code_Map.items()
            ]


            # Create a DataFrame from the list of dictionaries
            zip_code_df = pd.DataFrame(zip_code_map_list)

            # Export the DataFrame to an Excel file
            zip_code_df.to_excel("zip_code_map.xlsx", index=False)
            logger.info("Zip Code Map exported to zip_code_map.xlsx")
                
            
            
            # Assign a Zip code to each record in the combined dataset to view the records
            # This is where the zip code gets added and will be used for the final layering logic
            for record in combined_dataset:
                record.district_code = str(record.district_code).strip().lstrip("0")
                record.school_code = str(record.school_code).strip().lstrip("0")

                combined_key = (record.district_code, record.school_code)
                zip_code = zip_Code_Map.get(combined_key, "Not Found")
                record.zip_code = zip_code
            
            
            #Sorting the COmbined data set to view how this look Just to Generate how the data looks until now
            combined_dataset.sort(key=lambda x: (x.district_code, x.school_code, x.group_by,x.school_name))
            
            #THis is just for logging and debugging
            # for record in combined_dataset:
            #     logger.info(f"Record: {record.district_code:<{15}} {record.school_code:<{15}} {record.school_name:<{40}} {record.zip_code:<{15}} ")

            # Collect log data into a list
            log_data = []
            for record in combined_dataset:
                cleaned_district_code = record.district_code
                cleaned_school_code = record.school_code

                log_data.append({
                    "district_code": cleaned_district_code,
                    "school_code": cleaned_school_code,
                    "school_name": record.school_name,
                    "group_by": record.group_by,
                    "group_by_value": record.group_by_value,
                    "Stratification": record.stratification.label_name if record.stratification else "Unknown",
                    "removal count": int(record.removal_count),
                    "zip_code": record.zip_code
                })

                # logger.info(
                #     f"Record: {cleaned_district_code:<{15}} {cleaned_school_code:<{15}} {record.school_name:<{40}} {record.zip_code:<{15}}"
                # )
                        # Create a DataFrame from the log data
            df = pd.DataFrame(log_data)
            df = df.sort_values(by="Stratification")

            # Export the DataFrame to an Excel file
            df.to_excel("log_data_zip_code_Removal.xlsx", index=False)
            logger.info("Log data exported to log_data_zip_code_Removal.xlsx")

            
            
             # Process records for transformation
            grouped_data = {}
            for record in combined_dataset:
                period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}" if "-" in record.school_year else record.school_year
                strat_label = record.stratification.label_name if record.stratification else "Error"
                 # Ensure the zip_code attribute is present
                
                district_code = record.district_code
                school_code = record.school_code
                zip_code = record.zip_code
                
                # Map the zip code to its GEOID
                geoid=zip_code_geoid_map.get(zip_code, "Error")
                if geoid == "Error":
                    #logger.warning(f"GEOID not found for zip code: {zip_code}")
                    continue

                # Group by stratification and period
                strat_key = (strat_label,geoid)

                if strat_key not in grouped_data:
                        grouped_data[strat_key] = {
                            "layer": "Zip code",
                            "geoid": geoid,
                            "topic": "FVDEWVAR",
                            "stratification": strat_label,
                            "period": period,
                            "value": int(record.removal_count) if record.removal_count.isdigit() else 0,
                        }
                else:
                    grouped_data[strat_key]["value"] += int(record.removal_count) if record.removal_count.isdigit() else 0
               
                    

            zip_54915_count=sum(
                1 for record in combined_dataset
                if record.zip_code == "54915" 
            )
            logger.info(f"Total records with ZIP code 54915: {zip_54915_count}")
            

               
           # Check how many records exist with zip_code 54915 in the raw dataset
            logger.info("=== DEBUG: Checking all records with ZIP Code 54915 ===")
            count_54915 = 0
            for record in combined_dataset:   
                if record.zip_code == "54915":
                        count_54915 += 1
                        #logger.info(f"Record: School {record.school_name}, District {record.district_name}, County {record.county}, Student Count {record.student_count}")

            logger.info(f"Total raw records with ZIP 54915: {count_54915}")

            total_raw = 0
            logger.info("=== DEBUG: Computing total_raw for ZIP Code 54915 ===")

            for record in combined_dataset:
                    if record.zip_code == "54915":
                        try:
                            student_count = int(record.removal_count) if str(record.removal_count).isdigit() else 0
                            total_raw += student_count
                            #logger.info(f"Adding {student_count} from School {record.school_name}, School Code {record.school_code} , District Code {record.district_code}")
                        except Exception as e:
                            logger.error(f"Error converting student_count for record {record.school_name}: {e}")

            logger.info(f"Raw Total: {total_raw}")

                        
            
            #Identify the missing records
            missing_records =[
                record for record in combined_dataset
                if getattr(record,"geoid",None) == "54915" and  record.removal_count not in [data["value"] for data in grouped_data.values()]
            ]
            
            if missing_records:
                logger.warning(f"Missing records: {missing_records}")
            else:
                logger.info("No missing records found")
            
            
            
            
            
            # Prepare transformed data for bulk insertion
            transformed_data = [
                ZipCodeLayerRemovalData(
                    layer=data["layer"],
                    geoid=data["geoid"],
                    topic=data["topic"],
                    stratification=data["stratification"],
                    period=data["period"],
                    value=data["value"],
                )
                for data in grouped_data.values()
            ]

            # Insert transformed data in bulk
            with transaction.atomic():
                ZipCodeLayerRemovalData.objects.all().delete()  # Clear existing data
                ZipCodeLayerRemovalData.objects.bulk_create(transformed_data)

            logger.info(f"Successfully transformed {len(transformed_data)} records.")


            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Metopio ZipCode Layer Transformation: {e} at line number {line_number}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def transform_Zipcode_Layer_Removal_OPTIMIZED(self):
        """
        OPTIMIZED VERSION - Replicates OLD logic exactly but with optimized queries
        
        Key optimizations:
        1. select_related() for stratification to avoid N+1 queries
        2. Efficient bulk fetching of lookup maps
        3. Single atomic transaction for all inserts
        
        Business logic (matching OLD method exactly):
        1. Handle "Unknown" stratifications by calculating differences from "All Students"
        2. Add missing group_by categories for each school
        3. Realign stratifications after adding unknowns
        4. Group by (stratification, geoid) ignoring period
        """
        try:
            from django.db.models import F, Q, Sum, Count, Value
            from django.db.models.functions import Concat, LPad
            import time
            from collections import defaultdict
            
            start_time = time.time()
            logger.info("Starting OPTIMIZED Zipcode Layer Removal Transformation...")

            # OPTIMIZATION 1: Fetch lookup maps efficiently
            zip_code_geoid_map = dict(
                CountyGEOID.objects.filter(layer="Zip code")
                .values_list('name', 'geoid')
            )
            logger.info(f"Loaded {len(zip_code_geoid_map)} zip code GEOIDs")

            # OPTIMIZATION 2: Fetch all base data with select_related to avoid N+1 queries
            school_removal_data = SchoolRemovalData.objects.filter(
                county__in=["Outagamie", "Winnebago", "Calumet"],
                removal_type_description__in=["Out of School Suspension"]
            ).exclude(school_name="[Districtwide]").select_related('stratification')

            combined_dataset = list(school_removal_data)
            
            # STEP 1: Normalize district/school codes (matching OLD logic)
            for record in combined_dataset:
                record.district_code = str(record.district_code).strip().lstrip("0")
                record.school_code = str(record.school_code).strip().lstrip("0")
            
            # STEP 2: Calculate group totals and "All Students" totals (matching OLD logic lines 585-591)
            group_totals = defaultdict(int)
            all_students_totals = defaultdict(int)
            
            for record in combined_dataset:
                if record.school_code is None:
                    continue
                key = (record.district_code, record.school_code, record.group_by)
                group_totals[key] += int(record.removal_count)
                if record.group_by == "All Students":
                    all_students_totals[record.district_code, record.school_code] += int(record.removal_count)

            # STEP 3: Build group_by_totals map (matching OLD logic lines 593-595)
            group_by_totals = {}
            for record in combined_dataset:
                key = (record.county, record.district_code, record.school_code, record.group_by, 
                       record.group_by_value, record.stratification, record.removal_count)
                group_by_totals[key] = group_totals[(record.district_code, record.school_code, record.group_by)]

            # STEP 4: Handle "Unknown" records - calculate differences from "All Students" (matching OLD logic lines 597-649)
            new_unknown_records = []
            unique_records = set()

            for key, total in group_by_totals.items():
                county, district_code, school_code, group_by, group_by_value, stratification, removal_count = key
                if total < all_students_totals[(district_code, school_code)]:
                    difference = all_students_totals[(district_code, school_code)] - total
                    unique_key = (county, district_code, school_code, group_by, "Unknown")

                    if group_by_value == "Unknown":
                        group_by_totals[key] += difference
                        continue

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        record = next((r for r in combined_dataset if r.district_code == district_code and 
                                     r.school_code == school_code and r.group_by == group_by and 
                                     r.removal_count == removal_count), None)
                        if record:
                            new_record = SchoolRemovalData(
                                school_year=record.school_year,
                                agency_type=record.agency_type or "Unknown",
                                cesa=record.cesa,
                                county=record.county,
                                district_code=str(record.district_code).lstrip("0"),
                                school_code=str(record.school_code).lstrip("0"),
                                grade_group=record.grade_group or "Unknown",
                                charter_ind=record.charter_ind or "Unknown",
                                district_name=record.district_name or "Unknown",
                                school_name=record.school_name or "Unknown",
                                group_by=record.group_by,
                                group_by_value="Unknown",
                                removal_type_description=record.removal_type_description,
                                tfs_enrollment_count=record.tfs_enrollment_count,
                                stratification=record.stratification,
                                removal_count=str(difference),
                            )
                            new_unknown_records.append(new_record)

            logger.info(f"New unknown records count: {len(new_unknown_records)}")
            combined_dataset.extend(new_unknown_records)

            # STEP 5: Add missing group_by categories for each school (matching OLD logic lines 654-688)
            group_by_map = {f"{strat.group_by}": strat for strat in Stratification.objects.all()}
            school_code_groups = defaultdict(list)
            
            for record in combined_dataset:
                school_code_groups[record.school_code, record.district_code].append(record)

            for (school_code, district_code), records in school_code_groups.items():
                existing_group_by_keys = {record.group_by for record in records}
                missing_group_by_keys = set(group_by_map.keys()) - existing_group_by_keys

                for missing_group_by_key in missing_group_by_keys:
                    reference_record = next((r for r in records if r.group_by == "All Students"), None)
                    if reference_record:
                        new_record = SchoolRemovalData(
                            school_year=reference_record.school_year,
                            agency_type=reference_record.agency_type or "Unknown",
                            cesa=reference_record.cesa,
                            county=reference_record.county,
                            district_code=str(district_code).lstrip("0"),
                            school_code=str(school_code).lstrip("0"),
                            grade_group=reference_record.grade_group or "Unknown",
                            charter_ind=reference_record.charter_ind or "Unknown",
                            district_name=reference_record.district_name or "Unknown",
                            school_name=reference_record.school_name or "Unknown",
                            group_by=missing_group_by_key,
                            group_by_value="Unknown",
                            removal_type_description=reference_record.removal_type_description,
                            tfs_enrollment_count=reference_record.tfs_enrollment_count,
                            stratification=reference_record.stratification,
                            removal_count=str(all_students_totals[reference_record.district_code, reference_record.school_code]),
                        )
                        combined_dataset.append(new_record)

            # STEP 6: Realign stratifications after adding unknowns (matching OLD logic lines 690-698)
            strat_map = {f"{strat.group_by}{strat.group_by_value}": strat for strat in Stratification.objects.all()}
            for record in combined_dataset:
                combined_key = record.group_by + record.group_by_value
                record.stratification = strat_map.get(combined_key)

            # OPTIMIZATION 3: Use efficient lookup map for zip codes
            zip_Code_Map = dict(
                SchoolAddressFile.objects.values_list('lea_code', 'school_code')
                .annotate(key=Concat(F('lea_code'), Value(''), F('school_code')))
                .values_list('key', 'zip_code')
            )
            
            # Also create normalized key version
            for d in SchoolAddressFile.objects.all():
                key = (d.lea_code.lstrip("0"), d.school_code.lstrip("0"))
                zip_Code_Map[key] = d.zip_code

            # STEP 7: Assign zip codes to records (matching OLD logic lines 739-742)
            for record in combined_dataset:
                combined_key = (record.district_code, record.school_code)
                zip_code = zip_Code_Map.get(combined_key, "Not Found")
                record.zip_code = zip_code
            
            # STEP 8: Group data by (stratification, geoid) - matching OLD logic lines 774-802
            grouped_data = {}
            for record in combined_dataset:
                period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}" if "-" in record.school_year else record.school_year
                strat_label = record.stratification.label_name if record.stratification else ""
                
                district_code = record.district_code
                school_code = record.school_code
                zip_code = record.zip_code
                
                # Map the zip code to its GEOID
                geoid = zip_code_geoid_map.get(zip_code, "Error")
                if geoid == "Error":
                    continue

                # Group by (stratification, geoid) ONLY - matching OLD line 792
                strat_key = (strat_label, geoid)

                if strat_key not in grouped_data:
                    grouped_data[strat_key] = {
                        "layer": "Zip code",
                        "geoid": geoid,
                        "topic": "FVDEWVAR",
                        "stratification": strat_label,
                        "period": period,
                        "value": int(record.removal_count) if record.removal_count.isdigit() else 0,
                    }
                else:
                    grouped_data[strat_key]["value"] += int(record.removal_count) if record.removal_count.isdigit() else 0

            # STEP 9: Prepare transformed data for bulk insertion
            transformed_data = [
                ZipCodeLayerRemovalData(
                    layer=data["layer"],
                    geoid=data["geoid"],
                    topic=data["topic"],
                    stratification=data["stratification"],
                    period=data["period"],
                    value=data["value"],
                )
                for data in grouped_data.values()
            ]

            # OPTIMIZATION 5: Single atomic transaction for all operations
            with transaction.atomic():
                ZipCodeLayerRemovalData.objects.all().delete()
                if transformed_data:
                    ZipCodeLayerRemovalData.objects.bulk_create(
                        transformed_data,
                        batch_size=500  # Process in batches to avoid memory issues
                    )

            elapsed_time = time.time() - start_time
            logger.info(f"✅ OPTIMIZED transformation complete: {len(transformed_data)} records in {elapsed_time:.2f}s")
            logger.info(f"   Successfully transformed {len(transformed_data)} records.")
            if elapsed_time > 0:
                logger.info(f"   Performance: {int(len(transformed_data)/elapsed_time)} records/second")

            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during OPTIMIZED ZipCode Layer Transformation: {e} at line {line_number}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        
    def transform_City_Layer_Removal(self):
        try:
            logger.info("Starting City Layer Transformation...")

            #Fetch and Filter the Country GEOID entries
            # Fetch and filter County GEOID entries
            county_geoid_entries = CountyGEOID.objects.filter(layer="City or town")
            logger.info(f"Filtered County GEOID entries count: {county_geoid_entries.count()}")

            # Create a map to store the City and its corresponding GEOID from the County GEOID entries
            city_geoid_map = {entry.name: entry.geoid for entry in county_geoid_entries}

            school_removal_data = SchoolRemovalData.objects.filter(
                ~Q(school_name__startswith='['),
                county__in=["Outagamie", "Winnebago", "Calumet"],
                removal_type_description__in=["Out of School Suspension"]
            ).distinct()
                
            #HANDLE UNKNOWN VALUES

            combined_dataset = list(school_removal_data)  # Convert QuerySet to list
            group_totals = defaultdict(int)
            all_students_totals = defaultdict(int)


            #NORMALIZE AFTER FETCHING THE DATA
            for record in combined_dataset:
                record.district_code = str(record.district_code).strip().lstrip("0")
                record.school_code = str(record.school_code).strip().lstrip("0")
            
            logger.info(f"# Normalized the school_code district_code for {len(combined_dataset)} records.")

            # Compute totals per GROUP_BY and track "All Students" total
            #We have to do this group by total for each school which is not null


            for record in combined_dataset:
                if record.school_code is None:
                    continue
                key = (record.district_code, record.school_code, record.group_by)
                group_totals[key] += int(record.removal_count)
                if record.group_by == "All Students":
                    all_students_totals[record.district_code, record.school_code] += int(record.removal_count)

            group_by_totals = {}

            for record in combined_dataset:
                key = (record.county, record.district_code, record.school_code, record.group_by, record.group_by_value,record.stratification)
                group_by_totals[key] = group_totals[(record.district_code,record.school_code,record.group_by)]

            #Handling the Unknown Records
            new_unknown_records = []
            unique_records = set()

            for key,total in group_by_totals.items():
                county, district_code, school_code, group_by, group_by_value, stratification = key
                if total <all_students_totals[(district_code, school_code)]:
                    difference = all_students_totals[(district_code, school_code)] - total
                    unique_key = (county, district_code, school_code, group_by, "Unknown")

                    if group_by_value =="Unknown":
                        group_by_totals[key] += difference
                        continue

                    #Only append if this combination hasnt been seen before

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        #create new Unknown record
                        record = next((r for r in combined_dataset if r.district_code == district_code and r.school_code == school_code and r.group_by == group_by), None)
                        if record:
                            new_record =  SchoolRemovalData(
                                    school_year=record.school_year,
                                    agency_type=record.agency_type or "Unknown",
                                    cesa=record.cesa,
                                    county=county,
                                    district_code=str(district_code).lstrip("0"),
                                    school_code=str(school_code).lstrip("0"),
                                    grade_group=record.grade_group or "Unknown",
                                    charter_ind=record.charter_ind or "Unknown",
                                    district_name=record.district_name or "Unknown",
                                    school_name=record.school_name or "Unknown",
                                    group_by=group_by,
                                    group_by_value="Unknown",
                                    removal_type_description = record.removal_type_description,
                                    tfs_enrollment_count = record.tfs_enrollment_count,
                                    stratification=stratification,
                                    removal_count=str(difference),
                                )
                            
                            new_unknown_records.append(new_record)
                        else:
                            logger.error(f"Record not found for district_code: {district_code}, school_code: {school_code}, group_by: {group_by}")
                    else:
                        logger.info(f"Duplicate unknown record for {unique_key}")
            logger.info(f"New unknown records count: {len(new_unknown_records)}")

            #UPDATE THE COMBINED DATASET

            combined_dataset.extend(new_unknown_records)  # Convert QuerySet to list
            
            
            group_by_map= {
                f"{strat.group_by}": strat
                for strat in Stratification.objects.all()
            }
            #logger.info(f"Stratification Mapping: {group_by_map}")

            
            #Create a dictionary to group records by school code and district code 
            school_code_groups = defaultdict(list)
            for record in combined_dataset:
                school_code_groups[record.school_code,record.district_code].append(record) 

            for (school_code, district_code), records in school_code_groups.items():
                existing_group_by_keys = {record.group_by for record in records}
                missing_group_by_keys = set(group_by_map.keys()) - existing_group_by_keys

                for missing_group_by_key in missing_group_by_keys:
                    reference_record = next((r for r in records if r.group_by == "All Students"), None)
                    #Create a new record for themissing group_by_key
                    new_record = SchoolRemovalData(
                        school_year=reference_record.school_year,
                        agency_type=reference_record.agency_type or "Unknown",
                        cesa=reference_record.cesa,
                        county=reference_record.county,
                        district_code=str(district_code).lstrip("0"),
                        school_code=str(school_code).lstrip("0"),
                        grade_group=reference_record.grade_group or "Unknown",
                        charter_ind=reference_record.charter_ind or "Unknown",
                        district_name=reference_record.district_name or "Unknown",
                        school_name=reference_record.school_name or "Unknown",
                        group_by=missing_group_by_key,
                        group_by_value="Unknown",
                        removal_type_description = reference_record.removal_type_description,
                        tfs_enrollment_count = reference_record.tfs_enrollment_count,
                        stratification=reference_record.stratification,
                        removal_count=str(all_students_totals[reference_record.district_code, reference_record.school_code]),  # Default value for missing records
                    )

                    combined_dataset.append(new_record)
                    logger.info(f"Added new record for missing group_by_key: {missing_group_by_key}")
            #Create a dictionary to grup records by school code
            school_code_groups_xlx_log = defaultdict(list)
            for record in combined_dataset:
                school_code_groups_xlx_log[record.school_code, district_code].append(record)

            # Prepare data for export
            export_data = []
            for (school_code,district_code), records in school_code_groups_xlx_log.items():
                for record in records:
                    export_data.append({
                        "school_code": school_code,
                        "school_year": record.school_year,
                        "agency_type": record.agency_type,
                        "cesa": record.cesa,
                        "county": record.county,
                        "district_code": record.district_code,
                        "school_code": record.school_code,
                        "grade_group": record.grade_group,
                        "charter_ind": record.charter_ind,
                        "district_name": record.district_name,
                        "school_name": record.school_name,
                        "group_by": record.group_by,
                        "group_by_value": record.group_by_value,
                        "removal_count": record.removal_count,
                        "removal_type_description": record.removal_type_description,
                        "tfs_enrollment_count": record.tfs_enrollment_count,
                        "stratification": record.stratification.label_name if record.stratification else "Unknown",
                    })

            # Create a DataFrame from the export data
            df = pd.DataFrame(export_data)

            # Export the DataFrame to an Excel file
            df.to_excel("school_code_groups_city.xlsx", index=False)
            logger.info("School code groups exported to school_code_groups_city.xlsx")

            #REALIGN STRATIFICATION SINCE WE ADDED NEW RECORDS
            strat_map = {
                f"{strat.group_by}{strat.group_by_value}": strat
                for strat in Stratification.objects.all()
            }
            for record in combined_dataset:
                combined_key = record.group_by + record.group_by_value
                record.stratification = strat_map.get(combined_key) #assigning the stratification for the data
                #logger.info(f"Stratification for {combined_key} is {record.stratification}")

            logger.info(f"Combined dataset count: {len(combined_dataset)}")
            
            #REALIGNING THE CITY
            # Assign a City to each record in the combined dataset
            city_code_map = {
                (d.lea_code.lstrip("0"), d.school_code.lstrip("0")): d.city
                for d in SchoolAddressFile.objects.all()
            }
            
            #Assign a city to each record in the combined dataset
            for record in combined_dataset:
                record.district_code = str(record.district_code).strip().lstrip("0")
                record.school_code = str(record.school_code).strip().lstrip("0")
                
                combined_key = (record.district_code, record.school_code)
                city = city_code_map.get(combined_key, "Not Found")
                setattr(record, "city", city)

            #Sorting the COmbined data set to view how this look Just to Generate how the data looks until now
            combined_dataset.sort(key=lambda x: (x.district_code, x.school_code, x.group_by,x.school_name))
            
            #THis is just for logging and debugging
            # for record in combined_dataset:
            #     logger.info(f"Record: {record.district_code:<{15}} {record.school_code:<{15}} {record.school_name:<{40}} {record.zip_code:<{15}} ")

            # Collect log data into a list
            log_data = []
            for record in combined_dataset:
                cleaned_district_code = record.district_code
                cleaned_school_code = record.school_code

                log_data.append({
                    "district_code": cleaned_district_code,
                    "school_code": cleaned_school_code,
                    "school_name": record.school_name,
                    "group_by": record.group_by,
                    "group_by_value": record.group_by_value,
                    "Stratification": record.stratification.label_name if record.stratification else "Unknown",
                    "removal_count": int(record.removal_count),
                    "city": record.city
                })

                # logger.info(
                #     f"Record: {cleaned_district_code:<{15}} {cleaned_school_code:<{15}} {record.school_name:<{40}} {record.zip_code:<{15}}"
                # )
                        # Create a DataFrame from the log data
            df = pd.DataFrame(log_data)
            df = df.sort_values(by="Stratification")

            # Export the DataFrame to an Excel file
            df.to_excel("log_data_city.xlsx", index=False)
            logger.info("Log data exported to log_data.xlsx")

            # Process records for transformation
            grouped_data = {}
            for record in combined_dataset:
            
                period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}" if "-" in record.school_year else record.school_year
                strat_label = record.stratification.label_name if record.stratification else "Strat_Error"

                # Extract the city
                city = record.city + ", WI"  # Adding ", WI" to match the format in the CountyGEOID file

                # Map the city from the SchoolAddressFile to its GEOID from the CountyGEOID file
                geoid = city_geoid_map.get(city, "Error")
                if geoid == "Error":
                    logger.warning(f"GEOID not found for city: {city}")
                    continue

                # Group by stratification and period
                strat_key = (strat_label, geoid)

                if strat_key not in grouped_data:
                    grouped_data[strat_key] = {
                        "layer": "City or town",
                        "geoid": geoid,
                        "topic": "FVDEWVAR",
                        "stratification": strat_label,
                        "period": period,
                        "value": int(record.removal_count) if record.removal_count.isdigit() else 0,
                    }
                else:
                    grouped_data[strat_key]["value"] += int(record.removal_count) if record.removal_count.isdigit() else 0



            # Prepare transformed data for bulk insertion
            transformed_data = [
                MetopioCityRemovalData(
                    layer=data["layer"],
                    geoid=data["geoid"],
                    topic=data["topic"],
                    stratification=data["stratification"],
                    period=data["period"],
                    value=data["value"],
                )
                for data in grouped_data.values()
            ]

            # Insert transformed data in bulk
            with transaction.atomic():
                MetopioCityRemovalData.objects.all().delete()  # Clear existing data
                MetopioCityRemovalData.objects.bulk_create(transformed_data)
            logger.info(f"Successfully transformed {len(transformed_data)} records.")


            return True
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Metopio City Layer Transformation: {e} at line number {line_number}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
                
    def transform_combined_removal(self):
        """Apply Combined Removal Transformation by calling individual removal transformations and saving the results."""
        try:
            logger.info("Starting Combined Removal Transformation...")

            # Clear existing data in CombinedRemovalData
            CombinedRemovalData.objects.all().delete()

            # Initialize a list to hold all combined data
            combined_data = []

            # Call each individual removal transformation function and collect data
            if not self.transform_Statewide_Removal():
                logger.error("Statewide Removal Transformation failed.")
                return False
            combined_data.extend(
                MetopioStateWideRemovalDataTransformation.objects.values(
                    "layer", "geoid", "topic", "stratification", "period", "value"
                )
            )

            if not self.transform_Tri_County_Removal():
                logger.error("Tri-County Removal Transformation failed.")
                return False
            combined_data.extend(
                MetopioTriCountyRemovalDataTransformation.objects.values(
                    "layer", "geoid", "topic", "stratification", "period", "value"
                )
            )

            if not self.transform_County_Layer_Removal():
                logger.error("County Layer Removal Transformation failed.")
                return False
            combined_data.extend(
                CountyLayerRemovalData.objects.values(
                    "layer", "geoid", "topic", "stratification", "period", "value"
                )
            )

            if not self.transform_Zipcode_Layer_Removal():
                logger.error("Zipcode Layer Removal Transformation failed.")
                return False
            combined_data.extend(
                ZipCodeLayerRemovalData.objects.values(
                    "layer", "geoid", "topic", "stratification", "period", "value"
                )
            )

            if not self.transform_City_Layer_Removal():
                logger.error("City Layer Removal Transformation failed.")
                return False
            combined_data.extend(
                MetopioCityRemovalData.objects.values(
                    "layer", "geoid", "topic", "stratification", "period", "value"
                )
            )

            # Bulk insert the combined data into CombinedRemovalData
            combined_instances = [
                CombinedRemovalData(
                    layer=row["layer"],
                    geoid=row["geoid"],
                    topic=row["topic"],
                    stratification=row["stratification"],
                    period=row["period"],
                    value=row["value"],
                )
                for row in combined_data
            ]
            CombinedRemovalData.objects.bulk_create(combined_instances)

            logger.info("Combined Removal Transformation completed successfully.")
                
            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Combined Removal Transformation: {e} at line number {line_number}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    # ============================================
    # FORWARD EXAM TRANSFORMATIONS (PP-10a)
    # ============================================
    
