# 🚀 Deployment Guide - PythonAnywhere

## ✅ Prerequisites (Already Done)
- ✓ Code pushed to GitHub: https://github.com/shaazanaam/__PP9Transformation__
- ✓ App running locally on port 8001
- ✓ Settings configured for deployment

---

## 📋 **Step-by-Step Deployment Instructions**

### **Step 1: Create PythonAnywhere Account**

1. Go to: **https://www.pythonanywhere.com/registration/register/beginner/**
2. Create a **FREE** account (no credit card needed)
3. Choose a username (this will be your subdomain: `yourusername.pythonanywhere.com`)
4. Verify your email

---

### **Step 2: Clone Your Repository**

Once logged into PythonAnywhere:

1. Click on **"Consoles"** tab
2. Click **"Bash"** to open a new console
3. Run these commands:

```bash
# Clone your repository
git clone https://github.com/shaazanaam/__PP9Transformation__.git
cd __PP9Transformation__

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# (Enter your desired username, email, and password)

# Collect static files
python manage.py collectstatic --noinput
```

---

### **Step 3: Configure Web App**

1. Click on **"Web"** tab
2. Click **"Add a new web app"**
3. Choose **"Manual configuration"** (NOT Django wizard)
4. Select **Python 3.10**

---

### **Step 4: Configure WSGI File**

1. In the **"Web"** tab, scroll to **"Code"** section
2. Click on **WSGI configuration file** link (e.g., `/var/www/yourusername_pythonanywhere_com_wsgi.py`)
3. **Delete all contents** and replace with:

```python
import os
import sys

# Add your project directory to the sys.path
path = '/home/yourusername/__PP9Transformation__'  # CHANGE 'yourusername' to YOUR username
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variable for Django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'school_data_project.settings'

# Activate virtual environment
activate_this = '/home/yourusername/__PP9Transformation__/venv/bin/activate_this.py'  # CHANGE 'yourusername'
exec(open(activate_this).read(), {'__file__': activate_this})

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**IMPORTANT:** Replace `yourusername` with your actual PythonAnywhere username in 2 places!

4. Click **"Save"**

---

### **Step 5: Configure Virtual Environment Path**

1. Scroll down to **"Virtualenv"** section
2. Enter: `/home/yourusername/__PP9Transformation__/venv`  
   (Replace `yourusername` with your actual username)
3. Click the checkmark to save

---

### **Step 6: Configure Static Files**

1. Scroll down to **"Static files"** section
2. Add these mappings:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/yourusername/__PP9Transformation__/staticfiles` |
| `/media/` | `/home/yourusername/__PP9Transformation__/media` |

(Replace `yourusername` with your actual username)

---

### **Step 7: Reload Web App**

1. Scroll to top of **"Web"** tab
2. Click big green **"Reload yourusername.pythonanywhere.com"** button
3. Wait 10-20 seconds

---

### **Step 8: Test Your App**

1. Click on the link: **`yourusername.pythonanywhere.com`**
2. You should see your Django app!
3. Go to `/admin` to login with your superuser credentials
4. Go to `/data_processor/upload/` to test transformations

---

## 🌐 **Add Your GoDaddy Domain (Optional)**

### **In PythonAnywhere:**
1. Upgrade to **$5/month plan** (required for custom domains)
2. Go to **"Web"** tab → **"Add a new web app"**
3. Choose your GoDaddy domain

### **In GoDaddy:**
1. Go to your domain DNS settings
2. Add CNAME record:
   ```
   Type: CNAME
   Name: www
   Value: yourusername.pythonanywhere.com
   TTL: 600
   ```

---

## 🔧 **Common Issues and Solutions**

### **Issue: "Import Error" or "Module Not Found"**
**Solution:** Make sure virtual environment path is correct in Web tab

### **Issue: "Static files not loading"**
**Solution:** 
```bash
# In Bash console:
cd __PP9Transformation__
source venv/bin/activate
python manage.py collectstatic --noinput
```
Then reload web app

### **Issue: "Database is locked"**
**Solution:** SQLite works fine on free tier. If issues persist:
- Restart web app
- Or upgrade to MySQL (included in free tier)

### **Issue: Need to update code**
**Solution:**
```bash
# In Bash console:
cd __PP9Transformation__
git pull origin main
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
```
Then reload web app

---

## 📊 **Upload Your Data**

Once deployed:

1. Login to admin: `yourusername.pythonanywhere.com/admin`
2. Go to data upload page: `yourusername.pythonanywhere.com/data_processor/upload/`
3. Upload your CSV files:
   - Enrollment data
   - Removal data
   - Forward Exam data
   - School addresses
   - County GEOIDs
   - Stratifications
4. Run transformations
5. Download results

---

## 💰 **Free Tier Limits**

- **Storage:** Limited disk space (~500MB)
- **Database:** SQLite included, or MySQL for larger datasets
- **Domain:** Free subdomain (yourusername.pythonanywhere.com)
- **Custom Domain:** Requires $5/month upgrade

---

## ✅ **You're Done!**

Your Django app is now live and accessible to your client at:
**`https://yourusername.pythonanywhere.com`**

Share this URL with your client to demonstrate the application!

---

## 🆘 **Need Help?**

If you encounter issues:
1. Check error logs in PythonAnywhere: **"Web"** tab → **"Log files"**
2. Check PythonAnywhere forums: https://www.pythonanywhere.com/forums/
3. Or let me know the error and I'll help troubleshoot!
