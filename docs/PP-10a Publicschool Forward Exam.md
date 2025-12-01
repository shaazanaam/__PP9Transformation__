
Fox Valley Data Exchange
Data Structure and Framework Action and Advisory Team
Data Source Document
Contents
Data Source/Topic	1
Use Case	2
Input File Dimensions	2
Input Data File	2
Download Instructions	2
Discipline Actions_certified_Download File layout	2
File Lookups	3
School Address File	4
Stratifications File	4
Places File	5
Output Files for Metopio	5
Statewide Layer	7
Tri-County Layer	8
County Layer	8
Zip Code Layer	9
City or town Layer	10
Validation Method	10
Code to format the files	12
Authenticity	12
Comments	12


Data Source/Topic

Identifier	FVDEX-PP-10
Data Source Name	WISEdata
Data Source Link if any	WISEdash Public Portal - Department of Public Instruction
WISEdash Data Files by Topic | Wisconsin Department of Public Instruction
Download Type = ‘Forward’
Input: the files that are named as forward_certified_2023-24.zip
including 2023 forward 
Topic Name or other specifics within data source	Public School Forward Exam Prof (3rd Grade Reading) Count
Public School Forward Exam Prof (3rd Grade Reading) %
(proficient at grade level)

This specification includes two topics.
Vital Condition	Lifelong Learning
Requested by (name)	Sarahjean Schluechtermann
Update frequency	Yearly in September
Cost to obtain	free
Contact to obtain	none
Recorded by (Data Dingo conducting interview)	Susan Conzelman
Technical Solution	Shaaz Anaam

Use Case
This metric provides direction on readiness
Input File Dimensions

Input Data File

Download Instructions
There is one file for each year which can be found in this link:
WISEdash Data Files by Topic | Wisconsin Department of Public Instruction
Filter Download Type dropdown to “Forward”
The files that begin with “forward_actions_certified” followed by the school year range.zip are the ones to download. Click on the file name and open the file from your browser pop-up:

Forward_certified_Download File layout
Columns used are in bold:
Field No	Field Name	Field Datatype	Length	Field Description
1	SCHOOL_YEAR	Text	7	School year of enrollment
2	AGENCY_TYPE	Text	50	School/district type
3	CESA	Text	10	Cooperative Educational Service Agency
4	COUNTY	Text	50	County of main district office
5	DISTRICT_CODE	Text	10	District code - Unique 4 digit code assigned by DPI
6	SCHOOL_CODE	Text	10	School code - 4 digit code unique within district and assigned by DPI
7	GRADE_GROUP	Text	50	School grade group. Grade ranges of schools in the same GRADE_GROUP may vary. See also LOW_GRADE and HIGH_GRADE
8	CHARTER_IND	Text	4	Whether school/district is a charter SCHOOL_NAME
9	DISTRICT_NAME	Text	100	District name
10	SCHOOL_NAME	Text	100	School name
11	TEST_SUBJECT	Text	50	Test subject
12	GRADE_LEVEL	Text	50	Student grade when tested
13	TEST_RESULT	Text	50	Performance category
14	TEST_RESULT_CODE	Text	50	Performance category code
15	TEST_GROUP	Text	100	Test group - WKCE/WAA-SwD
16	GROUP_BY	Text	50	Data group - student attribute name
17	GROUP_BY_VALUE	Text	200	Data group - student attribute value
18	STUDENT_COUNT	Text	20	Count of students
19	PERCENT_OF_GROUP	Text	20	Percentage of the sub group within data group
20	GROUP_COUNT	Text	20	Count of students in the “GROUP BY” category
21	FORWARD_AVERAGE_SCALE_SCORE	Text	10	Mean scale score earned by students who took forward (for the TEST_SUBJECT and GRADE_LEVEL)

File Lookups
In addition to the input file, we have other files that have further information needed to format the data for Metopio:

 
School Address File
WISEdash allows us to download the school directory file where we can get the zip code and city of the school to use for those aggregation layers. Do this lookup for every row in the Input File to add City and Zip.
Sd-export-public-schools-20241208.1059 (each year a new version needs to be downloaded)
If concatenating the two columns to make a key “string” to compare, be sure to remove leading zeroes from the fields being compared. Otherwise a match won’t be found.
Column	Column Heading	Comment
A	LEA Code	Join DISTRICT_CODE
C	School Code	Join SCHOOL_CODE
J	City	Set to “ERROR” if not found.
L	Zip	Set to “ERROR” if not found.

