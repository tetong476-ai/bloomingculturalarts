import os
import json
from flask import (
    Flask, Blueprint, render_template, request, redirect,
    url_for, flash, jsonify, send_from_directory
)
from flask_login import LoginManager, login_required, current_user
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from database import db, SiteSetting, Campaign, GalleryItem, Stat, User, seed_defaults
from auth import auth_bp, admin_required

load_dotenv()

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app():
    app = Flask(__name__)

    # Config
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "postgresql://postgres:password@localhost:5432/bca_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Extensions
    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprints
    app.register_blueprint(auth_bp)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def get_settings():
        rows = SiteSetting.query.all()
        return {r.key: r.value for r in rows}

    def set_setting(key, value):
        s = SiteSetting.query.filter_by(key=key).first()
        if s:
            s.value = value
        else:
            s = SiteSetting(key=key, value=value)
            db.session.add(s)
        db.session.commit()

    def save_upload(file_field_name):
        """Save uploaded file; return relative URL or None."""
        f = request.files.get(file_field_name)
        if f and f.filename and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            # Avoid collisions
            import time
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(time.time())}{ext}"
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            return f"/static/uploads/{filename}"
        return None

    # -----------------------------------------------------------------------
    # Public routes
    # -----------------------------------------------------------------------

    @app.route("/")
    def index():
        settings = get_settings()
        campaigns = Campaign.query.filter_by(is_active=True).order_by(Campaign.created_at.desc()).all()
        gallery = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
        stats = Stat.query.all()
        goals = []
        try:
            goals = json.loads(settings.get("goals_json", "[]"))
        except Exception:
            pass
        return render_template(
            "index.html",
            settings=settings,
            campaigns=campaigns,
            gallery=gallery,
            stats=stats,
            goals=goals,
        )

    # -----------------------------------------------------------------------
    # Public JSON APIs (used by frontend JS)
    # -----------------------------------------------------------------------

    @app.route("/api/campaigns")
    def api_campaigns():
        campaigns = Campaign.query.filter_by(is_active=True).order_by(Campaign.created_at.desc()).all()
        return jsonify([c.to_dict() for c in campaigns])

    @app.route("/api/gallery")
    def api_gallery():
        category = request.args.get("category")
        q = GalleryItem.query
        if category and category != "All":
            q = q.filter_by(category=category)
        items = q.order_by(GalleryItem.created_at.desc()).all()
        return jsonify([i.to_dict() for i in items])

    @app.route("/api/stats")
    def api_stats():
        return jsonify([s.to_dict() for s in Stat.query.all()])

    @app.route("/api/settings")
    def api_settings():
        safe_keys = [
            "site_title", "site_logo", "hero_heading", "hero_subheading",
            "about_text", "mission_statement", "goals_json",
            "khqr_image_url", "contact_email", "phone", "address",
        ]
        settings = get_settings()
        return jsonify({k: settings.get(k, "") for k in safe_keys})

    # -----------------------------------------------------------------------
    # Admin blueprint
    # -----------------------------------------------------------------------

    admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

    @admin_bp.route("/")
    @admin_bp.route("/dashboard")
    @login_required
    @admin_required
    def dashboard():
        settings = get_settings()
        campaigns_count = Campaign.query.count()
        gallery_count = GalleryItem.query.count()
        stats_count = Stat.query.count()
        return render_template(
            "admin/dashboard.html",
            settings=settings,
            campaigns_count=campaigns_count,
            gallery_count=gallery_count,
            stats_count=stats_count,
        )

    # --- Site Settings ---

    @admin_bp.route("/settings", methods=["GET", "POST"])
    @login_required
    @admin_required
    def settings():
        if request.method == "POST":
            text_keys = [
                "site_title", "hero_heading", "hero_subheading",
                "about_text", "mission_statement", "contact_email",
                "phone", "address", "khqr_image_url",
            ]
            for key in text_keys:
                val = request.form.get(key, "")
                set_setting(key, val)

            # Goals (textarea, one per line -> JSON array)
            goals_raw = request.form.get("goals_raw", "")
            goals_list = [g.strip() for g in goals_raw.splitlines() if g.strip()]
            set_setting("goals_json", json.dumps(goals_list))

            # Logo upload or URL
            logo_url = save_upload("logo_file")
            if not logo_url:
                logo_url = request.form.get("site_logo", "")
            if logo_url:
                set_setting("site_logo", logo_url)

            # KHQR upload
            khqr_url = save_upload("khqr_file")
            if khqr_url:
                set_setting("khqr_image_url", khqr_url)

            flash("Site settings updated successfully!", "success")
            return redirect(url_for("admin.settings"))

        current_settings = get_settings()
        goals_raw = ""
        try:
            goals_raw = "\n".join(json.loads(current_settings.get("goals_json", "[]")))
        except Exception:
            pass
        return render_template("admin/dashboard.html", settings=current_settings, goals_raw=goals_raw, active_tab="settings")

    # --- Campaigns ---

    @admin_bp.route("/campaigns")
    @login_required
    @admin_required
    def campaigns():
        all_campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
        return render_template("admin/campaigns.html", campaigns=all_campaigns)

    @admin_bp.route("/campaigns/create", methods=["POST"])
    @login_required
    @admin_required
    def campaign_create():
        title = request.form.get("title", "").strip()
        if not title:
            flash("Campaign title is required.", "error")
            return redirect(url_for("admin.campaigns"))

        image_url = save_upload("image_file") or request.form.get("image_url", "")
        c = Campaign(
            title=title,
            description=request.form.get("description", ""),
            target_amount=float(request.form.get("target_amount", 0) or 0),
            raised_amount=float(request.form.get("raised_amount", 0) or 0),
            image_url=image_url,
            is_active=request.form.get("is_active") == "on",
        )
        db.session.add(c)
        db.session.commit()
        flash("Campaign created!", "success")
        return redirect(url_for("admin.campaigns"))

    @admin_bp.route("/campaigns/<int:cid>/edit", methods=["POST"])
    @login_required
    @admin_required
    def campaign_edit(cid):
        c = Campaign.query.get_or_404(cid)
        c.title = request.form.get("title", c.title).strip()
        c.description = request.form.get("description", c.description)
        c.target_amount = float(request.form.get("target_amount", c.target_amount) or 0)
        c.raised_amount = float(request.form.get("raised_amount", c.raised_amount) or 0)
        c.is_active = request.form.get("is_active") == "on"
        new_img = save_upload("image_file") or request.form.get("image_url", "")
        if new_img:
            c.image_url = new_img
        db.session.commit()
        flash("Campaign updated!", "success")
        return redirect(url_for("admin.campaigns"))

    @admin_bp.route("/campaigns/<int:cid>/delete", methods=["POST"])
    @login_required
    @admin_required
    def campaign_delete(cid):
        c = Campaign.query.get_or_404(cid)
        db.session.delete(c)
        db.session.commit()
        flash("Campaign deleted.", "info")
        return redirect(url_for("admin.campaigns"))

    @admin_bp.route("/campaigns/<int:cid>/toggle", methods=["POST"])
    @login_required
    @admin_required
    def campaign_toggle(cid):
        c = Campaign.query.get_or_404(cid)
        c.is_active = not c.is_active
        db.session.commit()
        return jsonify({"is_active": c.is_active})

    # --- Gallery ---

    @admin_bp.route("/gallery")
    @login_required
    @admin_required
    def gallery():
        items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
        return render_template("admin/gallery.html", items=items, categories=GalleryItem.CATEGORIES)

    @admin_bp.route("/gallery/create", methods=["POST"])
    @login_required
    @admin_required
    def gallery_create():
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "Events")
        image_url = save_upload("image_file") or request.form.get("image_url", "")
        if not image_url:
            flash("An image file or URL is required.", "error")
            return redirect(url_for("admin.gallery"))
        item = GalleryItem(title=title or "Untitled", category=category, image_url=image_url)
        db.session.add(item)
        db.session.commit()
        flash("Gallery item added!", "success")
        return redirect(url_for("admin.gallery"))

    @admin_bp.route("/gallery/<int:gid>/edit", methods=["POST"])
    @login_required
    @admin_required
    def gallery_edit(gid):
        item = GalleryItem.query.get_or_404(gid)
        item.title = request.form.get("title", item.title).strip() or item.title
        item.category = request.form.get("category", item.category)
        new_img = save_upload("image_file") or request.form.get("image_url", "")
        if new_img:
            item.image_url = new_img
        db.session.commit()
        flash("Gallery item updated!", "success")
        return redirect(url_for("admin.gallery"))

    @admin_bp.route("/gallery/<int:gid>/delete", methods=["POST"])
    @login_required
    @admin_required
    def gallery_delete(gid):
        item = GalleryItem.query.get_or_404(gid)
        db.session.delete(item)
        db.session.commit()
        flash("Gallery item deleted.", "info")
        return redirect(url_for("admin.gallery"))

    # --- Stats ---

    @admin_bp.route("/stats")
    @login_required
    @admin_required
    def stats():
        all_stats = Stat.query.all()
        return render_template("admin/dashboard.html", stats=all_stats, active_tab="stats")

    @admin_bp.route("/stats/create", methods=["POST"])
    @login_required
    @admin_required
    def stat_create():
        s = Stat(
            label=request.form.get("label", "").strip(),
            value=request.form.get("value", "").strip(),
            icon=request.form.get("icon", "⭐").strip(),
        )
        db.session.add(s)
        db.session.commit()
        flash("Stat added!", "success")
        return redirect(url_for("admin.dashboard") + "#stats")

    @admin_bp.route("/stats/<int:sid>/edit", methods=["POST"])
    @login_required
    @admin_required
    def stat_edit(sid):
        s = Stat.query.get_or_404(sid)
        s.label = request.form.get("label", s.label).strip()
        s.value = request.form.get("value", s.value).strip()
        s.icon = request.form.get("icon", s.icon).strip()
        db.session.commit()
        flash("Stat updated!", "success")
        return redirect(url_for("admin.dashboard") + "#stats")

    @admin_bp.route("/stats/<int:sid>/delete", methods=["POST"])
    @login_required
    @admin_required
    def stat_delete(sid):
        s = Stat.query.get_or_404(sid)
        db.session.delete(s)
        db.session.commit()
        flash("Stat deleted.", "info")
        return redirect(url_for("admin.dashboard") + "#stats")

    # --- Change Password ---

    @admin_bp.route("/change-password", methods=["POST"])
    @login_required
    @admin_required
    def change_password():
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")
        if not current_user.check_password(current_pw):
            flash("Current password is incorrect.", "error")
        elif new_pw != confirm_pw:
            flash("New passwords do not match.", "error")
        elif len(new_pw) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash("Password changed successfully!", "success")
        return redirect(url_for("admin.dashboard"))

    app.register_blueprint(admin_bp)

    # Create tables and seed
    with app.app_context():
        db.create_all()
        seed_defaults(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="0.0.0.0", port=5000)
