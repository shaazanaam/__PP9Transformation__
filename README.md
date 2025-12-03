# Wisconsin School Data Processor (PP9 Transformation)

A Django-based web application for processing, transforming, and analyzing Wisconsin school enrollment and disciplinary removal data. This application supports multiple geographic layers and stratifications for detailed educational data analysis.

## 🎯 Overview

The Wisconsin School Data Processor handles complex transformations of school data across multiple geographic layers:
- **Statewide** - Wisconsin-level aggregations
- **Tri-County** - Calumet, Outagamie, and Winnebago counties
- **County Layer** - All Wisconsin counties
- **ZIP Code Layer** - ZIP code-based geographic analysis
- **City/Town Layer** - Municipality-level data

The application processes both **enrollment data**, **disciplinary removal data**, and **Forward Exam data** (3rd Grade Reading Proficiency) with support for various stratifications (demographics, grade levels, disability status, etc.).

## 🏗️ Application Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Upload View │  │ Transform    │  │   Download   │             │
│  │              │→ │   View       │→ │     View     │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└────────────────────────────┬──────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     DJANGO APPLICATION LAYER                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                         views.py                              │  │
│  │  - File Upload Handler                                        │  │
│  │  - Transformation Router                                      │  │
│  │  - Download Generator (CSV/Excel)                            │  │
│  └───────────────────────┬──────────────────────────────────────┘  │
│                          ↓                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    transformers.py                            │  │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐│  │
│  │  │   Enrollment    │  │    Removal       │  │  Forward Exam ││  │
│  │  │ Transformations │  │ Transformations  │  │Transformations││  │
│  │  │                 │  │                  │  │               ││  │
│  │  │ - Statewide     │  │ - Statewide      │  │ - Statewide   ││  │
│  │  │ - Tri-County    │  │ - Tri-County     │  │ - Tri-County  ││  │
│  │  │ - County        │  │ - County         │  │ - County      ││  │
│  │  │ - Zip Code      │  │ - Zip Code       │  │ - Zip Code    ││  │
│  │  │ - City          │  │ - City           │  │ - City        ││  │
│  │  │ - Combined      │  │ - Combined       │  │ - Combined    ││  │
│  │  └─────────────────┘  └──────────────────┘  └──────────────┘│  │
│  └───────────────────────┬──────────────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER (models.py)                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Raw Data Models                                            │    │
│  │  - SchoolData (Enrollment)                                  │    │
│  │  - SchoolRemovalData (Discipline Actions)                   │    │
│  │  - ForwardExamData (Test Results)                          │    │
│  └────────────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Reference Data Models                                       │    │
│  │  - Stratification (Demographics Mapping)                     │    │
│  │  - CountyGEOID (Geographic IDs)                            │    │
│  │  - SchoolAddressFile (School Locations)                     │    │
│  └────────────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Transformed Data Models (Output)                           │    │
│  │  - MetopioStateWideLayerTransformation                      │    │
│  │  - MetopioTriCountyLayerTransformation                      │    │
│  │  - CountyLayerTransformation                                │    │
│  │  - ZipCodeLayerTransformation                               │    │
│  │  - MetopioCityLayerTransformation                           │    │
│  │  - ForwardExamStateWideTransformation                       │    │
│  │  - ForwardExamTriCountyTransformation                       │    │
│  │  - ForwardExamCountyLayerTransformation                     │    │
│  │  - ForwardExamZipCodeLayerTransformation                    │    │
│  │  - ForwardExamCityLayerTransformation                       │    │
│  │  - ForwardExamCombinedTransformation                        │    │
│  │  ... and removal data transformations                       │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘

Data Flow:
1. User uploads CSV files → views.py handles upload
2. Data stored in raw models → SchoolData, SchoolRemovalData, ForwardExamData
3. User triggers transformation → transformers.py processes data
4. Transformed data saved → Transformation models
5. User downloads results → CSV/Excel export
```

## ✨ Key Features

- 📊 **Multiple Transformation Types**: Support for 10+ data transformation types
- 📁 **Bulk Data Processing**: Efficient CSV upload and processing with validation
- 🗺️ **Geographic Mapping**: GEOID-based geographic data linkage
- 📈 **Stratification Support**: Demographics, disabilities, economic status, EL status, gender, and grade levels
- 📥 **Export Capabilities**: Download transformed data in CSV and Excel formats
- 🔍 **Data Validation**: Automatic handling of suppressed (*) and zero values
- 📋 **Pagination**: Easy navigation through large datasets
- 🎨 **Web Interface**: User-friendly upload and transformation interface

## 📋 Requirements

- Python 3.8+
- Django 3.2+
- PostgreSQL (recommended) or SQLite (development)
- pandas
- openpyxl
- xlsxwriter

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/shaazanaam/__PP9Transformation__.git
cd __PP9Transformation__
```

