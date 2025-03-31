
# data_processor/transformers.py

from .models import (
    SchoolData,
    TransformedSchoolData, 
    MetopioTriCountyLayerTransformation, 
    CountyLayerTransformation,
    CountyGEOID, 
    MetopioStateWideLayerTransformation, 
    ZipCodeLayerTransformation,
    SchoolAddressFile,
    MetopioCityLayerTransformation,
    Stratification,
    SchoolRemovalData,  # Added missing import
    MetopioStateWideRemovalDataTransformation,  # Ensure this is defined or imported correctly
    MetopioTriCountyRemovalDataTransformation,  # Added missing import
    CountyLayerRemovalData,  # Added missing import
    ZipCodeLayerRemovalData,  # Added missing import
    MetopioCityRemovalData,  # Added missing import
    CombinedRemovalData,  # Added missing import
    
)


from django.db import transaction
from django.db import models
import logging
import traceback
import pandas as pd
from collections import defaultdict
from django.db.models import Q, F
from django.contrib import messages
logger = logging.getLogger(__name__)


class DataTransformer:
    def __init__(self, request):
        self.request = request

    def transform_statewide(self):
        """ Transform 'Statewide' data from the SchoolData model """
        if not SchoolData.objects.exists():
            messages.error(self.request, 'No data found in the SchoolData model. Please upload a file first.')
            return False  # Indicate failure

        # Clear existing data in the TransformedSchoolData to avoid duplicates
        TransformedSchoolData.objects.all().delete()
        data = SchoolData.objects.filter(school_name='[Statewide]')
        transformed_data = []

        for entry in data:
            transformed_entry = TransformedSchoolData(
                year=entry.school_year[:4],
                year_range=entry.school_year,
                place='WI',
                group_by=entry.group_by,
                group_by_value=entry.group_by_value,
                student_count=entry.student_count,
            )
            transformed_data.append(transformed_entry)

        TransformedSchoolData.objects.bulk_create(transformed_data)
        messages.success(self.request, f"Statewide transformation completed successfully. {len(transformed_data)} records were transformed.")
        return True

    def transform_tri_county(self):
        """ Transform 'Tri-County' data from the SchoolData model """
        if not SchoolData.objects.exists():
            messages.error(self.request, "No data available in the database. Please upload a file before running the transformation.")
            return False  # Indicate failure

        # Clear existing data in TransformedSchoolData to avoid duplicates
        TransformedSchoolData.objects.filter(place='Tri-County').delete()
        data = SchoolData.objects.filter(
            county__in=['Outagamie', 'Winnebago', 'Calumet'],  # Filter counties
            school_name__iexact='[Districtwide]'              # Filter school_name
        )
        transformed_data = []

        for entry in data:
            transformed_entry = TransformedSchoolData(
                year=entry.school_year[:4],
                year_range=entry.school_year,
                place='Tri-County',
                group_by=entry.group_by,
                group_by_value=entry.group_by_value,
                student_count=entry.student_count,
            )
            transformed_data.append(transformed_entry)

        TransformedSchoolData.objects.bulk_create(transformed_data)
        messages.success(self.request, f"Tri-County transformation completed successfully. {len(transformed_data)} records were transformed.")
        return True

    def apply_transformation(self, transformation_type):
        """ Apply the selected transformation type """
        if transformation_type == 'Statewide V01':
            return self.transform_statewide()
        elif transformation_type == 'Tri-County':
            return self.apply_tri_county_layer_transformation()
        else:
            messages.error(self.request, 'Unknown transformation type.')
            return False

    def apply_tri_county_layer_transformation(self):
        """ Apply Tri-County Layer Transformation """
        try:
            logger.info("Starting Tri-County Layer Transformation...")
            logger.info(f"{SchoolData.objects.count()} records found in the SchoolData model.")
            # Fetch filtered school data, including 'Unknown' county and school_name
            school_data = SchoolData.objects.filter(
                county__in=['Outagamie', 'Winnebago', 'Calumet'],
             ).exclude(school_name='[Districtwide]')
            logger.info(f"Filtered school data count: {school_data.count()}")

            #Add the UNKOWNN VALUES TO THE MAIN DATA SET

            #COnstruct a dictionary to store the group totals
            group_totals = defaultdict(int)
            all_students_totals = 0

            #Compute totals per GROUP_BY and track "All Students" total

            for record in school_data:
                group_totals[record.group_by] += int(record.student_count)
                if record.group_by == "All Students":
                    all_students_totals += int(record.student_count)

            
            group_by_totals = {}


            for record in school_data:
                key = (record.county, record.group_by, record.group_by_value)
                group_by_totals[key] = group_totals[record.group_by]


            new_unknown_records = []
            unique_records = set()

            for (record.county, record.group_by, record.group_by_value), total in group_by_totals.items():
                if record.group_by == "All Students":
                    continue
                if total < all_students_totals:
                    difference = all_students_totals - total
                    unique_key = ("Unknown", difference)

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        new_unknown_records.append(
                            SchoolData(
                                  school_name=record.school_name,
                                    county=record.county,
                                    group_by=record.group_by,
                                    group_by_value="Unknown",
                                    school_year=record.school_year,
                                    student_count=str(difference),  # Keep redacted data
                                    stratification=record.stratification,
                                    agency_type=record.agency_type,
                                    cesa=record.cesa,
                                    district_code=record.district_code,
                                    school_code=record.school_code,
                                    grade_group=record.grade_group,
                                    charter_ind=record.charter_ind,
                                    district_name=record.district_name,
                                    percent_of_group=record.percent_of_group,
                            ))
                        logger.info(f"Added new unique unknown record for {unique_key}")
                    else:
                        logger.info(f"Duplicate unknown record for {unique_key}")

            
            for record in new_unknown_records:
                logger.info(f"New unknown record: {record.county:<{15}} {record.group_by:<{20}} {record.group_by_value:<{35}} {record.student_count}")

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


            # Group Data
            grouped_data = {}
            for record in combined_dataset:
                period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}" if '-' in record.school_year else record.school_year
                strat_label = record.stratification.label_name if record.stratification else "Unknown"
                group_by, group_by_value = record.group_by, record.group_by_value
                
                # Convert student_count to integer if it is a digit, else default to 0
                total_value = int(float(record.student_count)) if record.student_count.replace('.', '', 1).isdigit() else 0
                
                # Group by stratification, period, group_by, and group_by_value    
                strat_key = (strat_label)
                
                
                # Group and aggregate by strat_label, period, group_by, and group_by_value
                grouped_data.setdefault(strat_key, {
                    "layer": "Region",
                    "geoid": "fox-valley", 
                    "topic": "FVDEYLCV",
                    "period": period, 
                    "value": 0, 
                    "stratification": strat_label
                })["value"] += total_value

            # Bulk Insert Transformed Data

            transformed_data = [MetopioTriCountyLayerTransformation(**{
                "layer": data["layer"],
                "geoid": data["geoid"],
                "topic": data["topic"],
                "stratification": data["stratification"],
                "period": data["period"],
                "value": data["value"]
            }) for data in grouped_data.values() if data["value"]!=0] # Exclude zero values during bulk insertion

            if transformed_data:
                with transaction.atomic():
                    MetopioTriCountyLayerTransformation.objects.all().delete()
                    MetopioTriCountyLayerTransformation.objects.bulk_create(transformed_data)
                logger.info(f"Successfully transformed {len(transformed_data)} records.")
            else:
                logger.info("No transformed data to insert.")

            return True

        except Exception as e:
            tb= traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Tri-County Layer Transformation: {e} at line number {line_number}")  
            return False

