# 🌸 Blooming Cultural Arts (BCA) - Web Application

A complete, production-ready dynamic web application with a full CMS/Admin Panel for **Blooming Cultural Arts**, a Cambodian youth-led initiative supporting children's education through cultural arts.

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python + Flask |
| Database | PostgreSQL + SQLAlchemy ORM |
| Frontend | HTML5 + Tailwind CSS (CDN) + Vanilla JS |
| Auth | Flask-Login (session-based) |
| File Uploads | Local storage (`/static/uploads/`) |

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- PostgreSQL 14+
- pip

### 2. Clone & Setup

```bash
git clone <repo-url>
cd bca_app

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your values
notepad .env   # Windows
nano .env      # Linux/macOS
```

Required `.env` values:
```env
FLASK_SECRET_KEY=your-very-secret-key-change-this
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/bca_db
FLASK_ENV=development
FLASK_DEBUG=1
```

### 4. Create PostgreSQL Database

```sql
-- In psql or pgAdmin:
CREATE DATABASE bca_db;
```

### 5. Initialize Database & Run

```bash
# Tables are auto-created on first run
python app.py
```

The app will:
- Create all database tables automatically
- Seed default site settings
- Create a default admin user
- Start on http://localhost:5000

---

## 🔐 Default Admin Credentials

| Field | Value |
|-------|-------|
| URL | http://localhost:5000/login |
| Username | `admin` |
| Password | `admin123` |

> ⚠️ **Change the password immediately** after first login via Admin Panel → Change Password tab.

---

## 📁 Project Structure

```
bca_app/
├── app.py                  # Flask app factory, all routes
├── database.py             # SQLAlchemy models & seed data
├── auth.py                 # Login/logout blueprint
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── static/
│   ├── css/custom.css        # BCA brand styles
│   ├── js/main.js            # Public site JS (gallery, modals)
│   ├── js/admin.js           # Admin panel JS
│   └── uploads/              # Uploaded images (auto-created)
└── templates/
    ├── base.html             # Base template
    ├── index.html            # Public homepage
    ├── login.html            # Admin login page
    └── admin/
        ├── dashboard.html    # Admin control panel (settings + stats)
        ├── campaigns.html    # Campaign CRUD manager
        └── gallery.html      # Gallery CRUD manager
```

---

## 🌐 Public Website Sections

| Section | URL | Description |
|---------|-----|-------------|
| Homepage | `/` | Full public site |
| Hero | `/#home` | Dynamic heading + CTA |
| About | `/#about` | Mission & goals |
| Campaigns | `/#campaigns` | Active fundraising campaigns |
| Gallery | `/#gallery` | Filterable photo gallery |
| Impact | `/#impact` | Stats counter |
| Contact | `/#contact` | Contact info |

## 🔧 Admin Panel Pages

| Page | URL | Description |
|------|-----|-------------|
| Login | `/login` | Admin authentication |
| Dashboard | `/admin` | Site settings + stats |
| Campaigns | `/admin/campaigns` | Full campaign CRUD |
| Gallery | `/admin/gallery` | Full gallery CRUD |

---

## 📚 REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Public site settings |
| GET | `/api/campaigns` | Active campaigns |
| GET | `/api/gallery` | Gallery items (filterable by `?category=`) |
| GET | `/api/stats` | Impact statistics |

---

## 🚀 Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Environment Variables for Production

```env
FLASK_ENV=production
FLASK_DEBUG=0
FLASK_SECRET_KEY=<strong-random-key>
DATABASE_URL=postgresql://user:pass@host:5432/bca_db
```

### Nginx Reverse Proxy (example)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/bca_app/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🎨 Brand Colors

| Name | Hex | Usage |
|------|-----|-------|
| Soft Pink | `#FDF2F4` | Background sections |
| Warm Gold | `#EBB838` | Buttons, accents |
| Sage Green | `#6B8F71` | Details, hero overlay |
| Dark | `#2D2D2D` | Text |

---

## 🛡️ Security Notes

- Change the default admin password immediately after setup
- Set a strong `FLASK_SECRET_KEY` in production
- File uploads are validated by extension (png, jpg, jpeg, gif, webp, svg)
- Max upload size: 16 MB
- All admin routes require authentication + admin role
- Passwords are hashed using Werkzeug's `generate_password_hash`

---

*Built with ❤️ for Blooming Cultural Arts - Empowering Cambodian youth through cultural arts.*
