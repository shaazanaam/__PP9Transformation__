# Project Structure Documentation

## Overview
This document provides a comprehensive overview of the Wisconsin School Data Processor project structure, explaining the purpose of each directory and key files.

## Root Directory Structure

```
__PP9Transformation__/
│
├── docs/                          # Documentation files (this folder)
│   ├── PROJECT_STRUCTURE.md      # This file - project organization
│   ├── ROADMAP.md                # Development roadmap and future plans
│   ├── USER_GUIDE.md             # End-user documentation
│   └── API.md                    # Technical API documentation
│
├── __data_processor__/           # Main Django app for data processing
│   ├── migrations/               # Database migration files
│   ├── static/                   # Static files (CSS, JS, images)
│   │   └── css/                  # Stylesheets
│   ├── templates/                # HTML templates
│   │   └── __data_processor__/  # App-specific templates
│   ├── __init__.py              # Python package marker
│   ├── admin.py                 # Django admin configurations
│   ├── apps.py                  # App configuration
│   ├── forms.py                 # Form definitions
│   ├── models.py                # Database models (12+ models)
│   ├── transformers.py          # Core transformation logic
│   ├── urls.py                  # URL routing for the app
│   ├── views.py                 # View functions (30+ views)
│   └── tests.py                 # Unit tests
│
├── school_data_project/          # Django project settings
│   ├── __init__.py              # Python package marker
│   ├── asgi.py                  # ASGI configuration
│   ├── settings.py              # Project settings
│   ├── urls.py                  # Root URL configuration
│   └── wsgi.py                  # WSGI configuration
│
├── uploads/                      # Uploaded CSV files directory
│   ├── enrollment_certified_*.csv
│   ├── discipline_actions_*.csv
│   └── [other uploaded files]
│
├── venv/                         # Python virtual environment (excluded from git)
│
├── .vscode/                      # VS Code configuration
│   └── launch.json              # Debugger configuration
│
├── .git/                         # Git repository data
├── .gitignore                   # Git ignore rules
├── .gitattributes               # Git attributes
│
├── db.sqlite3                   # SQLite database (development)
├── manage.py                    # Django management script
├── README.md                    # Project README (root documentation)
├── requirements.txt             # Python dependencies
│
└── [Generated output files]     # CSV/Excel exports
    ├── combined_transformed_data.csv
    ├── transformed_*_data.csv
    └── *.xlsx files
```

## Detailed Component Descriptions

### 1. `__data_processor__/` - Main Application

The core Django application containing all data processing logic.

#### **models.py** (12 Models)
Defines the database schema for:

**Reference Data Models:**
- `Stratification` - Maps group_by/group_by_value to Metopio label names
- `CountyGEOID` - County to GEOID mappings
- `SchoolAddressFile` - School location and contact information

**Input Data Models:**
- `SchoolData` - Raw enrollment data from Wisconsin DPI
- `SchoolRemovalData` - Raw disciplinary removal data

**Transformation Output Models:**
- `TransformedSchoolData` - Basic statewide enrollment transformation
- `MetopioStateWideLayerTransformation` - Statewide removal transformations
- `MetopioTriCountyLayerTransformation` - Tri-county layer transformations
- `CountyLayerTransformation` - County-level transformations
- `ZipCodeLayerTransformation` - ZIP code layer transformations
- `MetopioCityLayerTransformation` - City/town layer transformations
- `CombinedRemovalData` - Combined multi-layer transformations

**Removal-Specific Models:**
- `MetopioStateWideRemovalDataTransformation`
- `MetopioTriCountyRemovalDataTransformation`
- `CountyLayerRemovalData`
- `ZipCodeLayerRemovalData`
- `MetopioCityRemovalData`

#### **views.py** (30+ View Functions)
Handles HTTP requests and responses:

**Upload & Processing Views:**
- `upload_file()` - Main file upload handler
- `handle_uploaded_file()` - Processes uploaded CSV files
- `load_county_geoid_file()` - Loads county GEOID reference data
- `load_school_address_file()` - Loads school address data
- `load_school_removal_data()` - Loads removal data

**Transformation Views:**
- `transformation_success()` - Post-transformation success page
- `data_processor_home()` - Homepage with transformation options

