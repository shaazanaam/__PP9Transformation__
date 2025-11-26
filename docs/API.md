# API Documentation

## Overview

This document provides technical API documentation for the Wisconsin School Data Processor. Note that a formal RESTful API is planned for Phase 3. This document currently describes the internal view-based endpoints.

---

## Base URL

**Development**: `http://127.0.0.1:8000`  
**Production**: `https://your-app.herokuapp.com`

---

## Authentication

Currently, no authentication is required for most endpoints. Admin endpoints require Django admin login.

**Planned (Phase 3)**: Token-based authentication with JWT.

---

## Endpoints

### 1. Upload & Processing

#### Upload Files
**URL**: `/data_processor/upload/`  
**Method**: `POST`  
**Content-Type**: `multipart/form-data`

**Parameters**:
- `file` (required): Main CSV file (enrollment or removal data)
- `stratifications_file` (optional): Stratification mapping CSV
- `county_geoid_file` (optional): County GEOID reference CSV
- `school_address_file` (optional): School address CSV

**Response**:
- **Success**: Redirect to transformation success page
- **Error**: Error message with details

**Example**:
```bash
curl -X POST http://127.0.0.1:8000/data_processor/upload/ \
  -F "file=@enrollment_certified_2023-24.csv" \
  -F "stratifications_file=@PP10_Normalized_Stratifications.csv"
```

---

### 2. View Transformed Data

#### Statewide Enrollment
**URL**: `/data_processor/statewide/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number (default: 1)

**Response**: HTML page with paginated data

**Data Fields**:
- `school_year`
- `county`
- `district_name`
- `school_name`
- `group_by`
- `group_by_value`
- `student_count`

#### Statewide Removal
**URL**: `/data_processor/statewide-removal/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

**Response**: HTML page with removal data

#### Tri-County Enrollment
**URL**: `/data_processor/tricounty/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

**Response**: HTML page with tri-county data

#### Tri-County Removal
**URL**: `/data_processor/tricounty-removal/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

#### County Layer
**URL**: `/data_processor/county-layer/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

#### County Layer Removal
**URL**: `/data_processor/county-layer-removal/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

#### Metopio Statewide
**URL**: `/data_processor/metopio-statewide/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

#### ZIP Code Layer
**URL**: `/data_processor/metopio-zipcode/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

#### ZIP Code Layer Removal
**URL**: `/data_processor/zipcode-layer-removal/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

#### City/Town Layer
**URL**: `/data_processor/city-town/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

