from django.shortcuts import render, redirect
from django.db.utils import OperationalError
import time
import os
import csv
from django.urls import reverse  # For generating URLs
from .models import (
    SchoolData,
    TransformedSchoolData,
    Stratification,
    MetopioTriCountyLayerTransformation,
    CountyLayerTransformation,
    MetopioStateWideLayerTransformation,
    ZipCodeLayerTransformation,
    MetopioCityLayerTransformation,  # Add this line
)
from .forms import UploadFileForm
from .models import ZipCodeLayerTransformation, SchoolRemovalData, MetopioStateWideRemovalDataTransformation, MetopioTriCountyRemovalDataTransformation, CountyLayerRemovalData, ZipCodeLayerRemovalData, MetopioCityRemovalData, CombinedRemovalData
from .models import SchoolAddressFile
from .models import CountyGEOID
from django.http import HttpResponse
import logging
from django.conf import settings

logger = logging.getLogger(__name__)
import pandas as pd
from django.db import transaction, connection
from django.core.paginator import Paginator
from django.contrib import messages  # For adding feedback messages
from .transformers import DataTransformer
from collections import defaultdict

def data_processor_home(request):
    if request.method == "POST":
        # Check which transformation type was selected
        transformation_type = request.POST.get(
            "transformation_type", "Statewide V01"
        )  # Default to 'Statewide'
        # Instantiate the DataTransformer and apply the transformation
        transformer = DataTransformer(request)
        success = transformer.apply_transformation(transformation_type)

        # If transformation was successful, redirect to success page
        if success:
            return redirect(f"/data_processor/success/?type={transformation_type}")

        # If transformation failed, stay on the same page to display the error
        return redirect("/data_processor/")  # Or render the page with the error message

    return render(request, "index.html")


## Create a view and template to display a success message after the transformation
##  This is to show the user that the transformation was successful and provide a link to view the transformed data

def transformation_success(request):
    # Example details we can customize this based on the needs
    details = "Transformation Completed Successfully. Check the Updated records in the database"

    # Determine the transformation type from the query parameter (default to 'Statewide')
    transformation_type = request.GET.get(
        "type", "Statewide V01"
    )  # Default to Statewide if not specified
    # Instantiate DataTransformer properly with the request
    # Transformer = DataTransformer(request)
    # Retrieve the appropriate transformed data based on the transformation type
    # Run the transformation explicitly
    if transformation_type == "Statewide V01":
        transformer = DataTransformer(request)
        transformer.apply_transformation("Statewide V01")
        data_list = TransformedSchoolData.objects.filter(place="WI")
        return redirect(
            reverse("statewide_view")
        )  # Replace 'statewide_view' with the actual name of your URL
    elif transformation_type == "Tri-County":
        transformer = DataTransformer(request)
        transformer.apply_tri_county_layer_transformation()
        data_list = MetopioTriCountyLayerTransformation.objects.all()
    elif transformation_type == "County-Layer":
        transformer = DataTransformer(request)  # Apply County Layer transformation
        transformer.apply_county_layer_transformation()
        data_list = CountyLayerTransformation.objects.all()
    elif transformation_type == "Metopio Statewide":
        transformer = DataTransformer(request)
        transformer.transform_Metopio_StateWideLayer()
        data_list = MetopioStateWideLayerTransformation.objects.all()
    elif transformation_type == "Zipcode":
        transformer = DataTransformer(request)
        transformer.transforms_Metopio_ZipCodeLayer()
        data_list = ZipCodeLayerTransformation.objects.all()
    elif transformation_type == "City-Town":
        transformer = DataTransformer(request)
        transformer.transform_Metopio_CityLayer()
        data_list = MetopioCityLayerTransformation.objects.all()
    elif transformation_type == "Statewide-Removal":
        transformer = DataTransformer(request)
        transformer.transform_Statewide_Removal()
        data_list = MetopioStateWideRemovalDataTransformation.objects.all()
    elif transformation_type == "Tricounty-Removal":
        transformer = DataTransformer(request)
        transformer.transform_Tri_County_Removal()
        data_list = MetopioTriCountyRemovalDataTransformation.objects.all()
    elif transformation_type == "County-Removal":
        transformer = DataTransformer(request)
        transformer.transform_County_Layer_Removal()
        data_list = CountyLayerRemovalData.objects.all()
    elif transformation_type == "Zipcode-Removal":
        transformer = DataTransformer(request)
        transformer.transform_Zipcode_Layer_Removal()
        data_list = ZipCodeLayerRemovalData.objects.all()
    elif transformation_type == "City-Removal":
        transformer = DataTransformer(request)
        transformer.transform_City_Layer_Removal()
        data_list = MetopioCityRemovalData.objects.all()
    elif transformation_type == "combined":
        transformer = DataTransformer(request) # Assuming this function generates the combined CSV data
        transformer.transform_combined_removal()
        data_list = CombinedRemovalData.objects.all()
    else:
        # Handle unknown transformation types
        details = "Unknown transformation type. Please check your request."
        data_list = []

    

    # Paginate the results
    paginator = Paginator(data_list, 20)  # Show 20 records per page
    page_number = request.GET.get(
        "page"
    )  # Get the page number from the query parameters
    data = paginator.get_page(page_number)  # Get the page object

    # Return the rendered success page with the appropriate data
    return render(
        request,
        "__data_processor__/success.html",
        {
            "message": details,
            "data": data,  # This is the paginated data
            "transformation_type": transformation_type,  # The transformation type (Statewide or Tri-County)
        },
    )