**Display Views (with pagination):**
- `statewide_view()` - Display statewide enrollment data
- `statewide_removal()` - Display statewide removal data
- `tri_county_view()` - Display tri-county data
- `tri_county_removal_view()` - Display tri-county removal data
- `county_layer_view()` - Display county layer data
- `county_layer_removal_view()` - Display county removal data
- `metopio_statewide_view()` - Display Metopio statewide layer
- `metopio_zipcode_view()` - Display ZIP code layer
- `city_town_view()` - Display city/town layer
- `city_layer_removal_view()` - Display city removal data
- `zipcode_layer_removal_view()` - Display ZIP removal data
- `combined_removal_view()` - Display combined removal data

**Export Views:**
- `download_csv()` - Generate and download CSV files
- `download_excel()` - Generate and download Excel files
- `generate_transformed_csv()` - CSV generation logic
- `generate_transformed_excel()` - Excel generation logic
- `generate_combined_csv()` - Combined CSV generation

#### **transformers.py** (DataTransformer Class)
Contains the core business logic for data transformations:

**Main Class:**
- `DataTransformer` - Orchestrates all transformation operations

**Key Methods:**
- `apply_transformation()` - Routes to specific transformation
- `transform_Statewide_V01()` - Statewide enrollment transformation
- `transform_Statewide_Removal()` - Statewide removal transformation
- `apply_tri_county_layer_transformation()` - Tri-county transformation
- `transform_Tri_County_Removal()` - Tri-county removal transformation
- `apply_county_layer_transformation()` - County layer transformation
- `transform_County_Layer_Removal()` - County removal transformation
- `transforms_Metopio_ZipCodeLayer()` - ZIP code transformation
- `transform_Zipcode_Layer_Removal()` - ZIP removal transformation
- `transform_Metopio_CityLayer()` - City/town transformation
- `transform_City_Layer_Removal()` - City removal transformation
- `transform_Metopio_StateWideLayer()` - Metopio statewide layer
- `transform_combined_removal()` - Combined removal transformation

**Helper Methods:**
- Aggregation logic
- Unknown value calculation
- GEOID matching
- Stratification mapping

#### **urls.py**
URL routing for all views (30+ routes):
- Upload endpoints
- Transformation trigger endpoints
- Display endpoints (with pagination)
- Download endpoints (CSV/Excel)

#### **forms.py**
Form definitions for file uploads:
- `UploadFileForm` - Multi-file upload form

#### **admin.py**
Django admin interface configurations for all models.

#### **templates/__data_processor__/**
HTML templates for the web interface:
- `upload.html` - File upload interface
- `success.html` - Transformation success page
- `statewide.html` - Statewide data display
- `tricounty.html` - Tri-county data display
- `county_layer.html` - County layer display
- `metopio_statewide.html` - Metopio statewide display
- `metopio_zipcode.html` - ZIP code display
- `city_town.html` - City/town display
- `statewide_removal.html` - Statewide removal display
- `tricounty_removal.html` - Tri-county removal display
- `county_layer_removal.html` - County removal display
- `zipcode_layer_removal.html` - ZIP removal display
- `city_layer_removal.html` - City removal display
- `combined_removal.html` - Combined removal display

#### **static/css/**
Stylesheets for the web interface.

#### **migrations/**
Database migration files tracking schema changes.

### 2. `school_data_project/` - Django Project Configuration

#### **settings.py**
Project-wide settings:
- Database configuration
- Installed apps
- Middleware
- Static files configuration
- Templates configuration
- Logging configuration

#### **urls.py**
Root URL configuration:
- Includes `__data_processor__.urls`
- Admin site URL

#### **wsgi.py** & **asgi.py**
WSGI/ASGI application entry points for deployment.

### 3. `uploads/` - Data Storage

Stores uploaded CSV files:
- **Enrollment Data**: `enrollment_certified_YYYY-YY.csv`
- **Removal Data**: `discipline_actions_certified_YYYY-YY.csv`
- **Stratifications**: `PP10 Normalized Stratifications.csv`
- **County GEOIDs**: `Fox Valley Data Exchange Places GEIODs.csv`
- **School Addresses**: `sd-export-public-schools-*.csv`

### 4. Root Configuration Files

#### **manage.py**
Django command-line utility:
```bash
python manage.py runserver      # Start dev server
python manage.py migrate         # Run migrations
python manage.py createsuperuser # Create admin user
python manage.py test            # Run tests
```

