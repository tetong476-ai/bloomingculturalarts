from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()


class SiteSetting(db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SiteSetting {self.key}>"


class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_amount = db.Column(db.Numeric(12, 2), default=0)
    raised_amount = db.Column(db.Numeric(12, 2), default=0)
    image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def progress_percent(self):
        if self.target_amount and float(self.target_amount) > 0:
            pct = (float(self.raised_amount) / float(self.target_amount)) * 100
            return min(round(pct, 1), 100)
        return 0

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "target_amount": float(self.target_amount or 0),
            "raised_amount": float(self.raised_amount or 0),
            "progress_percent": self.progress_percent,
            "image_url": self.image_url or "",
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GalleryItem(db.Model):
    __tablename__ = "gallery_items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False, default="Events")
    image_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    CATEGORIES = ["Traditional Dance", "Music", "Painting", "Events"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "image_url": self.image_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Stat(db.Model):
    __tablename__ = "stats"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(200), nullable=False)
    value = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(100), nullable=True, default="⭐")

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "value": self.value,
            "icon": self.icon or "⭐",
        }


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="admin")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


def seed_defaults(app):
    """Seed the database with default site settings and sample data."""
    with app.app_context():
        # Default site settings
        defaults = {
            "site_title": "Blooming Cultural Arts",
            "site_logo": "",
            "hero_heading": "Empowering Cambodian Youth Through Cultural Arts",
            "hero_subheading": "Blooming Cultural Arts nurtures children's creativity, preserves Khmer heritage, and builds brighter futures through traditional dance, music, and visual arts.",
            "about_text": "Blooming Cultural Arts (BCA) is a Cambodian youth-led initiative dedicated to supporting children's education through the power of cultural arts. We believe that every child deserves access to their cultural heritage and the transformative power of artistic expression.",
            "mission_statement": "To empower Cambodian youth by preserving and promoting traditional cultural arts, fostering creativity, and building pathways to education and opportunity.",
            "goals_json": '["Provide free arts education to underprivileged children", "Preserve and promote Khmer traditional arts", "Build community through cultural exchange", "Create sustainable income for local artists", "Reach 10,000 students by 2026"]',
            "khqr_image_url": "https://via.placeholder.com/300x300/EBB838/ffffff?text=KHQR+Code",
            "contact_email": "info@bloomingculturalarts.org",
            "phone": "+855 12 345 678",
            "address": "Phnom Penh, Cambodia",
        }
        for key, value in defaults.items():
            if not SiteSetting.query.filter_by(key=key).first():
                db.session.add(SiteSetting(key=key, value=value))

        # Default stats
        if not Stat.query.first():
            stats = [
                Stat(label="Students Reached", value="5,000+", icon="🎓"),
                Stat(label="Partner Schools", value="50+", icon="🏫"),
                Stat(label="Cultural Programs", value="30+", icon="🎭"),
                Stat(label="Volunteer Artists", value="200+", icon="🎨"),
            ]
            db.session.add_all(stats)

        # Default admin user
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)

        db.session.commit()