#### City Layer Removal
**URL**: `/data_processor/city-layer-removal/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

#### Combined Removal
**URL**: `/data_processor/combined-removal/`  
**Method**: `GET`  
**Query Parameters**:
- `page` (optional): Page number

---

### 3. Export Data

#### Download CSV
**URL**: `/data_processor/download/<transformation_type>/csv/`  
**Method**: `GET`

**Transformation Types**:
- `statewide`
- `statewide-removal`
- `tricounty`
- `tricounty-removal`
- `county-layer`
- `county-layer-removal`
- `metopio-statewide`
- `metopio-zipcode`
- `zipcode-layer-removal`
- `city-town`
- `city-layer-removal`
- `combined-removal`

**Response**: CSV file download

**Example**:
```bash
curl -O http://127.0.0.1:8000/data_processor/download/statewide/csv/
```

#### Download Excel
**URL**: `/data_processor/download/<transformation_type>/excel/`  
**Method**: `GET`

**Response**: Excel (.xlsx) file download

**Example**:
```bash
curl -O http://127.0.0.1:8000/data_processor/download/tricounty-removal/excel/
```

---

## Data Models

### Stratification
**Fields**:
- `id` (int): Primary key
- `group_by` (str): Category (e.g., "Disability Status")
- `group_by_value` (str): Value (e.g., "SwD")
- `label_name` (str): Metopio code (e.g., "SWD1")

### CountyGEOID
**Fields**:
- `id` (int): Primary key
- `county` (str): County name
- `geoid` (str): Geographic identifier

### SchoolData
**Fields**:
- `id` (int): Primary key
- `school_year` (str): Academic year (e.g., "2023-24")
- `agency_type` (str): Type of agency
- `cesa` (str): CESA region
- `county` (str): County name
- `district_code` (str): District code (leading zeros stripped)
- `school_code` (str): School code (leading zeros stripped)
- `grade_group` (str): Grade grouping
- `charter_ind` (str): Charter indicator
- `district_name` (str): District name
- `school_name` (str): School name
- `group_by` (str): Stratification category
- `group_by_value` (str): Stratification value
- `student_count` (int): Number of students
- `percent_of_group` (str): Percentage
- `stratification` (FK): Link to Stratification model

### SchoolRemovalData
**Fields**:
- Similar to SchoolData
- `removal_type_description` (str): Type of removal
- `tfs_enrollment_count` (str): TFS enrollment
- `removal_count` (str): Number of removals

### TransformedSchoolData
**Fields**:
- `year` (str): School year
- `county` (str): County
- `district_code` (str)
- `school_code` (str)
- `district_name` (str)
- `school_name` (str)
- `group_by` (str)
- `group_by_value` (str)
- `student_count` (int)
- `stratification` (FK)

### MetopioTriCountyLayerTransformation
**Fields**:
- All SchoolData fields
- `place` (str): Place name
- `geoid` (FK): Link to CountyGEOID

### MetopioStateWideRemovalDataTransformation
**Fields**:
- All removal fields
- State-level aggregations

### CountyLayerTransformation
**Fields**:
- County-specific fields
- `geoid` (FK)

### ZipCodeLayerTransformation
**Fields**:
- ZIP code-specific fields
- Address information

### MetopioCityLayerTransformation
**Fields**:
- City/town-specific fields

### CombinedRemovalData
**Fields**:
- Combined fields from all layers

---

## Error Handling

### Common HTTP Status Codes

- **200 OK**: Success
- **302 Found**: Redirect (after successful upload)
- **400 Bad Request**: Invalid input data
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

### Error Response Format

Currently returns HTML error pages. JSON error responses planned for Phase 3.

**Example Error**:
```html
<h1>Error</h1>
<p>Error processing file: Missing required column 'SCHOOL_YEAR'</p>
```

---

## Rate Limiting

Currently no rate limiting. Planned for Phase 3 API.

---

## Pagination

**Default**: 20 records per page

**Query Parameter**: `?page=<number>`

**Example**:
```
/data_processor/statewide/?page=2
```

---

## Future API (Phase 3)

### Planned RESTful Endpoints

#### Authentication
```
POST /api/auth/login/
POST /api/auth/logout/
POST /api/auth/register/
```

#### Transformations
```
GET  /api/transformations/
POST /api/transformations/
GET  /api/transformations/{id}/
PUT  /api/transformations/{id}/
DELETE /api/transformations/{id}/
```

#### Data Query
```
GET /api/data/{layer}/
  ?year=2023-24
  &county=Outagamie
  &group_by=Gender
  &page=1
  &limit=50
```

#### Exports
```
GET /api/export/{layer}/csv/
GET /api/export/{layer}/excel/
GET /api/export/{layer}/json/
```

### Authentication (Planned)

**Token-based authentication** with JWT:

**Request**:
```bash
curl -X POST http://api.example.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

**Response**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "user",
    "email": "user@example.com"
  }
}
```

**Using Token**:
```bash
curl -X GET http://api.example.com/api/data/statewide/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Webhooks (Planned)

Subscribe to transformation completion events:

**Endpoint**: `/api/webhooks/subscribe/`

**Payload**:
```json
{
  "url": "https://your-service.com/webhook",
  "events": ["transformation.complete", "transformation.error"]
}
```

**Webhook Callback**:
```json
{
  "event": "transformation.complete",
  "transformation_id": 123,
  "layer": "statewide-removal",
  "timestamp": "2025-01-15T10:30:00Z",
  "record_count": 5420
}
```

---

## SDK & Client Libraries (Planned)

### Python Client
```python
from pp9_client import PP9Client

client = PP9Client(api_key="your_api_key")
data = client.get_statewide_data(year="2023-24", county="Outagamie")
```

### JavaScript Client
```javascript
import { PP9Client } from 'pp9-client';

const client = new PP9Client({ apiKey: 'your_api_key' });
const data = await client.getStatewideData({ year: '2023-24' });
```

---

## OpenAPI Specification (Planned)

Full OpenAPI 3.0 specification will be available at:
```
/api/schema/
/api/docs/
```

Interactive API documentation with Swagger UI.

---

## Performance Tips

1. **Use pagination** for large datasets
2. **Cache responses** when possible
3. **Filter data** at the API level rather than client-side
4. **Use CSV export** for bulk data extraction

---

## Support

For API questions or issues:
- Open a GitHub issue
- Contact development team
- Check docs for updates

---

**Last Updated**: January 2025  
**API Version**: Internal v1.0 (RESTful API v1.0 planned Q2 2025)
