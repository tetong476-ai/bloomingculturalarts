import json
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()
HOME_WORK_ITEMS = [
    "Khmer Cultural Arts",
    "School Partnerships",
    "Inclusive Education",
    "Corporate Sponsorship",
    "Creative Workshop",
    "Community Engagement",
]


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
    def is_video(self):
        return urlparse(self.image_url or "").path.lower().endswith((".mp4", ".webm"))

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
            "is_video": self.is_video,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GalleryItem(db.Model):
    __tablename__ = "gallery_items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False, default="Events")
    image_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    CATEGORIES = ["Traditional Dance", "Music", "Painting", "Events"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "category": self.category,
            "image_url": self.image_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RecentActivity(db.Model):
    __tablename__ = "recent_activities"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False, default="Events")
    image_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    CATEGORIES = GalleryItem.CATEGORIES

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
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


class Donation(db.Model):
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    donor_name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="USD")
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    transaction_reference = db.Column(db.String(200), nullable=True)
    proof_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


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
            "home_work_enabled": "true",
            "home_work_heading": "HOW WE WORK",
            "home_work_items_json": json.dumps(HOME_WORK_ITEMS, ensure_ascii=False),
            "home_work_commitment_heading": "OUR NON-PROFIT COMMITMENT",
            "home_work_commitment_text": "100% Youth-Led & Community Driven",
            "home_work_button_text": "Request Proposal",
            "collaborate_enabled": "true",
            "collaborate_eyebrow": "Collaborate With Us",
            "collaborate_heading": "Ready to Empower Cambodian Youth & Culture Together?",
            "collaborate_text": "Partner with Blooming Cultural Arts or sponsor our upcoming cultural gala, 'A Night of Possibility,' to create lasting educational opportunities.",
            "collaborate_button_text": "Partner With Us",
            "collaborate_background_highlight": "#fff8f8",
            "collaborate_background_midpoint": "#fce8ec",
            "collaborate_background_edge": "#f9e1e6",
            "about_text": "Blooming Cultural Arts (BCA) is a youth-led initiative dedicated to celebrating cultural arts while creating meaningful opportunities for children in Cambodia through education, creativity, and community engagement. BCA seeks to bring together culture, the arts, and community to create positive, memorable experiences and support opportunities for children to learn, grow, and thrive.",
            "about_hero_title": "Our Story",
            "about_hero_subtitle": "The Belief That Started It All — Every Child Deserves Opportunity",
            "about_hero_image_url": "/static/uploads/hero-speech-therapy-room.png",
            "mission_statement": "Our mission is to promote and celebrate cultural arts in the Kingdom of Cambodia, while supporting children's education and well-being. Through art, community engagement, and fundraising initiatives, we hope to raise awareness, create meaningful connections, and give back to children who need support and opportunities to thrive.",
            "goals_json": '["Promote and celebrate cultural arts.", "Support children\'s education and well-being.", "Create opportunities through art, culture, and community engagement.", "Organize unforgettable events for educational initiatives."]',
            "about_closing_heading": "Celebrating Culture, Nurturing Creativity",
            "about_closing_text": "When cultural arts bloom in young hearts, every child gains the confidence to dream, create, and thrive.",
            "partners_heading": "Our Partners",
            "sponsors_heading": "Our Sponsors",
            "partner_1_name": "Cambodian partner organization",
            "partner_1_image_url": "/static/images/partner-cambodian-organization.png",
            "partner_2_name": "Blooming Cultural Arts",
            "partner_2_image_url": "/static/images/bca-footer-logo.png",
            "partner_3_name": "The Rabbit School",
            "partner_3_image_url": "/static/images/partner-rabbit-school.png",
            "partner_4_name": "Additional partner",
            "partner_4_image_url": "",
            "facebook_url": "https://web.facebook.com/BloomingCulturalArts",
            "tiktok_url": "https://www.tiktok.com/@blooming.cultural.arts",
            "khqr_image_url": "https://via.placeholder.com/300x300/EBB838/ffffff?text=KHQR+Code",
            "contact_email": "info@bloomingculturalarts.org",
            "phone": "+855 12 345 678",
            "address": "Phnom Penh, Cambodia",
        }
        legacy_defaults = {
            "about_text": "Blooming Cultural Arts (BCA) is a Cambodian youth-led initiative dedicated to supporting children's education through the power of cultural arts. We believe that every child deserves access to their cultural heritage and the transformative power of artistic expression.",
            "mission_statement": "To empower Cambodian youth by preserving and promoting traditional cultural arts, fostering creativity, and building pathways to education and opportunity.",
            "goals_json": '["Provide free arts education to underprivileged children", "Preserve and promote Khmer traditional arts", "Build community through cultural exchange", "Create sustainable income for local artists", "Reach 10,000 students by 2026"]',
        }
        for key, value in defaults.items():
            setting = SiteSetting.query.filter_by(key=key).first()
            if not setting:
                db.session.add(SiteSetting(key=key, value=value))
            elif key in legacy_defaults and setting.value == legacy_defaults[key]:
                setting.value = value

        for number in range(1, 5):
            for field in ("name", "image_url"):
                sponsor_key = f"sponsor_{number}_{field}"
                if SiteSetting.query.filter_by(key=sponsor_key).first():
                    continue
                partner_setting = SiteSetting.query.filter_by(
                    key=f"partner_{number}_{field}"
                ).first()
                db.session.add(SiteSetting(
                    key=sponsor_key,
                    value=partner_setting.value if partner_setting else "",
                ))

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