# Key features of the Function Handle_uploaded_file
# Handles two file upload : Saves the uploaded files to a consistent directory in the project
# Processes two files : Supports the processing of a main data file and an optional stratification file
# Uses Bulk Operations ; Employs bulk insertion to to efficiently save data
# Handles the error gracefully : Implements the retry mechanism to handle database locking errors
# Links the data in the SchoolData and the Stratification using the foreign key
#Addition of the Stratification file upload and processing
# handling to load the main file and the stratification file

def handle_uploaded_file(f, stratifications_file=None):
    """ Handle file upload and process main and stratification files """
    try:
        # Save uploaded files
        upload_dir = os.path.join(settings.BASE_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f.name)

        # Check if the file has already been processed
        file_already_exists = os.path.exists(file_path)
        if file_already_exists:
            logger.info(f"File {file_path} has already been processed. Skipping.")
        else:
            with open(file_path, "wb+") as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
            logger.info(f"File uploaded successfully to {file_path}")

        # Process stratification file if provided
        strat_map = {}
        if stratifications_file:
            strat_file_path = os.path.join(upload_dir, stratifications_file.name)
            with open(strat_file_path, "wb+") as destination:
                for chunk in stratifications_file.chunks():
                    destination.write(chunk)
            logger.info(f"Stratification file uploaded successfully to {strat_file_path}")

            # Load stratifications into the database
            try:
                with open(strat_file_path, "r") as strat_file:
                    strat_reader = csv.DictReader(strat_file)
                    Stratification.objects.all().delete()
                    for row in strat_reader:
                        group_by = "Grade Level" if row["GROUP_BY"] == "Grade" else row["GROUP_BY"]
                        group_by_value = row["GROUP_BY_VALUE"]
                        label_name = row["Stratification"]
                        
                        # Create a Stratification object and save it to the database
                        strat, created = Stratification.objects.get_or_create(
                            group_by=group_by,
                            group_by_value=group_by_value,
                            label_name=label_name,
                        )
                        # Create a mapping of group_by and group_by_value to the Stratification object
                        strat_map[f"{group_by}{group_by_value}"] = strat
            except Exception as e:
                logger.error(f"Error processing stratifications file: {e}")
                raise

        # Process the main file
        retries = 5
        while retries > 0:
            try:
                with open(file_path, "r") as file:
                    reader = csv.DictReader(file)
                    SchoolData.objects.all().delete()
                    data = []

                    strat_map = {
                        f"{strat.group_by}{strat.group_by_value}": strat
                        for strat in Stratification.objects.all()
                    }

                    for row in reader:
                        if row["STUDENT_COUNT"] == "*" or row["STUDENT_COUNT"] == "0":
                            continue
                        group_by = "Grade Level" if row["GROUP_BY"] == "Grade" else row["GROUP_BY"]
                        combined_key = group_by + row["GROUP_BY_VALUE"]
                        stratification = strat_map.get(combined_key)
                        unknown_key = (group_by, "Unknown")
                        
                        data.append(
                            SchoolData(
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
                                group_by=group_by,
                                group_by_value=row["GROUP_BY_VALUE"],
                                student_count=row["STUDENT_COUNT"],
                                percent_of_group=row["PERCENT_OF_GROUP"],
                                stratification=stratification,
                            )
                        )

                            
                    
                    # Insert new data into the database
                    SchoolData.objects.bulk_create(data)
                    logger.info(f"{len(data)} SCHOOL DATA records inserted into the database")
                    break
            except OperationalError as e:
                if "database is locked" in str(e):
                    retries -= 1
                    logger.warning(f"Database is locked, retrying... ({5 - retries} retries left)")
                    time.sleep(1)
                else:
                    logger.error(f"Error processing file: {e}")
                    raise
    except Exception as e:
        logger.error(f"Error handling file upload: {e}")
        raise

