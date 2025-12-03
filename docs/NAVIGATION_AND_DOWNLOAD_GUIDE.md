# Navigation & Data Download Feature Guide

## Overview
The application now has improved navigation and automatic data download capabilities from WISEdash.

## Key Improvements

### 1. **Enhanced Home Page**
The home page now features a modern card-based layout with:
- **Data Management Section**: Quick access to auto-download or manual upload
- **View Results Section**: Access transformed data and downloads
- **Organized Transformations**: Three categories (Enrollment, Removal/Discipline, Forward Exam)

### 2. **Improved Navigation Bar**
The navigation has been reorganized with dropdown menus:
- 🏠 **Home**: Dashboard
- 📥 **Data Management**: Auto Download | Manual Upload
- 📚 **Enrollment**: All enrollment transformation types
- ⚠️ **Removal/Discipline**: All removal transformation types
- 📝 **Forward Exam**: All Forward Exam transformation types
- 📊 **Downloads**: Excel & CSV download options

### 3. **Auto Download Data Feature**
New page at `/data_processor/data_download/` that allows you to:

#### How to Use:
1. Navigate to **Data Management → Auto Download Data**
2. Select the **Data Type** from dropdown:
   - Enrollment (Certified)
   - Enrollment by Grade Level
   - Discipline Actions (Certified)
   - Discipline Incidents (Certified)
   - Forward Exam (3rd Grade Reading)
   - Agency/District Information
   - Absenteeism Data
   - Attendance & Dropouts

3. Select the **School Year** (e.g., 2024-25, 2023-24, etc.)

4. Click **"Download from WISEdash"**

5. The system will:
   - Construct the correct WISEdash URL
   - Download the ZIP file
   - Extract the CSV file
   - Save to your `uploads/` folder
   - Show success message with file details

#### Features:
- **Real-time feedback**: Shows download progress and results
- **Recent files list**: View last 10 downloaded files
- **Expected filename preview**: See what file will be downloaded
- **Error handling**: Clear messages if download fails

### 4. **WISEdash URL Pattern**
The system uses the official WISEdash URL pattern:
```
https://dpi.wi.gov/sites/default/files/imce/wisedash/data-files/{data_type}_certified_{year}.zip
```

Examples:
- `enrollment_certified_2023-24.zip`
- `discipline_actions_certified_2023-24.zip`
- `forward_certified_2024-25.zip`

## Workflow

### Option 1: Auto Download (NEW)
```
Home → Data Management → Auto Download Data
  ↓
Select Data Type & Year
  ↓
Click Download
  ↓
System downloads & extracts file
  ↓
File ready in uploads/ folder
  ↓
Run transformations from Home
```

### Option 2: Manual Upload (Existing)
```
Home → Data Management → Manual Upload
  ↓
Browse and select CSV file
  ↓
Upload file
  ↓
Run transformations from Home
```

## Technical Details

### New Files Created:
1. **Template**: `__data_processor__/templates/__data_processor__/data_download.html`
2. **View Function**: `data_download_view()` in `views.py`
3. **URL Route**: `/data_processor/data_download/`

### Dependencies Added:
- `requests>=2.28.0` - For HTTP downloads
- `pandas>=1.3.0` - Data processing
- `openpyxl>=3.0.0` - Excel support
- `xlsxwriter>=3.0.0` - Excel writing

### Key Features:
- ✅ Automatic file download from WISEdash
- ✅ ZIP file extraction
- ✅ File size validation
- ✅ Recent files tracking
- ✅ Error handling with user feedback
- ✅ Bootstrap 5 styling
- ✅ Responsive design

## Future Enhancements (From TODO)
As noted in the README, future improvements will include:
- API integration for scheduled automatic updates
- Background task processing for large files
- Email notifications on completion
- Data validation before transformation

## Troubleshooting

### If download fails:
1. Check your internet connection
2. Verify the data type and year are available on WISEdash
3. Visit https://dpi.wi.gov/wisedash/download-files to confirm file exists
4. Check console logs for detailed error messages

### If transformation fails:
1. Ensure the CSV file is in the `uploads/` folder
2. Check the file format matches expected structure
3. Review error messages in the UI
4. Check Django logs for detailed errors

## Testing the New Features

1. Start the Django server:
   ```bash
   python manage.py runserver
   ```

2. Navigate to: http://localhost:8000/

3. Click on "Auto Download Data" card

4. Try downloading an enrollment file for 2023-24

5. Return to Home and run a transformation

## Summary
The new navigation and auto-download features streamline the data processing workflow, eliminating the need to manually visit WISEdash, download files, and upload them. The organized navigation makes it easier to find and access specific transformation types.