### 2. Set Up Virtual Environment
```bash
# On Windows with bash
python -m venv venv
source venv/Scripts/activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Create a `.env` file in the project root:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Create Superuser
```bash
python manage.py createsuperuser
```

### 7. Run Development Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your browser.

## 📚 Documentation

Detailed documentation is available in the `docs/` folder:

- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Complete folder and file organization
- **[Project Roadmap](docs/ROADMAP.md)** - Development phases and future enhancements
- **[User Guide](docs/USER_GUIDE.md)** - How to use the application
- **[API Documentation](docs/API.md)** - Technical API reference

## 🔄 Data Processing Workflow

1. **Upload Files**
   - Main enrollment/removal data (CSV)
   - Stratification mappings (CSV)
   - County GEOID reference (CSV)
   - School address file (CSV)

2. **Select Transformation Type**
   - Choose from 10+ transformation options
   - System validates and processes data

3. **View Results**
   - Browse transformed data with pagination
   - Download as CSV or Excel

4. **Export**
   - Individual transformation exports
   - Combined multi-layer exports

## 🗃️ Supported Data Files

### Input Files
- **Enrollment Data**: `enrollment_certified_YYYY-YY.csv`
- **Removal Data**: `discipline_actions_certified_YYYY-YY.csv`
- **Stratifications**: `PP10 Normalized Stratifications.csv`
- **County GEOIDs**: `Fox Valley Data Exchange Places GEIODs.csv`
- **School Addresses**: `sd-export-public-schools-YYYYMMDD.csv`

### Output Files
- **Statewide**: `transformed_statewide-removal_data.csv`
- **Tri-County**: `transformed_tricounty-removal_data.csv`
- **County**: `transformed_county-layer_data.csv`
- **ZIP Code**: `transformed_zipcode_data.csv`
- **City**: `transformed_city-removal_data.csv`
- **Combined**: `combined_transformed_data.csv`

## 🛠️ Technology Stack

- **Backend**: Django 3.2+
- **Database**: SQLite (dev), PostgreSQL (production)
- **Data Processing**: pandas, openpyxl
- **Frontend**: Django Templates, Bootstrap (via static files)
- **Deployment**: Heroku-ready

## 📦 Deployment

### Heroku Deployment

1. **Install Heroku CLI**
```bash
# Windows (using Chocolatey)
choco install heroku-cli

# macOS
brew tap heroku/brew && brew install heroku
```

2. **Login and Create App**
```bash
heroku login
heroku create your-app-name
```

3. **Configure for Deployment**
Ensure you have:
- `Procfile`
- `runtime.txt`
- `requirements.txt` with `gunicorn`, `whitenoise`, `dj-database-url`, `psycopg2-binary`

4. **Deploy**
```bash
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed deployment instructions.

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test __data_processor__
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is proprietary. All rights reserved.

## 👥 Authors

- **Shaazanaam** - [shaazanaam](https://github.com/shaazanaam)

## 🙏 Acknowledgments

- Wisconsin Department of Public Instruction for data standards
- Fox Valley community partners for geographic data requirements

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Contact the development team

## 📋 TODO - Future Enhancements

### High Priority

#### 🔌 API Data Integration
**Problem:** Currently, users must manually upload CSV files for each transformation, which is time-consuming and error-prone.

**Proposed Solution:** Integrate with data source API to automatically fetch the latest school data, eliminating manual uploads.

**Benefits:**
- Automated data updates
- Reduced user workload
- Real-time data availability
- Fewer upload errors
- Streamlined workflow

**Implementation Considerations:**
- API endpoint to be provided
- Support for scheduling automatic data fetches
- Fallback to manual upload if API unavailable
- Data validation after API fetch
- Cache mechanism to reduce API calls
- Authentication/API key management
- Error handling for API timeouts or failures

**Status:** 🟡 Planned - Endpoint information pending

---

## 📈 Project Status

**Current Version**: 1.0.0  
**Status**: Active Development

See [ROADMAP.md](docs/ROADMAP.md) for planned features and improvements.