# data_processor/views.py
def upload_file(request):
    message = ""             # Initialize the message variable
    form = UploadFileForm()  # Initialize the form

    if request.method == "POST":
        # Handle file upload
        file = request.FILES.get("file")
        stratifications_file = request.FILES.get("stratifications_file")  
        county_geoid_file = request.FILES.get("county_geoid_file") #New County GEOID file
        school_address_file = request.FILES.get("school_address_file")  #New School Address file
        school_removal_file = request.FILES.get("school_removal_file")  #New School Removal file
        
        #Get the stratification file if provided

        if file:  # Check if a file is uploaded
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                handle_uploaded_file(
                    file, 
                    stratifications_file=stratifications_file,
                    )   # Process the main file and the stratification uploaded file
            
        #Process the COunty GEOID file if provided
        if county_geoid_file:
            load_county_geoid_file(county_geoid_file)
        if school_address_file:
            load_school_address_file(school_address_file)
        if school_removal_file:
            load_school_removal_data(school_removal_file)
            return redirect(
                f"{reverse('upload')}?message=File uploaded successfully. Now you can run the transformation."
            )
        # After this step in the rendered page we have the transformation forms from where we can get the tranformation type
        # since we called the handle_uploaded_file function to process the file and save it to the database
        # we are already prepared to handle the transformation actions after the page as above has been rendered
        # Handle transformation actions
        transformation_type = request.POST.get("transformation_type")
        if transformation_type:
            transformer = DataTransformer(request)  # Create an instance of the DataTransformer class
            if transformation_type == "Tri-County":
                success = (transformer.apply_tri_county_layer_transformation())  # Apply the Tri-County Layer transformation
            elif transformation_type == "County-Layer":
                success = transformer.apply_county_layer_transformation()        # Apply County Layer transformation
            elif transformation_type == "Metopio Statewide":
                success = transformer.transform_Metopio_StateWideLayer()         # Apply Metopio Statewide transformation
            elif transformation_type == "Zipcode":
                success = transformer.transforms_Metopio_ZipCodeLayer()          # Apply Metopio Zipcode transformation 
            elif transformation_type == "City-Town":
                success = transformer.transform_Metopio_CityLayer()              # Apply Metopio City-Town transformation
            elif transformation_type =="Statewide-Removal":
                success = transformer.transform_Statewide_Removal()             # Apply Statewide Removal transformation
            elif transformation_type == "Tricounty-Removal":
                success = transformer.transform_Tri_County_Removal()
            elif transformation_type == "County-Removal":
                success = transformer.transform_County_Layer_Removal()
            elif transformation_type =="Zipcode-Removal":
                success = transformer.transform_Zipcode_Layer_Removal()
            elif transformation_type == "City-Removal":
                success = transformer.transform_City_Layer_Removal()
            elif transformation_type == "combined":
                success = transformer.transform_combined_removal()  # Generate the combined CSV file
            else:
                success = transformer.apply_transformation(transformation_type ) # Apply the transformation

            # If transformation was successful, redirect to the success page
            if success:
                # Redirect to the transformation success page with the transformation type
                return redirect(
                    f"{reverse('transformation_success')}?type={transformation_type}"
                )
            else:
                # If transformation failed, display an error message
                message = "Transformation failed. Please try again."

    else:
        form = UploadFileForm()  # Initialize the form if it's a GET request

    # Get any message passed via query parameters
    message = request.GET.get("message", message)  # Show the message if it exists
    details = "Upload your file and select the transformation type."
    return render(
        request,
        "__data_processor__/upload.html",
        {"form": form, "message": message, "details": details},
    )
    