#### **requirements.txt**
Python package dependencies:
- Django
- pandas
- openpyxl
- xlsxwriter
- (and others)

#### **.gitignore**
Excludes from version control:
- `venv/`
- `db.sqlite3`
- `__pycache__/`
- `*.pyc`
- `.env`
- `uploads/` (large data files)

#### **.vscode/launch.json**
VS Code debugger configuration for Django debugging.

### 5. Generated Output Files

Transformation results (not version controlled):
- `transformed_statewide-removal_data.csv`
- `transformed_tricounty-removal_data.csv`
- `transformed_county-layer_data.csv`
- `transformed_zipcode_data.csv`
- `transformed_city-removal_data.csv`
- `combined_transformed_data.csv`
- Various `.xlsx` files for intermediate analysis

## Data Flow

```
1. CSV Upload (views.py)
   ↓
2. Data Validation & Storage (models.py)
   ↓
3. Transformation Logic (transformers.py)
   ↓
4. Database Storage (Django ORM)
   ↓
5. Display/Export (views.py → templates)
```

## Key Design Patterns

### 1. **Model-View-Template (MVT)**
Django's standard architecture:
- **Models**: Data structure and business logic
- **Views**: Request handling and response generation
- **Templates**: HTML presentation

### 2. **Bulk Operations**
Efficient database operations:
- `bulk_create()` for inserting multiple records
- QuerySet aggregation for complex calculations

### 3. **Separation of Concerns**
- **models.py**: Data structure only
- **transformers.py**: Business logic
- **views.py**: Request/response handling
- **templates/**: Presentation logic

### 4. **Configuration Over Code**
- Settings in `settings.py`
- URL patterns in `urls.py`
- Environment variables in `.env`

## Development Workflow

1. **Data Upload**: User uploads CSV files via web interface
2. **Validation**: System validates file format and content
3. **Storage**: Data stored in appropriate models
4. **Transformation**: DataTransformer applies business logic
5. **Display**: Results shown with pagination
6. **Export**: User downloads transformed data

## Database Schema Relationships

```
Stratification (1) ←→ (M) SchoolData
CountyGEOID (1) ←→ (M) SchoolData
SchoolAddressFile (1) ←→ (M) [Various transformations via district/school code]
SchoolData (M) → [Transformations] → Output Models (M)
```

## File Naming Conventions

- **Models**: `PascalCase` (e.g., `SchoolData`)
- **Functions/Views**: `snake_case` (e.g., `upload_file`)
- **Templates**: `lowercase_with_underscores.html`
- **URLs**: `lowercase-with-hyphens`
- **CSS classes**: `kebab-case`

## Important Notes

1. **Leading Zeros**: Automatically stripped from district_code and school_code in save() methods
2. **Suppressed Values**: Rows with "*" or "0" are filtered out during processing
3. **Unknown Values**: System calculates unknown counts based on stratification totals
4. **GEOID Matching**: County names matched to GEOIDs for geographic layers
5. **Migrant Status**: Explicitly filtered out in removal data processing

## Environment-Specific Configurations

### Development
- SQLite database
- DEBUG=True
- Local file storage

### Production (Heroku)
- PostgreSQL database
- DEBUG=False
- WhiteNoise for static files
- Gunicorn WSGI server

## Security Considerations

1. **SECRET_KEY**: Stored in environment variables
2. **DEBUG**: Disabled in production
3. **ALLOWED_HOSTS**: Configured per environment
4. **File Uploads**: Validated and sanitized
5. **SQL Injection**: Protected via Django ORM

## Performance Optimizations

1. **Bulk Operations**: Using `bulk_create()` for insertions
2. **Database Indexing**: On frequently queried fields
3. **Pagination**: 20 records per page for large datasets
4. **Query Optimization**: Using `select_related()` and `prefetch_related()`
5. **Caching**: (Future enhancement)

## Testing Structure

```
__data_processor__/tests.py
├── Model Tests
├── View Tests
├── Transformation Logic Tests
└── Integration Tests
```

## Logging

Configured in `settings.py`:
- INFO level for general operations
- ERROR level for failures
- Custom logger: `__name__`

## Future Structure Additions

See ROADMAP.md for planned structural changes and enhancements.
