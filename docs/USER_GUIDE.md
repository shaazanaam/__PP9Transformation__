# Wisconsin School Data Processor - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Uploading Data Files](#uploading-data-files)
4. [Transformation Types](#transformation-types)
5. [Viewing Results](#viewing-results)
6. [Exporting Data](#exporting-data)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## Introduction

The Wisconsin School Data Processor is a web-based application designed to transform and analyze school enrollment and disciplinary removal data across multiple geographic layers.

### What Can You Do?
- Upload enrollment and removal data from Wisconsin DPI
- Transform data into multiple geographic layers (statewide, county, ZIP code, etc.)
- View transformed data with easy-to-use pagination
- Export results to CSV or Excel formats
- Analyze data by various stratifications (demographics, disabilities, etc.)

---

## Getting Started

### Accessing the Application

1. **Development Mode**: Navigate to `http://127.0.0.1:8000` in your web browser
2. **Production**: Access your deployed URL (e.g., `https://your-app.herokuapp.com`)

### Home Page

The home page displays all available transformation options organized by category.

---

## Uploading Data Files

### Required Files

To perform transformations, you need to upload the following files:

#### 1. **Main Data File** (Required)
- **Enrollment Data**: `enrollment_certified_YYYY-YY.csv`
- **Removal Data**: `discipline_actions_certified_YYYY-YY.csv`

**Expected Columns**:
- `SCHOOL_YEAR`
- `AGENCY_TYPE`
- `CESA`
- `COUNTY`
- `DISTRICT_CODE`
- `SCHOOL_CODE`
- `GRADE_GROUP`
- `CHARTER_IND`
- `DISTRICT_NAME`
- `SCHOOL_NAME`
- `GROUP_BY`
- `GROUP_BY_VALUE`
- `STUDENT_COUNT` (for enrollment) or `REMOVAL_COUNT` (for removals)
- `PERCENT_OF_GROUP`

#### 2. **Stratification File** (Required)
File: `PP10 Normalized Stratifications.csv`

**Expected Columns**:
- `GROUP_BY` - Category (e.g., "Disability Status", "Gender")
- `GROUP_BY_VALUE` - Specific value (e.g., "SwD", "Female")
- `Stratification` - Metopio label name (e.g., "SWD1", "FEM3")

**Important Notes**:
- Each row maps a GROUP_BY/GROUP_BY_VALUE combination to a Metopio stratification code
- The "All Students" row should have an empty Stratification field (represents "FULL")
- Do NOT include "Migrant Status" rows (they are filtered out)

#### 3. **County GEOID File** (Optional but recommended for geographic layers)
File: `Fox Valley Data Exchange Places GEIODs.csv`

**Expected Columns**:
- `County` - County name
- `GEOID` - Geographic identifier

#### 4. **School Address File** (Optional but recommended)
File: `sd-export-public-schools-YYYYMMDD.csv`

**Expected Columns**:
- `LEA Code` - District code
- `School Code`
- `Physical Address`
- `Physical City`
- `Physical ZIP`
- (other address fields)

### Upload Process

1. **Navigate to Upload Page**: Click "Upload Files" from the home page
2. **Select Files**: Choose the required files using the file browser
3. **Upload**: Click "Upload and Process"
4. **Wait**: The system will validate and process your files
5. **Confirmation**: You'll see a success message when complete

### File Validation

The system automatically:
- Validates file formats
- Checks for required columns
- Filters out suppressed values ("*") and zero counts
- Strips leading zeros from district/school codes
- Maps stratifications to database records

---

## Transformation Types

### Enrollment Transformations

#### 1. **Statewide Transformation**
- Aggregates data at the Wisconsin state level
- Groups by stratifications
- Calculates totals and percentages

**Output Model**: `TransformedSchoolData`

#### 2. **Tri-County Transformation**
- Focuses on Calumet, Outagamie, and Winnebago counties
- Includes stratification breakdowns
- Adds GEOID linkage

**Output Model**: `MetopioTriCountyLayerTransformation`

#### 3. **County Layer Transformation**
- Aggregates data by county
- All Wisconsin counties included
- GEOID-based geographic linking

**Output Model**: `CountyLayerTransformation`

#### 4. **ZIP Code Layer Transformation**
- Groups data by ZIP code
- Requires school address file
- Useful for local analysis

**Output Model**: `ZipCodeLayerTransformation`

#### 5. **City/Town Layer Transformation**
- Aggregates by municipality
- Uses physical city from address file
- Place-based analysis

**Output Model**: `MetopioCityLayerTransformation`

### Removal Data Transformations

#### 6. **Statewide Removal**
- State-level disciplinary removal data
- Includes removal type descriptions
- Stratification breakdowns

**Output Model**: `MetopioStateWideRemovalDataTransformation`

#### 7. **Tri-County Removal**
- Removal data for tri-county region
- Unknown value calculation
- GEOID linkage

**Output Model**: `MetopioTriCountyRemovalDataTransformation`

#### 8. **County Layer Removal**
- County-level removal data
- All counties included

**Output Model**: `CountyLayerRemovalData`

#### 9. **ZIP Code Layer Removal**
- ZIP code-based removal data

**Output Model**: `ZipCodeLayerRemovalData`

#### 10. **City Layer Removal**
- City/town removal data

**Output Model**: `MetopioCityRemovalData`

### Combined Transformations

#### 11. **Combined Removal Data**
- Merges all removal layers
- Comprehensive dataset
- Includes all geographic levels

**Output Model**: `CombinedRemovalData`

---

## Viewing Results

### Navigation

After a successful transformation:
1. Click the transformation name from the home page
2. Data displays with pagination (20 records per page)
3. Use "Previous" and "Next" buttons to navigate

### Data Display

Each view shows:
- School year
- County/Place
- District and school information
- Stratification details
- Student/removal counts
- Calculated percentages

### Filtering and Sorting

(Feature planned for Phase 2)

---

## Exporting Data

### CSV Export

1. Navigate to the transformation view
2. Click "Download CSV"
3. File saves to your downloads folder

**Filename format**: `transformed_[type]_data.csv`

### Excel Export

1. Navigate to the transformation view
2. Click "Download Excel"
3. File saves with `.xlsx` extension

**Advantages**:
- Formatted columns
- Better for sharing
- Opens in Excel/Google Sheets

### Combined Export

For removal data:
1. Go to "Combined Removal" view
2. Download includes all layers in one file
3. Useful for comprehensive analysis

---

## Troubleshooting

### Common Issues

#### "Error: Missing required columns"
**Solution**: Ensure your CSV has all required columns with exact names (case-sensitive)

#### "UnicodeDecodeError"
**Solution**: Save your CSV file with UTF-8 encoding

#### "File already processed"
**Solution**: The system detected a duplicate file. Delete the old file from `uploads/` or rename your new file

#### "No stratification found"
**Solution**: Ensure stratification file is uploaded and contains all GROUP_BY/GROUP_BY_VALUE combinations from your main data

#### "'NoneType' object has no attribute 'label_name'"
**Solution**: A stratification mapping is missing. Check that:
- Stratification file has all required GROUP_BY values
- No typos in GROUP_BY or GROUP_BY_VALUE
- "Migrant Status" rows are NOT in your stratification file

#### "'<' not supported between instances"
**Solution**: Internal sorting issue. Report to development team.

### Debug Mode

If you encounter errors:
1. Check the terminal/console for detailed error messages
2. Look for the line number and error type
3. Contact support with the full error message

### Getting Help

- **GitHub Issues**: Open an issue with detailed description
- **Email Support**: Contact development team
- **Documentation**: Check docs/ folder for technical details

---

## FAQ

### Q: What file formats are supported?
**A**: CSV files only. Ensure UTF-8 encoding.

### Q: How large can my files be?
**A**: No hard limit, but files over 100MB may take several minutes to process.

### Q: Can I upload multiple years at once?
**A**: Yes, but each file is processed separately. Combine years in your CSV before uploading.

### Q: What happens to "*" values?
**A**: Suppressed values are automatically filtered out during processing.

### Q: How are "Unknown" values calculated?
**A**: System calculates the difference between "All Students" and sum of stratifications, then creates unknown records.

### Q: Why is "Migrant Status" excluded?
**A**: By design, Migrant Status is filtered out in removal data processing.

### Q: Can I delete uploaded data?
**A**: Admin users can delete via Django admin. Regular users should contact admin.

### Q: How do I view historical transformations?
**A**: Current version only shows latest transformation. Version history planned for Phase 3.

### Q: Can I export to other formats (JSON, XML)?
**A**: CSV and Excel only. API with JSON support planned for Phase 3.

### Q: How do I update stratification mappings?
**A**: Upload a new stratification file. It will replace the old one.

### Q: What's the difference between layers?
**A**: 
- **Statewide**: Entire Wisconsin
- **Tri-County**: Calumet, Outagamie, Winnebago only
- **County**: All counties separately
- **ZIP**: By ZIP code
- **City**: By municipality

### Q: How often should I update data?
**A**: Whenever new certified data is released by Wisconsin DPI (typically annually).

### Q: Can I schedule automatic uploads?
**A**: Not currently. Planned for Phase 3 with API integration.

### Q: Is my data secure?
**A**: Yes. Data is stored in a local database. Production deployments use encrypted connections.

---

## Tips & Best Practices

### Data Preparation
1. Always use the most recent certified data from Wisconsin DPI
2. Verify column names match exactly
3. Save files with UTF-8 encoding
4. Remove any extra header rows or comments
5. Ensure consistent year format (YYYY-YY)

### Workflow
1. Upload stratification file first
2. Upload county GEOID and address files
3. Upload main enrollment/removal data
4. Run transformations in order (statewide first)
5. Verify results before exporting
6. Keep backup copies of original files

### Performance
- Close other applications during large uploads
- Use wired internet connection for stability
- Allow sufficient time for processing (5-10 minutes for large files)

### Quality Checks
- Review "Unknown" counts (should be reasonable)
- Compare totals across layers (should match)
- Spot-check a few records manually
- Verify GEOID mappings are correct

---

## Keyboard Shortcuts

(Planned for future release)

---

## Version Information

**Current Version**: 1.0.0  
**Last Updated**: January 2025  
**Compatible Data Years**: 2018-19 through 2024-25

---

## Additional Resources

- **Technical Documentation**: See docs/PROJECT_STRUCTURE.md
- **Development Roadmap**: See docs/ROADMAP.md
- **GitHub Repository**: [shaazanaam/__PP9Transformation__](https://github.com/shaazanaam/__PP9Transformation__)

---

**Need More Help?**  
Contact the development team or open an issue on GitHub with detailed information about your problem.