Stratifications File
Stratifications in Metopio each have a unique code. We need to translate the Group by fields and values into the ones we added there.
PP8 Stratifications.csv can be found in the FVDEX Teams Meeting Library. It may need to be updated if new values are found in new input files. PP8 and PP9 share the same stratifications.

Column	Column Heading	Comment
A	GROUP_BY	Join to GROUP_BY
B	GROUP_BY_VALUE	Join to GROUP_BY_VALUE
C	Stratification	Use this value in the output file

This file is manually created after adding the stratifications to the Metopio in the Administrator Site. Click on “Data”   then “Stratifications” under “Topic Management”. Find the Metopio Stratification that will be used then click on its Name. Example:
 
The “Key” is unique across all stratifications. This is what is needed in the Metopio upload file.

Places File
Fox Valley Data Exchange Places GEIODs.csv can be found in the FVDEX Teams Meeting Library. We use this file to obtain the GEOID used in Metopio for each place. This lookup is done differently for each aggregation layer below.
Column	Column Heading	Comment
A	Layer	Filter or join to the layer needed:
Region
County
Zip Code
City or town
B	Name	Join to this field using the input file
C	GEOID	Set to “ERROR” if not found.

This file was created manually by Metopio and sent to us. It can be recreated through the “Download” dropdown on the far left of the Atlas site, but this has to be done for each Geographic Layer and then combined. Since it doesn’t change, it is easier to simply use our saved file.
Output Files for Metopio

Format a .csv file with rows for each geographic layer. Steps:
1 – Read the above file and filter to these rows:
	
DISTRICT_NAME = [Statewide] or COUNTY = ‘Outagamie’, ‘Winnebago’, and ‘Calumet’
SCHOOL_NAME not=’Districtwide’
Group By not = ‘Migrant Status’
GRADE_LEVEL = 3
TEST_GROUP = ‘Forward’
TEST_RESULT = ‘Meeting’ or ’Advanced’
There are no redacted data points with this criteria. 
This topic will show a % of the total student count 

Statewide Layer


Filter to:
	DISTRICT_NAME = [Statewide]
Column Name	Comment (granularity/sample values/aggregation method for measures)
layer	‘State’
geoid	‘WI’
topic	‘FVDEHAAP’
stratification	See above notes
period	SCHOOL YEAR, but insert ‘20’ on the second year’s range (after the hyphen). So 2023-24 becomes 2023-2024
value	STUDENT_COUNT / STUDENT_COUNT for the “All Students” group.


Tri-County Layer

Filter to:
	COUNTY = ‘Outagamie’, ‘Winnebago’, and ‘Calumet’

Column Name	Comment (granularity/sample values/aggregation method for measures)
layer	‘Region’
geoid	‘fox-valley’

topic	‘FVDEHAAP’
stratification	See above notes
period	SCHOOL YEAR, but insert ‘20’ on the second year’s range. So 2023-24 becomes 2023-2024
value	REMOVAL_COUNT

County Layer

Filter to:
	COUNTY = ‘Outagamie’, ‘Winnebago’, and ‘Calumet’


Column Name	Comment (granularity/sample values/aggregation method for measures)
layer	‘County’
geoid	See notes above.
Filter Places source to Layer = ‘County’
Concatenate Input  “COUNTY”, ‘ County, WI’ and match to Places.Name to get GEOID
topic	‘FVDEHAAP’
stratification	See above notes
period	SCHOOL YEAR, but insert ‘20’ on the second year’s range. So 2023-24 becaomes 2023-2024
value	REMOVAL_COUNT

Zip Code Layer

Filter to:
	
	COUNTY = ‘Outagamie’, ‘Winnebago’, and ‘Calumet’

Column Name	Comment (granularity/sample values/aggregation method for measures)
layer	‘Zip Code’
geoid	Zip from School Address logic above

topic	‘FVDEHAAP’
stratification	See above notes
period	SCHOOL YEAR, but insert ‘20’ on the second year’s range. So 2023-24 becaomes 2023-2024
value	REMOVAL_COUNT

City or town Layer

Filter to:
	
	COUNTY = ‘Outagamie’, ‘Winnebago’, and ‘Calumet’

