# Quick Deployment Checklist

## ✅ Pre-Deployment (DONE)
- [x] Code pushed to GitHub
- [x] Settings configured
- [x] App tested locally

## 📝 Do These Steps Now:

### 1. Create Account (5 min)
- Go to: https://www.pythonanywhere.com/registration/register/beginner/
- Sign up (FREE, no credit card)
- Pick username → becomes: `yourusername.pythonanywhere.com`

### 2. Setup Code (10 min)
Open Bash console, paste these commands:
```bash
git clone https://github.com/shaazanaam/__PP9Transformation__.git
cd __PP9Transformation__
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 3. Configure Web App (5 min)
- Web tab → "Add new web app" → Manual → Python 3.10
- Click WSGI file → Delete all → Paste from DEPLOYMENT_GUIDE.md
- Change `yourusername` to YOUR username (2 places)
- Save

### 4. Set Paths (2 min)
- Virtualenv: `/home/yourusername/__PP9Transformation__/venv`
- Static files: `/static/` → `/home/yourusername/__PP9Transformation__/staticfiles`
- Media files: `/media/` → `/home/yourusername/__PP9Transformation__/media`

### 5. Launch (1 min)
- Click green "Reload" button
- Visit: `yourusername.pythonanywhere.com`

## 🎉 Total Time: ~20 minutes

## 🔗 Share with Client:
`https://yourusername.pythonanywhere.com`

## Full guide: DEPLOYMENT_GUIDE.md