# handle the county geoid file upload

def load_county_geoid_file(file):
    # Save the file to the uploads directory
    upload_dir = os.path.join(settings.BASE_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.name)

    with open(file_path, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    logger.info(f"County GEOID file uploaded successfully to {file_path}")

    try:
        with open(file_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            CountyGEOID.objects.all().delete()  # Clear existing records
            # Validate required columns
            required_columns = {"Layer", "Name", "GEOID"}
            if not required_columns.issubset(reader.fieldnames):
                raise ValueError(f"Missing required columns: {required_columns - set(reader.fieldnames)}")

           

            # Filter rows where Layer = 'County' and prepare data
            data = [
                CountyGEOID(
                    layer=row["Layer"],  # Use the "Layer" field
                    name=row["Name"],    # Use the "Name" field
                    geoid=row["GEOID"]   # Use the "GEOID" field
                )
                for row in reader 
            ]

            # Bulk insert filtered data
            CountyGEOID.objects.bulk_create(data)
            logger.info(f"{len(data)} County GEOID records inserted into the database")

    except Exception as e:
        logger.error(f"Error processing County GEOID file: {e}")
        raise

# handle the school AddressFile upload
def load_school_address_file(file):
    # Save the file to the uploads directory
    upload_dir = os.path.join(settings.BASE_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.name)

    with open(file_path, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    logger.info(f"School Address file uploaded successfully to {file_path}")

    try:
        with open(file_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            SchoolAddressFile.objects.all().delete()  # Clear existing records
            # Validate required columns
            required_columns = {
                "LEA Code", "District Name", "School Code", "School Name",
                "Organization Type", "School Type", "Low Grade", "High Grade",
                "Address", "City", "State", "Zip", "CESA", "Locale",
                "County", "Current Status", "Categories And Programs",
                "Virtual School", "IB Program", "Phone Number",
                "Fax Number", "Charter Status", "Website Url"
            }
            if not required_columns.issubset(reader.fieldnames):
                raise ValueError(f"Missing required columns: {required_columns - set(reader.fieldnames)}")
            
            with transaction.atomic():
                

                # Prepare data for bulk insertion
                data = [
                    SchoolAddressFile(
                        lea_code=row["LEA Code"],
                        district_name=row["District Name"],
                        school_code=row["School Code"],
                        school_name=row["School Name"],
                        organization_type=row["Organization Type"],
                        school_type=row["School Type"],
                        low_grade=row["Low Grade"],
                        high_grade=row["High Grade"],
                        address=row["Address"],
                        city=row["City"],
                        state=row["State"],
                        zip_code=row["Zip"],
                        cesa=row["CESA"],
                        locale=row["Locale"],
                        county=row["County"],
                        current_status=row["Current Status"],
                        categories_and_programs=row.get("Categories And Programs", ""),
                        virtual_school=row.get("Virtual School", ""),
                        ib_program=row.get("IB Program", ""),
                        phone_number=row["Phone Number"],
                        fax_number=row.get("Fax Number", ""),
                        charter_status=row["Charter Status"].lower() == "true",
                        website_url=row.get("Website Url", ""),
                    )
                    for row in reader
                ]

                # Bulk insert data
                SchoolAddressFile.objects.bulk_create(data)
            logger.info(f"{len(data)} School Address records inserted into the database")

    except Exception as e:
        logger.error(f"Error processing School Address file: {e}")
        raise

#handle the school removal data
def load_school_removal_data(file):
    # Save the file to the uploads directory
    upload_dir = os.path.join(settings.BASE_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.name)

    with open(file_path, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    logger.info(f"School Removal file uploaded successfully to {file_path}")

    try:
        with open(file_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            SchoolRemovalData.objects.all().delete()  # Clear existing records
            data = []

            strat_map = {
                f"{strat.group_by}{strat.group_by_value}": strat
                for strat in Stratification.objects.all()
            }
            # Validate required columns
            for row in reader:
                if row["REMOVAL_COUNT"] == "*" or row["REMOVAL_COUNT"] == "0":
                    continue
                group_by = "Grade Level" if row["GROUP_BY"] == "Grade" else row["GROUP_BY"]
                #----IGNORE rows with GROUP_BY ="Migrant Status"------
                if group_by=="Migrant Status":
                    continue
                combined_key = group_by + row["GROUP_BY_VALUE"]
                stratification = strat_map.get(combined_key)
                unknown_key = (group_by, "Unknown")
                data.append(
                    SchoolRemovalData(
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
                        group_by=group_by,
                        group_by_value=row["GROUP_BY_VALUE"],
                        removal_type_description = row["REMOVAL_TYPE_DESCRIPTION"],
                        tfs_enrollment_count=row["TFS_ENROLLMENT_COUNT"],
                        removal_count=row["REMOVAL_COUNT"],
                        stratification=stratification,
                    )
                )

            # Bulk insert data
            SchoolRemovalData.objects.bulk_create(data)
            logger.info(f"{len(data)} School Removal records inserted into the database")
            
    except Exception as e:
        logger.error(f"Error processing School Removal file: {e}")
        raise
def statewide_view(request):
    transformation_type = request.GET.get(
        "type"
    )  # Default to 'Statewide' if not specified
    print(f"Query Parameters: {request.GET}")  # Log query parameters

    """ View to display the statewide data """
    # Simply fetching the transformed data from the data base
    data_list = TransformedSchoolData.objects.filter(
        place="WI"
    )  # Assuming the place is WI
    paginator = Paginator(data_list, 20)  # Show 30 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)
    return render(
        request,
        "__data_processor__/statewide.html",
        {
            "data": data,
            "transformation_type": transformation_type,  # The transformation type (Statewide or Tri-County)
        },
    )

def tri_county_view(request):
    transformation_type = request.GET.get(
        "type", "Tri-County"
    )  # Default to the TriCountry Layer if not specified
    print(f"Query Parameters: {request.GET}")  # Log query parameters
    # Fetch the data from the Metopio Data Transformation model
    DataTransformer.apply_tri_county_layer_transformation(request)
    data_list = MetopioTriCountyLayerTransformation.objects.all()
    """ View to display the Tri-County data """

    # Pagiante the Results
    paginator = Paginator(data_list, 20)  # Show 30 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    # pass the data to the template file
    return render(
        request,
        "__data_processor__/tricounty.html",
        {"data": data, "transformation_type": transformation_type},
    )

#COUNTY LAYER VIEW

# views.py

def county_layer_view(request):
    # Get the transformation type from the query parameters
    transformation_type = request.GET.get(
        "type", "County-Layer"
    )  # Default to County Layer if not specified
    print(f"Query Parameters: {request.GET}")  # Log query parameters

    # Apply the County Layer Transformation
    DataTransformer(request).apply_county_layer_transformation()

    # Fetch the transformed data from the CountyLayerTransformation model
    data_list = CountyLayerTransformation.objects.all()

    # Paginate the Results
    paginator = Paginator(data_list, 20)  # Show 20 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    # Pass the data to the template file
    return render(
        request,
        "__data_processor__/county_layer.html",
        {"data": data, "transformation_type": transformation_type},
    )

#METOPIO STATEWIDE VIEW
def metopio_statewide_view(request):
    # Get the transformation type from the query parameters
    transformation_type = request.GET.get(
        "type", "Statewide"
    )  # Default to 'Statewide' if not specified
    print(f"Query Parameters: {request.GET}")  # Log query parameters

    # Apply the Metopio Statewide Transformation
    DataTransformer(request).transform_Metopio_StateWideLayer()

    # Fetch the transformed data from the MetopioStateWideLayerTransformation model
    data_list = MetopioStateWideLayerTransformation.objects.all()

    # Paginate the Results
    paginator = Paginator(data_list, 20)  # Show 20 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    # Pass the data to the template file
    return render(
        request,
        "__data_processor__/metopio_statewide.html",
        {"data": data, "transformation_type": transformation_type},
    )

#METOPIO ZIPCODE VIEW
def metopio_zipcode_view(request):
    # Get the transformation type from the query parameters
    transformation_type = request.GET.get(
        "type", "Zipcode"
    )  # Default to 'Zipcode' if not specified
    print(f"Query Parameters: {request.GET}")  # Log query parameters

    # Apply the Metopio Zipcode Transformation
    DataTransformer(request).transforms_Metopio_ZipCodeLayer()

    # Fetch the transformed data from the MetopioZipCodeLayerTransformation model
    data_list = ZipCodeLayerTransformation.objects.all()

    # Paginate the Results
    paginator = Paginator(data_list, 20)  # Show 20 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    # Pass the data to the template file
    return render(
        request,
        "__data_processor__/metopio_zipcode.html",
        {"data": data, "transformation_type": transformation_type},
    )

#City or Town View
def city_layer_removal_view(request):
    transformation_type = request.GET.get(
        "type", "City-Removal"
    )  # Default to 'City-Removal' if not specified
    print(f"Query Parameters: {request.GET}")  # Log query parameters

    DataTransformer(request).transform_City_Layer_Removal()

    data_list = MetopioCityRemovalData.objects.all()

    # Paginate the Results
    paginator = Paginator(data_list, 20)  # Show 20 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    return render(
        request,
        "__data_processor__/city_layer_removal.html",
        {"data": data, "transformation_type": transformation_type},
    )
def city_town_view(request):
    transformation_type = request.GET.get(
        "type", "City-Town"
    )  # Default to 'City-Town' if not specified
    print(f"Query Parameters: {request.GET}")  # Log query parameters
    # Fetch the data from the Metopio Data Transformation model
    DataTransformer.transform_Metopio_CityLayer(request)
    data_list = MetopioCityLayerTransformation.objects.all()
    """ View to display the City-Town data """

    # Pagiante the Results
    paginator = Paginator(data_list, 20)  # Show 30 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    # pass the data to the template file
    return render(
        request,
        "__data_processor__/city_town.html",
        {"data": data, "transformation_type": transformation_type},
    )
#OUTPUT DOWNLOADS
##EXCEL HANDLE ##

#Removal views
def statewide_removal(request):
    transformation_type = request.GET.get(
        "type", "Statewide-Removal"
    )
    print(f"Query Parameters: {request.GET}")  # Log query parameters

    DataTransformer(request).transform_Statewide_Removal()

    data_list  = MetopioStateWideRemovalDataTransformation.objects.all()

    #Paginate the results
    paginator = Paginator(data_list, 20)  # Show 20 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    return render(
        request,
        "__data_processor__/statewide_removal.html",
        {"data": data, "transformation_type": transformation_type},
    )

#Tri County REMOVAL View
def tri_county_removal_view(request):
    transformation_type = request.GET.get(
        "type", "Tri-County"
    )
    print(f"Query Parameters: {request.GET}")  # Log query parameters

    DataTransformer(request).transform_Tri_County_Removal()

    data_list  = MetopioTriCountyRemovalDataTransformation.objects.all()

    #Paginate the results
    paginator = Paginator(data_list, 20)  # Show 20 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    return render(
        request,
        "__data_processor__/tricounty_removal.html",
        {"data": data, "transformation_type": transformation_type},
    )
#County Layer REMOVAL View
def county_layer_removal_view(request):
    transformation_type = request.GET.get(
        "type", "County-Removal"
    )
    print(f"Query Parameters: {request.GET}")  # Log query parameters

    DataTransformer(request).transform_County_Layer_Removal()

    data_list  = CountyLayerRemovalData.objects.all()

    #Paginate the results
    paginator = Paginator(data_list, 20)  # Show 20 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    return render(
        request,
        "__data_processor__/county_layer_removal.html",
        {"data": data, "transformation_type": transformation_type},
    )
    
#Zip Code Layer REMOVAL View
def zipcode_layer_removal_view(request):
    transformation_type = request.GET.get(
        "type", "Zipcode-Removal"
    )
    print(f"Query Parameters: {request.GET}")  # Log query parameters

    DataTransformer(request).transform_Zipcode_Layer_Removal()

    data_list  = ZipCodeLayerRemovalData.objects.all()

    #Paginate the results
    paginator = Paginator(data_list, 20)  # Show 20 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    return render(
        request,
        "__data_processor__/zipcode_layer_removal.html",
        {"data": data, "transformation_type": transformation_type},
    )

#Combined View
def combined_removal_view(request):
    transformation_type = request.GET.get(
        "type", "combined"
    )  # Default to 'Combined' if not specified
    print(f"Query Parameters: {request.GET}")  # Log query parameters

    DataTransformer(request).transform_combined_removal()
    data_list = CombinedRemovalData.objects.all()

  

    # Paginate the results
    paginator = Paginator(data_list, 20)  # Show 20 records per page
    page_number = request.GET.get("page")
    data = paginator.get_page(page_number)

    return render(
        request,
        "__data_processor__/combined_removal.html",
        {"data": data, "transformation_type": transformation_type},
    )

#City Town REMOVAL View

def generate_transformed_excel(transformation_type):
    # Fetch the transformed data based on the transformation type
    if transformation_type == "Tri-County":
        data = MetopioTriCountyLayerTransformation.objects.all()
    else:
        data = TransformedSchoolData.objects.filter(
            place="WI"
        )  # Default to Statewide if not Tri-County

    # Convert the QuerySet to a list of dictionaries
    data_list = list(data.values())

    # Create a Pandas DataFrame
    df = pd.DataFrame(data_list)

    # Generate the Excel file name
    excel_file = f"transformed_{transformation_type.lower()}_data.xlsx"

    # Use the context manager to handle the saving of the Excel file
    with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
        # Convert the DataFrame to an Excel object
        df.to_excel(writer, sheet_name="Transformed Data", index=False)

    # The file is automatically saved and closed when the context manager exits
    return excel_file

def download_excel(request):
    # Get the transformation type from the URL query parameter
    transformation_type = request.GET.get(
        "type", "Statewide"
    )  # Default to 'Statewide' if not specified

    excel_file = generate_transformed_excel(transformation_type)

    # Serve the file as a download
    with open(excel_file, "rb") as f:
        response = HttpResponse(
            f.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename={excel_file}"
        return response

## CSV HANDLE##

def generate_transformed_csv(transformation_type):

    # Fetch the transformed data based on the transformation type
    # This is where you will be having various trnasformation types
    if transformation_type == "Tri-County":
        data = MetopioTriCountyLayerTransformation.objects.all()
    elif transformation_type == "County-Layer":
        data = CountyLayerTransformation.objects.all()
    elif transformation_type == "Metopio Statewide":
        data = MetopioStateWideLayerTransformation.objects.all()
    elif transformation_type == "Zipcode":
        data = ZipCodeLayerTransformation.objects.all()
    elif transformation_type == "City-Town":
        data = MetopioCityLayerTransformation.objects.all()
    elif transformation_type == "Statewide-Removal":
        data = MetopioStateWideRemovalDataTransformation.objects.all()
    elif transformation_type == "Tricounty-Removal":
        data = MetopioTriCountyRemovalDataTransformation.objects.all()
    elif transformation_type == "County-Removal":
        data = CountyLayerRemovalData.objects.all()
    elif transformation_type == "Zipcode-Removal":
        data = ZipCodeLayerRemovalData.objects.all()
    elif transformation_type =="City-Removal":
        data= MetopioCityRemovalData.objects.all()
    elif transformation_type == "combined":
        data = CombinedRemovalData.objects.all()
    else:
        data = TransformedSchoolData.objects.filter(
            place="WI"
        )  # Default to Statewide if not Tri-County

    # Convert the QuerySet to a list of dictionaries and exclude the id field
    data_list = [
        {key.lower(): value for key, value in row.items() if key != "id"}
        for row in data.values()
    ]

    # Get the field names (keys) from the first item, converted to uppercase and now lower case
    fieldnames = data_list[0].keys() if data_list else []

    # Generate CSV file
    csv_file = f"transformed_{transformation_type.lower()}_data.csv"
    with open(csv_file, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_list)

    return csv_file

def generate_combined_csv():
    """ Generate a single CSV file containing data from all transformation types """
    # Define all transformation types and their corresponding models
    transformation_types = {
        
        "Statewide-Removal": MetopioStateWideRemovalDataTransformation,
        "Tricounty-Removal": MetopioTriCountyRemovalDataTransformation,
        "County-Removal": CountyLayerRemovalData,
        "Zipcode-Removal": ZipCodeLayerRemovalData,
        "City-Removal": MetopioCityRemovalData,
        
    }

    # Initialize an empty list to hold all data
    combined_data = []

    # Iterate through each transformation type and fetch its data
    for transformation_type, model in transformation_types.items():
       
        data = model.objects.all()

        # Convert the QuerySet to a list of dictionaries and add a "type" field
        data_list = [
            {**{key.lower(): value for key, value in row.items() if key != "id"}, "type": transformation_type}
            for row in data.values()
        ]

        # Append the data to the combined list
        combined_data.extend(data_list)

    # Get the field names (keys) from the first item, including the "type" field
    fieldnames = combined_data[0].keys() if combined_data else []

    # Generate the combined CSV file
    csv_file = "combined_transformed_data.csv"
    with open(csv_file, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined_data)

    return csv_file

def download_csv(request):
    # Get the transformation type from the URL query parameter
    transformation_type = request.GET.get(
        "type", "Statewide"
    )  # Default to 'Statewide' if not specified

    # Generate the transformed CSV file
  
    csv_file = generate_transformed_csv(transformation_type)
    # Extract the period from the CSV file
    period = "unknown"  # Default value in case period is not found
    try:
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            first_row = next(reader, None)  # Get the first row
            if first_row and "period" in first_row:
                period = first_row["period"].replace("-", "_")  # Replace invalid characters for filenames
    except Exception as e:
        logger.error(f"Error extracting period from CSV file: {e}")

    # Construct the new file name
    new_file_name = f"transformed_{transformation_type.lower()}_{period}.csv"

    # Serve the file as a download
    with open(csv_file, "rb") as f:
        response = HttpResponse(f.read(), content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={new_file_name}"
        return response