Column Name	Comment (granularity/sample values/aggregation method for measures)
layer	‘City or town’
geoid	Filter the Place file to Layer = ‘City or town’.
Find the city for the school using the notes above to lookup School Address.
Concatenate to ‘, WI’
Match the concatenated SchoolAddress.City = Place.Name to get the GEOID
Set to “ERROR” if not found
3 towns are not included in the places file. Asked Metopio to add them.
topic	‘FVDEHAAP’
stratification	See above notes
period	SCHOOL YEAR, but insert ‘20’ on the second year’s range. So 2023-24 becaomes 2023-2024
value	REMOVAL_COUNT



Validation Method
Step 1: For the most current year, manually mock up the expected Metopio load files using Excel pivot tables and vlookups to the lookup files.
Step 2: Compare the mock up to the output side by side with “true/false” comparisons on every column. “Pass” means that every cell matches. 
Step 3: For additional years, we assume that the results will follow the norm, so we do not do mock-ups for those. Instead, we check for new stratifications and errors in the lookups. 

Geo Layer	2023	2022	2021	2020	2019	2018
State						
Tri-County						
County						
Zip Code						
City or Town						

Step 4: Upload to Metopio to “unplublished” metric.
In the Administrator Tool, on the “Data” tab, under “Data Management”, click on “Upload Data”.
 
Click “Validate file (will not import yet)”
Scroll down on the list and click “Import Data” if there are no error messages:
 
Step 4: Spot Checks between Metopio and the source dashboard completed after loading the files.
If the Topic is not visible in the Atlas yet, we spot check from the Administrator tool. Click “Data” tab. Click “Explore Data” under “Data Management” (or Explore Data from the Topics entry). Spot check some of the values in the listed data.
Geo Layer	2023	2022	2021	2020	2019	2018
State						
Tri-County						
County						
Zip Code						
City or Town						

Step 5: March 2025 data load signed off by the FVDEX Executive Director on _______________________.
Step 6: Make data visible to public. In Administrator site, click “Data” tab and “Topics” under “Topic Management”. Edit and turn on Public View.
Step 7: Spot Check Metopio Dashboard to WISEDash. Check the map, chart, etc for new data added.
Step 8: Have requester review the topic
Step 9: Communicate the new topic to the Action Committee.
Code to format the files
This link has the Python code developed to format the Metopio upload files. Start with the “Readme” file.
https://github.com/shaazanaam/__wes_dataProcessor__.git
Authenticity

An "out-of-school suspension" (also known as "suspension") is a removal from school grounds imposed by the school administration for noncompliance with school district policies or rules; for threatening to destroy school property; or for endangering the property, health, or safety of those at school. 
WISEdata is a multi-vendor, open data collection system that allows school districts, charter schools, and private schools participating in a parental Choice program to submit data to the Department of Public Instruction (DPI) from the student information system (SIS) vendor of their choice.
Comments

Hi Sarah Jean,

I’m working on loading the Disciplinary Action metric now. Unfortunately, this topic has three demographic layers and Metopio can only handle two. So we have some choices to make:

Proposed Name: # of Students Expelled or Suspended in

Here is a statewide example for gender:
Strat	Sub-Strat	Removal Type	Total Enrolled	Total Disciplined
Gender	Female	Expulsion with Services Offered	398216	182
Gender	Female	Expulsion without Services Offered	398216	127
Gender	Female	Out of School Suspension	398216	28073
Gender	Male	Out of School Suspension	424235	53976
Gender	Male	Expulsion without Services Offered	424235	183
Gender	Male	Expulsion with Services Offered	424235	288
Gender	Non-binary	Expulsion with Services Offered	353	1
Gender	Non-binary	Out of School Suspension	353	29
Gender	Unknown	Out of School Suspension	0	14


Here are our options:
1 – Add the three removal types to one total by demographic group. Pro: see all demographics easily who were disciplined. Con: Don’t know detail disciplines, but people could go to WISEdash for more details if needed. This is the option I prefer, but will is it enough?
	
Public School K-12 Expelled or Suspended

Strat	Sub-Strat	Total Enrolled	Total Disciplined
Gender	Female	398216	28382
Gender	Male	424235	54447
Gender	Non-binary	353	30
Gender	Unknown	0	14

2 – Add each removal type as a separate topic by demographic group in addition to the total suggested above. Pro: see all demographics easily who were disciplined. Con: The  individual removal types can’t be viewed together.

	
Public School K-12 Expelled or Suspended
Public School K-12 Expelled with Svc Offer
Public School K-12 Expelled without Svc Offer
Public School K-12 Out of School Suspension

3 – Combine the current Strat and Sub-Strat values into one that sits under the removal type:

	Removal Type
		Strat + Sub-Strat

	Would look like this in stratifications:
		