# Apply the county Layer Transformation 

    def apply_county_layer_transformation(self):
        try:
            # Reinitialize school Data
            logger.info("Starting County Layer Transformation...")

            # Fetch County GEOID entries
            county_geoid_entries = CountyGEOID.objects.filter(layer='County')
            county_geoid_map = {entry.name.split(" County, WI")[0].strip(): entry for entry in county_geoid_entries}

            logger.info(f"County GEOID entries count: {len(county_geoid_map)}")

            # STEP 2: Fetch dataset (No need to process "Unknown" separately)
            school_data = SchoolData.objects.filter(
                models.Q(county__in=county_geoid_map.keys())
            ).exclude(school_name="[Districtwide]")
            logger.info(f"Refetched school data count: {school_data.count()}")
            
            #HANDLE UNKOWN
            combined_dataset = list(school_data)  # Convert QuerySet to list
            group_totals =defaultdict(int)
            all_students_totals = defaultdict(int)
            
            #Compute totals per GROUP_BY and track "All Students" total
            # You have to nest it down to county level
            
            for record in combined_dataset:               
                key = (record.county, record.group_by)   # using just the county and the group BY
                group_totals[key] += int(record.student_count)
                if record.group_by == "All Students":
                    all_students_totals[record.county] += int(record.student_count)
            
            group_by_totals = {}
            
            # We are assigning this new group_totals dictionary to hold the objects of the remaining columsn
            for record in combined_dataset:
                key=(record.county,record.group_by,record.group_by_value,record.stratification)
                group_by_totals[key] = group_totals[(record.county, record.group_by)]   
            #logger.info(f"The Group_By_Totals length : {len(group_by_totals)}")
            #logger.info(f"The Group_Totals length : {len(group_totals)}")
            #logger.info(f"**********************Group by totals: {group_by_totals} ====== and **********************Group totals: {group_totals}")
            
            new_unknown_records = []
            unique_records =set()
            
            for key, total in group_by_totals.items():
                county, group_by, group_by_value, stratification = key
                if group_by == "All Students":
                    continue
                if total < all_students_totals[(county)]:
                    difference = all_students_totals[(county)] - total
                #    logger.info(f"Difference {difference} for {record.county} {record.group_by} {record.group_by_value}= {all_students_totals} - {total}")
                   
                    unique_key = (county, group_by, "Unknown")


                    if key[2]=="Unknown":
                        group_by_totals[key] += difference
                        continue
                    
                   
                #    #Only append if this combination hasnt been seen before
                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                    #    #Create new "Unknown" record
                        new_unknown_records.append(
                                SchoolData(
                                    school_name=record.school_name,
                                    county=county,
                                    group_by=group_by,
                                    group_by_value="Unknown",
                                    school_year=record.school_year,
                                    student_count=str(difference),  # Keep redacted data
                                    stratification=stratification,
                                    agency_type=record.agency_type,
                                    cesa=record.cesa,
                                    district_code=record.district_code,
                                    school_code=record.school_code,
                                    grade_group=record.grade_group,
                                    charter_ind=record.charter_ind,
                                    district_name=record.district_name,
                                    percent_of_group=record.percent_of_group,
                                ))
                        
                        
                        logger.info(f"Added new unique unknown record for {unique_key}")
                    else:
                        logger.info(f"Duplicate unknown record for {unique_key}")
                        #logger.info(f"New unknown records count: {len(new_unknown_records)}")
            
            #create a combined data set in memory
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
                    "Stratification": record.stratification.label_name,
                    "student_count": record.student_count,
                    

                })

            df = pd.DataFrame(log_data)
            df.to_excel("before_grouping_county.xlsx", index=False)
            
            # STEP 3: Group Data
            grouped_data = {}

            for record in combined_dataset:
                period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}" if "-" in record.school_year else record.school_year
                strat_label = record.stratification.label_name 
                group_by, group_by_value = record.group_by, record.group_by_value
                geoid = county_geoid_map.get(record.county).geoid if county_geoid_map.get(record.county) else "Error"
                county=record.county
             
                
                strat_key = (county,strat_label)

                # Add to grouped data
                if strat_key not in grouped_data:
                    grouped_data[strat_key] = {
                        "layer": "County",
                        "geoid": geoid,
                        "topic": "FVDEYLCV",
                        "stratification": strat_label,
                        "period": period,
                        "value": int(record.student_count) if record.student_count.isdigit() else 0,
                    }
                else:
                    grouped_data[strat_key]["value"] += int(record.student_count) if record.student_count.isdigit() else 0
            # STEP 4: Bulk Insert Transformed Data
            transformed_data = [
                CountyLayerTransformation(
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
                    CountyLayerTransformation.objects.all().delete()  # Consider using bulk_update
                    CountyLayerTransformation.objects.bulk_create(transformed_data)
                logger.info(f"Successfully transformed {len(transformed_data)} records.")
            else:
                logger.info("No transformed data to insert.")

            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during County Layer Transformation: {e} at line number {line_number}")
            return False


    def transform_Metopio_StateWideLayer(self):
        """Apply StateWide Layer Transformation"""
        logger.info(f"{SchoolData.objects.count()} records found in the SchoolData model.")
        if not SchoolData.objects.exists():
            messages.error(self.request, 'No data found in the SchoolData model. Please upload a file first.')
            return False
        try:
            logger.info("Starting Metopio StateWide Layer Transformation...")
            # Clear the existing data in the MetopioStateWideLayerTransformation to avoid duplicates
            MetopioStateWideLayerTransformation.objects.all().delete()
            
            #Define filters for DISTRICT_NAME =[Statewide]
            district_name_filter = '[Statewide]'
            
            #Fetch filtered school data
            
            school_data = SchoolData.objects.filter(district_name=district_name_filter)
            logger.info(f"Filtered school data count: {school_data.count()}")
            

            #Handle unknown values
            # Construct a dictionary to store the group totals
            group_totals = defaultdict(int)
            all_students_totals = 0

            # Compute totals per GROUP_BY and track "All Students" total

            for record in school_data:
                group_totals[record.group_by] += int(record.student_count)
                if record.group_by == "All Students":
                    all_students_totals += int(record.student_count)

            group_by_totals = {}

            for record in school_data:
                key = (record.group_by, record.group_by_value)
                group_by_totals[key] = group_totals[record.group_by]


            new_unknown_records = []
            unique_records = set()
            #logger.info(f"Group by totals: {group_by_totals}")
            for (record.group_by, record.group_by_value), total in group_by_totals.items():
                if record.group_by == "All Students":
                    continue
                if total < all_students_totals:
                    difference = all_students_totals - total
                    unique_key = ("Unknown", difference)

                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        new_unknown_records.append(
                            SchoolData(
                                school_name=record.school_name,
                                county=record.county,
                                group_by=record.group_by,
                                group_by_value="Unknown",
                                school_year=record.school_year,
                                student_count=str(difference),  # Keep redacted data
                                stratification=record.stratification,
                                agency_type=record.agency_type,
                                cesa=record.cesa,
                                district_code=record.district_code,
                                school_code=record.school_code,
                                grade_group=record.grade_group,
                                charter_ind=record.charter_ind,
                                district_name=record.district_name,
                                percent_of_group=record.percent_of_group,
                            ))
                        logger.info(f"Added new unique unknown record for {unique_key}")
                    else:
                        logger.info(f"Duplicate unknown record for {unique_key}")

            for record in new_unknown_records:
                logger.info(f"New unknown record: {record.group_by:<{20}} {record.group_by_value:<{35}} {record.student_count}")

            # Create a combined dataset in memory
            combined_dataset = list(school_data)  # Convert QuerySet to list

            # Add the new unknown records to the combined dataset
            if new_unknown_records:
                # Look up stratification for each new unknown record
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
                        "topic": "FVDEYLCV",
                        "stratification": stratification,
                        "period": period,
                        "value": int(record.student_count) if record.student_count.isdigit() else 0,
                    }
                else:
                    grouped_data[strat_key]["value"] += int(record.student_count) if record.student_count.isdigit() else 0
                    
            # Prepare transformed data for bulk insertion
            transformed_data = [
                MetopioStateWideLayerTransformation(
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
                MetopioStateWideLayerTransformation.objects.all().delete()  # Clear existing data
                MetopioStateWideLayerTransformation.objects.bulk_create(transformed_data)
            logger.info(f"Successfully transformed {len(transformed_data)} records.")
            return True
        
        except Exception as e:
            logger.error(f"Error during Metopio StateWide Layer Transformation: {e}")
            return False

    def transforms_Metopio_ZipCodeLayer(self):
        try:
            logger.info("Starting Metopio ZipCode Layer Transformation...")

            # Fetch and filter County GEOID entries
            county_geoid_entries = CountyGEOID.objects.filter(layer="Zip code")
            logger.info(f"Filtered County GEOID entries count: {county_geoid_entries.count()}")

            # Create a map to store the Zip Code and its corresponding GEOID from the CountyGEOID entries
            zip_code_geoid_map = {entry.name: entry.geoid for entry in county_geoid_entries}
            #logger.info(f"Zip Code GEOID map: {zip_code_geoid_map}")

            # Fetch and join SchoolData with SchoolAddressFile dynamically
            school_data = (
                SchoolData.objects.filter(
                    # Exclude records with school names in square brackets                   
                    ~Q(school_name__startswith='['),
                    county__in=['Outagamie', 'Winnebago', 'Calumet']
                        # Filter for specified counties
                )
                # .prefetch_related('address_details')  # Fetch related address details in a single query
                 .distinct()  # Ensure unique records
            )
            
            # Check for null school_code values and log them
            null_school_code_count = school_data.filter(school_code__isnull=True).count()
            logger.info(f"Number of records with null school_code: {null_school_code_count}")
            logger.info(f"Filtered school data count: {school_data.count()}")

            # HANDLE UNKNOWNS
            combined_dataset = list(school_data) # Convert QuerySet to list
            group_totals = defaultdict(int)
            all_students_totals = defaultdict(int)
            
            #NORMALIZING AFTER FETCHING THE DATA
            for record in combined_dataset:
                record.school_code=record.school_code.lstrip("0")
                record.district_code=record.district_code.lstrip("0")

            logger.info(f"#1 Normalized the school_code and district_code for {len(combined_dataset)} records")  ##3408
            

            # Compute totals per GROUP_BY and track "All Students" per zip code total
            # We have to do this groupBy total for each school code which is not null

            for record in combined_dataset:
                if record.school_code is None:
                    continue
                key =(record.district_code,record.school_code, record.group_by)
                group_totals[key] += int(record.student_count)
                if record.group_by == "All Students":
                    all_students_totals[record.district_code,record.school_code] += int(record.student_count)


        

            group_by_totals = {}

            # We are assigning this new group_totals dictionary to group_by_totals dictionary  to 
            # hold the objects of the remaining columns which we will need to refer when we are building the 
            # transformed data . Essentially the group_by_totals is a more complex dictionary that uses a combination of the fields
            # as the key to store the corresponding totals from the group totals
            # Purpose of this dictionary is to store the totals of the group_by  for each unique combination of county , district_code, school_code, group_by, group_by_value
            #Structure of this dictionary :  A dictionary with a tuple of (county, district_code, school_code, group_by, group_by_value, zip_code) as the key and the total of the group_by as the value
            for record in combined_dataset:
                key = (record.county, record.district_code, record.school_code, record.group_by, record.group_by_value,record.stratification, record.student_count)
                group_by_totals[key] = group_totals[(record.district_code,record.school_code,record.group_by)]

        
            new_unknown_records = []
            unique_records = set()
            
            # Create a combined dataset in memory
             # Convert QuerySet to list
            
            # After we have built that dictionary then we are now trying to add the unknown entries in the data
            # And we would be adding this entry by creating memory objects rather than directly adding to the database
            # This is because we need to refer to the address details of the original record when we are building the transformed data
            
            for key, total in group_by_totals.items():
                county, district_code, school_code, group_by, group_by_value,stratification,student_count = key

                if total < all_students_totals[(district_code,school_code)]:   #Changed ::Added student_count == 0 in 2/23
                    difference = all_students_totals[(district_code,school_code)] - total
                    
                    unique_key = (county, district_code, school_code, group_by, "Unknown")
                    
                    #If there is already an unknown record for this combination, update the student count
                    if group_by_value == "Unknown":
                            group_by_totals[key] += difference
                            logger.info(f"Updated existing unknown record for {county}, {district_code}, {school_code}, {group_by} with difference {difference}")
                            continue     
                                       
                    # Only append if this combination hasn't been seen before
                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        # Create new "Unknown" record
                        record = next((r for r in combined_dataset if r.district_code == district_code and r.school_code == school_code and r.group_by == group_by), None)
                        if record:
                            # Create new "Unknown" record
                            new_record = SchoolData(
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
                                student_count=str(difference),  
                                percent_of_group=record.percent_of_group or "0",
                                place=record.place or "",
                                stratification=stratification,
                                
                            )
                                # Copy address details from the original record
                            new_unknown_records.append(new_record)
                        else:
                            logger.error(f"Record not found for {district_code}, {school_code}, {group_by}")
                    else:
                        logger.info(f"Duplicate unknown record for {unique_key}")     
            logger.info(f"****New unknown records count: {len(new_unknown_records)}")

            combined_dataset.extend(new_unknown_records)
            logger.info(f"#3 Normalized the school_code and district_code for {len(combined_dataset)} records")  ##3560
            
            #Now in this combined data set list we need to loop through the group_by_map list and 
            # check if the combined data set has a missing group_by record for every school code
            # If it does not have a record then we need to add a new record with the group_by as 
            # the one that is missing from the key of the map below which why is we are making the group_by_map a dictionary
            group_by_map={
                f"{strat.group_by}": strat
                for strat in Stratification.objects.all()
            }
            logger.info(f"Stratification Mapping: {group_by_map}")

            #loop through the combined data set and check for each school code if that record
            #has missing group_by records and if it does then we need to add a new record for that group_by

            #Create a dictionary to group records by school code and district code 
            school_code_groups =defaultdict(list)
            for record in combined_dataset:
                school_code_groups[record.school_code,record.district_code].append(record)   ##Change Added the district code 
      

            #Loop through the grouped records and check for the missing group_by keys
            for (school_code,district_code), records in school_code_groups.items():
                existing_group_by_keys ={record.group_by for record in records}
                missing_group_by_keys = set(group_by_map.keys()) - existing_group_by_keys

                for missing_group_by_key in missing_group_by_keys:
                    reference_record = next((r for r in records if r.group_by == "All Students"), None)
                    # Create a new record for the missing group_by key
                    new_record = SchoolData(
                        school_year=reference_record.school_year,
                        agency_type=reference_record.agency_type or "Unknown",
                        cesa=reference_record.cesa,
                        county=reference_record.county,
                        district_code=reference_record.district_code,
                        school_code=reference_record.school_code,
                        grade_group=reference_record.grade_group or "Unknown",
                        charter_ind=reference_record.charter_ind or "Unknown",
                        district_name=reference_record.district_name or "Unknown",
                        school_name=reference_record.school_name or "Unknown",
                        group_by=missing_group_by_key,
                        group_by_value="Unknown",
                        student_count=str(all_students_totals[reference_record.district_code, reference_record.school_code]),
                        percent_of_group=reference_record.percent_of_group or "0",
                        place=reference_record.place or "",
                        stratification=reference_record.stratification,
                    )
                    combined_dataset.append(new_record)
                    logger.info(f"""Added new record for missing group_by: {missing_group_by_key} 
                    #             for count {all_students_totals[(records[0].district_code,records[0].school_code)]}
                    #             for school code: {school_code}
                    #             for school name: {records[0].school_name}""")    

            
            
            
            
            
            logger.info(f"#3 Normalized the school_code and district_code for {len(combined_dataset)} records")   ##3422


            # Create a dictionary to group records by school code
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
                        "student_count": record.student_count,
                        "percent_of_group": record.percent_of_group,
                        "place": record.place,
                        "stratification": record.stratification.label_name if record.stratification else "Unknown",
                    })

            # Create a DataFrame from the export data
            df = pd.DataFrame(export_data)

            # Export the DataFrame to an Excel file
            df.to_excel("school_code_groups.xlsx", index=False)
            logger.info("School code groups exported to school_code_groups.xlsx")

            


            #REALIGNING STRATIFICATIONS SINCE WE RE ADDED THE UNKNOWNS
            strat_map = {
                f"{strat.group_by}{strat.group_by_value}": strat
                for strat in Stratification.objects.all()
            }
           
            for record in combined_dataset:
                combined_key = record.group_by + record.group_by_value
                record.stratification = strat_map.get(combined_key)   #assigning the stratification for the data
            #logger.info(f"Stratification for {combined_key} is {record.stratification.label_name}")

            logger.info(f"#4 Combined dataset count After Stratification: {len(combined_dataset)}")

           
            #REALIGNING THE ZIP CODE
            #Assign a Zip code to each record in the combined dataset
            # Create a map to store the Zip Code for each (lea_code, school_code) tuple
            # REALIGNING THE ZIP CODE
            # Create a map to store the Zip Code for each (lea_code, school_code) tuple
            zip_Code_Map = {
                (d.lea_code.lstrip("0"), d.school_code.lstrip("0")): d.zip_code
                for d in SchoolAddressFile.objects.all()
            }
            #logger.info(f"Zip Code Mapping: {zip_Code_Map}")
            
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
                    "Stratification": record.stratification.label_name,
                    "student_count": int(record.student_count),
                    "zip_code": record.zip_code
                })

                # logger.info(
                #     f"Record: {cleaned_district_code:<{15}} {cleaned_school_code:<{15}} {record.school_name:<{40}} {record.zip_code:<{15}}"
                # )
                        # Create a DataFrame from the log data
            df = pd.DataFrame(log_data)

            # Export the DataFrame to an Excel file
            df.to_excel("log_data.xlsx", index=False)
            logger.info("Log data exported to log_data.xlsx")

            
            
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
                            "topic": "FVDEYLCV",
                            "stratification": strat_label,
                            "period": period,
                            "value": int(record.student_count) if record.student_count.isdigit() else 0,
                        }
                else:
                    grouped_data[strat_key]["value"] += int(record.student_count) if record.student_count.isdigit() else 0
               
                    

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
                            student_count = int(record.student_count) if str(record.student_count).isdigit() else 0
                            total_raw += student_count
                            #logger.info(f"Adding {student_count} from School {record.school_name}, School Code {record.school_code} , District Code {record.district_code}")
                        except Exception as e:
                            logger.error(f"Error converting student_count for record {record.school_name}: {e}")

            logger.info(f"Raw Total: {total_raw}")

                        
            
            #Identify the missing records
            missing_records =[
                record for record in combined_dataset
                if getattr(record,"geoid",None) == "54915" and  record.student_count not in [data["value"] for data in grouped_data.values()]
            ]
            
            if missing_records:
                logger.warning(f"Missing records: {missing_records}")
            else:
                logger.info("No missing records found")
            
            
            
            
            
            # Prepare transformed data for bulk insertion
            transformed_data = [
                ZipCodeLayerTransformation(
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
                ZipCodeLayerTransformation.objects.all().delete()  # Clear existing data
                ZipCodeLayerTransformation.objects.bulk_create(transformed_data)

            logger.info(f"Successfully transformed {len(transformed_data)} records.")


            return True

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Metopio ZipCode Layer Transformation: {e} at line number {line_number}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def transform_Metopio_CityLayer(self):
        try:
            logger.info("Starting Metopio City Layer Transformation...")
    
            # Fetch and filter County GEOID entries
            county_geoid_entries = CountyGEOID.objects.filter(layer="City or town")
            logger.info(f"Filtered County GEOID entries count: {county_geoid_entries.count()}")
    
            # Create a map to store the City and its corresponding GEOID from the County GEOID entries
            city_geoid_map = {entry.name: entry.geoid for entry in county_geoid_entries}
            #logger.info(f"City GEOID map: {city_geoid_map}")
    
            # Fetch and join SchoolData with SchoolAddressFile dynamically
            school_data = (
                SchoolData.objects.filter(
                    ~Q(school_name__startswith='['),  # Exclude records with county names in square brackets
                    county__in=['Outagamie', 'Winnebago', 'Calumet']  # Filter for specified counties
                )
                #.prefetch_related('address_details')  # Fetch related address details in a single query
                .distinct()  # Ensure unique records
            )
            logger.info(f"Filtered school data count: {school_data.count()}")
    
            # HANDLE UNKNOWN
            combined_dataset = list(school_data)  # Convert QuerySet to list
            group_totals = defaultdict(int)
            all_students_totals = defaultdict(int)
            
            #NORMALIZING AFTER FETCHING THE DATA
            for record in combined_dataset:
                record.school_code=record.school_code.lstrip("0")
                record.district_code=record.district_code.lstrip("0")
    
            # Compute totals per GROUP_BY and track "All Students" total
            # We have to do this groupBy total for each school code which is not null
    
            for record in combined_dataset:
                if record.school_code is None:
                    continue
                key = (record.district_code, record.school_code, record.group_by)
                group_totals[key] += int(record.student_count)
                if record.group_by == "All Students":
                    all_students_totals[record.district_code,record.school_code] += int(record.student_count)
    
            group_by_totals = {}
    
            # We are assigning this new group_totals dictionary to hold the objects of the remaining columns
            for record in school_data:
                key = (record.county, record.district_code, record.school_code, record.group_by, record.group_by_value,record.stratification)
                group_by_totals[key] = group_totals[(record.district_code,record.school_code,record.group_by)]
    
            
            #BUILDING THE UNKNOWN RECORDS
            
            new_unknown_records = []
            unique_records = set()

            for key, total in group_by_totals.items():
                county, district_code, school_code, group_by, group_by_value,stratification = key
                if total < all_students_totals[(district_code,school_code)]:
                    difference = all_students_totals[(district_code,school_code)] - total
                    #logger.info(f"****Difference {difference} for {school_code} {group_by} {group_by_value}= {all_students_totals[(district_code,school_code)]} - {total}")
                    unique_key = (county, district_code, school_code, group_by, "Unknown")

                    # Adjust the key structure to match unique_key
                    if group_by_value == "Unknown":
                            group_by_totals[key] += difference
                            logger.info(f"Updated existing unknown record for {county}, {district_code}, {school_code}, {group_by} with difference {difference}")
                            continue 
                    
                    # Only append if this combination hasn't been seen before
                    if unique_key not in unique_records:
                        unique_records.add(unique_key)
                        # Create new "Unknown" record
                        record = next((r for r in combined_dataset if r.district_code == district_code and r.school_code == school_code and r.group_by == group_by), None)
                        if record:
                            # Create new "Unknown" record
                            new_record = SchoolData(
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
                                student_count=str(difference), 
                                percent_of_group=record.percent_of_group or "0",
                                place=record.place or "",
                                stratification=stratification,
                                
                            )
                                # Copy address details from the original record
                            new_unknown_records.append(new_record)
                        else:
                            logger.error(f"Record not found for {district_code}, {school_code}, {group_by}")
                    else:
                        logger.info(f"Duplicate unknown record for {unique_key}")     
            logger.info(f"****New unknown records count: {len(new_unknown_records)}")

    
                # Create a combined dataset in memory
            combined_dataset.extend(new_unknown_records)  # Convert QuerySet to list
            #Now in this combined data set list we need to loop through the group_by_map list and 
            # check if the combined data set has a missing group_by record for every school code
            # If it does not have a record then we need to add a new record with the group_by as 
            # the one that is missing from the key of the map below which why is we are making the group_by_map a dictionary
            group_by_map={
                f"{strat.group_by}": strat
                for strat in Stratification.objects.all()
            }
            logger.info(f"Stratification Mapping: {group_by_map}")

            #loop through the combined data set and check for each school code if that record
            #has missing group_by records and if it does then we need to add a new record for that group_by

            #Create a dictionary to group records by school code and district code 
            school_code_groups =defaultdict(list)
            for record in combined_dataset:
                school_code_groups[record.school_code,record.district_code].append(record)   ##Change Added the district code 
      

            #Loop through the grouped records and check for the missing group_by keys
            for (school_code,district_code), records in school_code_groups.items():
                existing_group_by_keys ={record.group_by for record in records}
                missing_group_by_keys = set(group_by_map.keys()) - existing_group_by_keys

                for missing_group_by_key in missing_group_by_keys:
                    reference_record = next((r for r in records if r.group_by == "All Students"), None)
                    # Create a new record for the missing group_by key
                    new_record = SchoolData(
                        school_year=reference_record.school_year,
                        agency_type=reference_record.agency_type or "Unknown",
                        cesa=reference_record.cesa,
                        county=reference_record.county,
                        district_code=reference_record.district_code,
                        school_code=reference_record.school_code,
                        grade_group=reference_record.grade_group or "Unknown",
                        charter_ind=reference_record.charter_ind or "Unknown",
                        district_name=reference_record.district_name or "Unknown",
                        school_name=reference_record.school_name or "Unknown",
                        group_by=missing_group_by_key,
                        group_by_value="Unknown",
                        student_count=str(all_students_totals[reference_record.district_code, reference_record.school_code]),
                        percent_of_group=reference_record.percent_of_group or "0",
                        place=reference_record.place or "",
                        stratification=reference_record.stratification,
                    )
                    combined_dataset.append(new_record)
                    logger.info(f"""Added new record for missing group_by: {missing_group_by_key} 
                    #             for count {all_students_totals[(records[0].district_code,records[0].school_code)]}
                    #             for school code: {school_code}
                    #             for school name: {records[0].school_name}""")    

            
            
            
            
            
            logger.info(f"#3 Normalized the school_code and district_code for {len(combined_dataset)} records")   ##3422


            # Create a dictionary to group records by school code
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
                        "student_count": record.student_count,
                        "percent_of_group": record.percent_of_group,
                        "place": record.place,
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
                #logger.info(f"Stratification for {combined_key} is {record.stratification.label_name}")

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
                    "Stratification": record.stratification.label_name,
                    "student_count": int(record.student_count),
                    "city": record.city
                })

                # logger.info(
                #     f"Record: {cleaned_district_code:<{15}} {cleaned_school_code:<{15}} {record.school_name:<{40}} {record.zip_code:<{15}}"
                # )
                        # Create a DataFrame from the log data
            df = pd.DataFrame(log_data)

            # Export the DataFrame to an Excel file
            df.to_excel("log_data_city.xlsx", index=False)
            logger.info("Log data exported to log_data.xlsx")

            # Process records for transformation
            grouped_data = {}
            for record in combined_dataset:
            
                period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}" if "-" in record.school_year else record.school_year
                strat_label = record.stratification.label_name if record.stratification else "Error"

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
                        "topic": "FVDEYLCV",
                        "stratification": strat_label,
                        "period": period,
                        "value": int(record.student_count) if record.student_count.isdigit() else 0,
                    }
                else:
                    grouped_data[strat_key]["value"] += int(record.student_count) if record.student_count.isdigit() else 0



            # Prepare transformed data for bulk insertion
            transformed_data = [
                MetopioCityLayerTransformation(
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
                MetopioCityLayerTransformation.objects.all().delete()  # Clear existing data
                MetopioCityLayerTransformation.objects.bulk_create(transformed_data)
            logger.info(f"Successfully transformed {len(transformed_data)} records.")


            return True
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1][1]
            logger.error(f"Error during Metopio City Layer Transformation: {e} at line number {line_number}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

#######################Removal Count Transformation#######################

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

            #fetch filtered school data
            school_removal_data = []
            school_removal_data = SchoolRemovalData.objects.filter(district_name=district_name_filter)
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

            
            group_by_totals = {}


            for record in school_data:
                key = (record.county, record.group_by, record.group_by_value)
                group_by_totals[key] = group_totals[record.group_by]


            new_unknown_records = []
            unique_records = set()

            for (record.county, record.group_by, record.group_by_value), total in group_by_totals.items():
                if record.group_by == "All Students":
                    continue
                if total < all_students_totals:
                    difference = all_students_totals - total
                    unique_key = ("Unknown", difference)

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
                        logger.info(f"Added new unique unknown record for {unique_key}")
                    else:
                        logger.info(f"Duplicate unknown record for {unique_key}")

            
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
                group_by_totals[key] = group_totals[record.group_by]


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
                    "Stratification": record.stratification.label_name,
                    "removal_count": record.removal_count,
                    

                })

            # Create a DataFrame from the log data
            df = pd.DataFrame(log_data)
            df.to_excel("before_grouping_county.xlsx", index=False)
            
            # STEP 3: Group Data
            grouped_data = {}

            for record in combined_dataset:
                period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}" if "-" in record.school_year else record.school_year
                strat_label = record.stratification.label_name 
                group_by, group_by_value = record.group_by, record.group_by_value
                geoid = county_geoid_map.get(record.county).geoid if county_geoid_map.get(record.county) else "Error"
                county=record.county
             
                
                strat_key = (county,strat_label)

                # Add to grouped data
                if strat_key not in grouped_data:
                    grouped_data[strat_key] = {
                        "layer": "County",
                        "geoid": geoid,
                        "topic": "FDEWVAR",
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
                county__in=["Outagamie", "Winnebago", "Calumet"]
            ).exclude(school_name="[Districtwide]").distinct()

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
                key = (record.county, record.district_code, record.school_code, record.group_by, record.group_by_value,record.stratification, record.removal_count)
                group_by_totals[key] = group_totals[(record.district_code,record.school_code,record.group_by)]

            new_unknown_records = []
            unique_records = set()

            for key,total in group_by_totals.items():
                county, district_code, school_code, group_by, group_by_value, stratification, student_count = key
                if total <all_students_totals[(district_code, school_code)]:
                    difference = all_students_totals[(district_code, school_code)] - total
                    unique_key = (county, district_code, school_code, group_by, "Unknown")

                    if key[4] =="Unknown":
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


            combined_dataset.extend(new_unknown_records)  # Convert QuerySet to list
            logger.info(f"#3 Normalized the school_code and district_code for {len(combined_dataset)} records")  ##3560
            
            group_by_map= {
                f"{strat.group_by}{strat.group_by_value}": strat
                for strat in Stratification.objects.all()
            }
            logger.info(f"Stratification Mapping: {group_by_map}")

            
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
                    "Stratification": record.stratification.label_name,
                    "removal count": int(record.removal_count),
                    "zip_code": record.zip_code
                })

                # logger.info(
                #     f"Record: {cleaned_district_code:<{15}} {cleaned_school_code:<{15}} {record.school_name:<{40}} {record.zip_code:<{15}}"
                # )
                        # Create a DataFrame from the log data
            df = pd.DataFrame(log_data)

            # Export the DataFrame to an Excel file
            df.to_excel("log_data.xlsx", index=False)
            logger.info("Log data exported to log_data.xlsx")

            
            
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
                            "topic": "FDEWVAR",
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
                county__in=["Outagamie", "Winnebago", "Calumet"]
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
                key = (record.county, record.district_code, record.school_code, record.group_by, record.group_by_value,record.stratification, record.removal_count)
                group_by_totals[key] = group_totals[(record.district_code,record.school_code,record.group_by)]

            new_unknown_records = []
            unique_records = set()

            for key,total in group_by_totals.items():
                county, district_code, school_code, group_by, group_by_value, stratification, student_count = key
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


            combined_dataset.extend(new_unknown_records)  # Convert QuerySet to list
            logger.info(f"#3 Normalized the school_code and district_code for {len(combined_dataset)} records")  ##3560
            
            group_by_map= {
                f"{strat.group_by}{strat.group_by_value}": strat
                for strat in Stratification.objects.all()
            }
            logger.info(f"Stratification Mapping: {group_by_map}")

            
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
                #logger.info(f"Stratification for {combined_key} is {record.stratification.label_name}")

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
                    "Stratification": record.stratification,
                    "removal_count": int(record.removal_count),
                    "city": record.city
                })

                # logger.info(
                #     f"Record: {cleaned_district_code:<{15}} {cleaned_school_code:<{15}} {record.school_name:<{40}} {record.zip_code:<{15}}"
                # )
                        # Create a DataFrame from the log data
            df = pd.DataFrame(log_data)

            # Export the DataFrame to an Excel file
            df.to_excel("log_data_city.xlsx", index=False)
            logger.info("Log data exported to log_data.xlsx")

            # Process records for transformation
            grouped_data = {}
            for record in combined_dataset:
            
                period = f"{record.school_year.split('-')[0]}-20{record.school_year.split('-')[1]}" if "-" in record.school_year else record.school_year
                strat_label = record.stratification.label_name if record.stratification else "Error"

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
                        "topic": "FDEWVAR",
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
