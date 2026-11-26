import os
import json
import re
from urllib.parse import urlparse
from flask import (
    Flask, Blueprint, Request, render_template, request, redirect,
    url_for, flash, jsonify, send_from_directory
)
from flask_login import LoginManager, login_required, current_user
from sqlalchemy import inspect, text
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from database import (
    db, SiteSetting, Campaign, GalleryItem, RecentActivity, Stat, Donation, User,
    HOME_WORK_ITEMS, seed_defaults,
)
from auth import auth_bp, admin_required

load_dotenv()

CAMPAIGN_UPLOAD_LIMIT = 500 * 1024 * 1024
COLLABORATE_BACKGROUND_DEFAULTS = {
    "collaborate_background_highlight": "#fff8f8",
    "collaborate_background_midpoint": "#fce8ec",
    "collaborate_background_edge": "#f9e1e6",
}
ABOUT_BACKGROUND_DEFAULTS = {
    "about_background_color": "#f7f5f4",
    "mission_background_color": "#687c4a",
    "goals_background_color": "#f6b7be",
}
HEX_COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{6}\Z")


class CampaignUploadRequest(Request):
    @property
    def max_content_length(self):
        if self.endpoint in {"admin.campaign_create", "admin.campaign_edit"}:
            return CAMPAIGN_UPLOAD_LIMIT
        return super().max_content_length


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app():
    app = Flask(__name__)
    app.request_class = CampaignUploadRequest

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

    @app.errorhandler(413)
    def campaign_upload_too_large(error):
        if request.endpoint in {"admin.campaign_create", "admin.campaign_edit"}:
            flash("Campaign photo/video must be smaller than 500 MB.", "error")
            return redirect(url_for("admin.campaigns"))
        return error

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

    def allowed_file(filename, extensions=None):
        extensions = ALLOWED_EXTENSIONS if extensions is None else extensions
        return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions

    def get_settings():
        rows = SiteSetting.query.all()
        return {r.key: r.value for r in rows}

    def get_home_work_items(settings):
        raw_items = settings.get("home_work_items_json")
        if raw_items is None:
            return HOME_WORK_ITEMS.copy()
        try:
            items = json.loads(raw_items)
        except (TypeError, json.JSONDecodeError) as error:
            app.logger.warning("Invalid home work items setting: %s", error)
            return HOME_WORK_ITEMS.copy()
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            app.logger.warning("Home work items setting must be a list of strings.")
            return HOME_WORK_ITEMS.copy()
        return [item.strip() for item in items if item.strip()]

    def get_partners(settings, include_empty=False):
        defaults = [
            ("Cambodian partner organization", "/static/images/partner-cambodian-organization.png"),
            ("Blooming Cultural Arts", "/static/images/bca-footer-logo.png"),
            ("The Rabbit School", "/static/images/partner-rabbit-school.png"),
            ("Additional partner", ""),
        ]
        partners = []
        for number, (name, default_image_url) in enumerate(defaults, start=1):
            image_url = settings.get(f"partner_{number}_image_url", default_image_url)
            partner_name = settings.get(f"partner_{number}_name", name)
            if image_url is None:
                image_url = default_image_url
            if partner_name is None:
                partner_name = name
            if image_url or include_empty:
                partners.append({
                    "number": number,
                    "name": partner_name,
                    "image_url": image_url,
                })
        return partners

    def get_sponsors(settings, include_empty=False):
        partners = get_partners(settings, include_empty=True)
        sponsors = []
        for partner in partners:
            number = partner["number"]
            sponsor_name = settings.get(f"sponsor_{number}_name", partner["name"])
            image_url = settings.get(
                f"sponsor_{number}_image_url", partner["image_url"]
            )
            if sponsor_name is None:
                sponsor_name = partner["name"]
            if image_url is None:
                image_url = partner["image_url"]
            if image_url or include_empty:
                sponsors.append({
                    "number": number,
                    "name": sponsor_name,
                    "image_url": image_url,
                })
        return sponsors

    def set_setting(key, value):
        s = SiteSetting.query.filter_by(key=key).first()
        if s:
            s.value = value
        else:
            s = SiteSetting(key=key, value=value)
            db.session.add(s)
        db.session.commit()

    def save_upload(file_field_name, extensions=None):
        """Save uploaded file; return relative URL or None."""
        f = request.files.get(file_field_name)
        if f and f.filename and allowed_file(f.filename, extensions):
            filename = secure_filename(f.filename)
            # Avoid collisions
            import time
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(time.time())}{ext}"
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            return f"/static/uploads/{filename}"
        return None

    def save_campaign_media():
        media_file = request.files.get("image_file")
        if not media_file or not media_file.filename:
            return None

        campaign_media_extensions = ALLOWED_EXTENSIONS | {"mp4", "webm"}
        if not allowed_file(media_file.filename, campaign_media_extensions):
            raise ValueError("Upload an image or an MP4/WebM video.")
        return save_upload("image_file", campaign_media_extensions)

    # -----------------------------------------------------------------------
    # Public routes
    # -----------------------------------------------------------------------

    def render_public_page(about_page=False):
        settings = get_settings()
        for key, default_color in COLLABORATE_BACKGROUND_DEFAULTS.items():
            color = settings.get(key, default_color)
            if not HEX_COLOR_PATTERN.fullmatch(color or ""):
                app.logger.warning("Invalid Collaborate background color setting: %s", key)
                color = default_color
            settings[key] = color.lower()
        for key, default_color in ABOUT_BACKGROUND_DEFAULTS.items():
            color = settings.get(key, default_color)
            if not HEX_COLOR_PATTERN.fullmatch(color or ""):
                app.logger.warning("Invalid About background color setting: %s", key)
                color = default_color
            settings[key] = color.lower()
        campaigns = Campaign.query.filter_by(is_active=True).order_by(Campaign.created_at.desc()).all()
        gallery = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
        recent_activities = RecentActivity.query.order_by(RecentActivity.created_at.desc()).all()
        stats = Stat.query.all()
        goals = []
        try:
            goals = json.loads(settings.get("goals_json", "[]"))
        except Exception:
            pass
        if not goals:
            goals = [
                "Promote and celebrate cultural arts.",
                "Support children's education and well-being.",
                "Create opportunities through art, culture, and community engagement.",
                "Organize unforgettable events for educational initiatives.",
            ]
        return render_template(
            "index.html",
            settings=settings,
            campaigns=campaigns,
            featured_campaign=campaigns[0] if campaigns else None,
            gallery=gallery,
            recent_activities=recent_activities,
            stats=stats,
            goals=goals,
            home_work_items=get_home_work_items(settings),
            partners=get_partners(settings),
            sponsors=get_sponsors(settings),
            about_page=about_page,
        )

    @app.route("/")
    def index():
        return render_public_page()

    @app.route("/campaigns")
    def campaigns_page():
        settings = get_settings()
        return render_template(
            "campaigns.html",
            settings=settings,
            campaigns=Campaign.query.filter_by(is_active=True)
            .order_by(Campaign.created_at.desc())
            .all(),
            partners=get_partners(settings),
            sponsors=get_sponsors(settings),
        )

    @app.route("/join")
    def join_page():
        settings = get_settings()
        return render_template(
            "join.html",
            settings=settings,
            partners=get_partners(settings),
            sponsors=get_sponsors(settings),
        )

    @app.route("/about")
    def about():
        return render_public_page(about_page=True)

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

    @app.route("/api/recent-activities")
    def api_recent_activities():
        items = RecentActivity.query.order_by(RecentActivity.created_at.desc()).all()
        return jsonify([item.to_dict() for item in items])

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

    @app.route("/api/donations", methods=["POST"])
    def create_donation():
        donor_name = request.form.get("donor_name", "").strip()
        proof_file = request.files.get("proof_file")

        if not donor_name:
            return jsonify({"error": "Your name is required."}), 400
        if not proof_file or not proof_file.filename:
            return jsonify({"error": "Payment receipt is required."}), 400
        if not allowed_file(proof_file.filename):
            return jsonify({"error": "Payment receipt must be an image file."}), 400
        proof_url = save_upload("proof_file")
        if not proof_url:
            return jsonify({"error": "The payment receipt could not be uploaded."}), 400

        donation = Donation(
            donor_name=donor_name,
            amount=0,
            currency="N/A",
            proof_url=proof_url,
        )
        db.session.add(donation)
        db.session.commit()
        return jsonify({"message": "Donation saved successfully.", "id": donation.id}), 201

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
        try:
            goals_raw = "\n".join(json.loads(settings.get("goals_json", "[]")))
        except Exception:
            goals_raw = ""
        campaigns_count = Campaign.query.count()
        gallery_count = GalleryItem.query.count()
        recent_activities_count = RecentActivity.query.count()
        stats_count = Stat.query.count()
        stats = Stat.query.all()
        return render_template(
            "admin/dashboard.html",
            settings=settings,
            campaigns_count=campaigns_count,
            gallery_count=gallery_count,
            recent_activities_count=recent_activities_count,
            stats_count=stats_count,
            stats=stats,
            goals_raw=goals_raw,
            home_work_items_raw="\n".join(get_home_work_items(settings)),
            partners=get_partners(settings, include_empty=True),
            sponsors=get_sponsors(settings, include_empty=True),
        )

    # --- Site Settings ---

    @admin_bp.route("/settings", methods=["GET", "POST"])
    @login_required
    @admin_required
    def settings():
        if request.method == "POST":
            social_links = {
                "facebook_url": request.form.get("facebook_url", "").strip(),
                "tiktok_url": request.form.get("tiktok_url", "").strip(),
            }
            for platform, link in social_links.items():
                parsed_link = urlparse(link)
                if link and (
                    parsed_link.scheme not in {"http", "https"} or not parsed_link.netloc
                ):
                    platform_name = "TikTok" if platform == "tiktok_url" else "Facebook"
                    flash(
                        f"{platform_name} link must be a valid HTTP or HTTPS URL.",
                        "error",
                    )
                    return redirect(url_for("admin.dashboard") + "#tab-settings")

            text_keys = [
                "site_title", "hero_heading", "hero_subheading",
                "contact_email", "phone", "address", "khqr_image_url",
                "facebook_url", "tiktok_url",
                "home_work_heading", "home_work_commitment_heading",
                "home_work_commitment_text", "home_work_button_text",
            ]
            for key in text_keys:
                val = social_links[key] if key in social_links else request.form.get(key, "")
                set_setting(key, val)

            work_items = [
                line.strip()
                for line in request.form.get("home_work_items_raw", "").splitlines()
                if line.strip()
            ]
            set_setting("home_work_items_json", json.dumps(work_items, ensure_ascii=False))
            set_setting(
                "home_work_enabled",
                "true" if request.form.get("home_work_enabled") == "true" else "false",
            )

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
            return redirect(url_for("admin.dashboard") + "#tab-settings")

        current_settings = get_settings()
        goals_raw = ""
        try:
            goals_raw = "\n".join(json.loads(current_settings.get("goals_json", "[]")))
        except Exception:
            pass
        return render_template(
            "admin/dashboard.html",
            settings=current_settings,
            goals_raw=goals_raw,
            home_work_items_raw="\n".join(get_home_work_items(current_settings)),
            partners=get_partners(current_settings, include_empty=True),
            sponsors=get_sponsors(current_settings, include_empty=True),
            active_tab="settings",
        )

    @admin_bp.route("/home-work-banner/delete", methods=["POST"])
    @login_required
    @admin_required
    def home_work_banner_delete():
        set_setting("home_work_enabled", "false")
        flash("The How We Work banner was removed from the website.", "info")
        return redirect(url_for("admin.dashboard") + "#tab-settings")

    @admin_bp.route("/collaborate-settings", methods=["POST"])
    @login_required
    @admin_required
    def collaborate_settings():
        background_colors = {}
        for key in COLLABORATE_BACKGROUND_DEFAULTS:
            color = request.form.get(key, "").strip()
            if not HEX_COLOR_PATTERN.fullmatch(color):
                flash("Please choose valid Collaborate background colors.", "error")
                return redirect(url_for("admin.dashboard") + "#tab-collaborate")
            background_colors[key] = color.lower()

        for key in (
            "collaborate_eyebrow",
            "collaborate_heading",
            "collaborate_text",
            "collaborate_button_text",
        ):
            set_setting(key, request.form.get(key, "").strip())
        for key, color in background_colors.items():
            set_setting(key, color)
        set_setting(
            "collaborate_enabled",
            "true" if request.form.get("collaborate_enabled") == "true" else "false",
        )
        flash("Collaborate section updated successfully!", "success")
        return redirect(url_for("admin.dashboard") + "#tab-collaborate")

    @admin_bp.route("/collaborate/delete", methods=["POST"])
    @login_required
    @admin_required
    def collaborate_delete():
        set_setting("collaborate_enabled", "false")
        flash("The Collaborate section was removed from the website.", "info")
        return redirect(url_for("admin.dashboard") + "#tab-collaborate")

    @admin_bp.route("/about-settings", methods=["POST"])
    @login_required
    @admin_required
    def about_settings():
        background_colors = {}
        for key in ABOUT_BACKGROUND_DEFAULTS:
            color = request.form.get(key, "").strip()
            if not HEX_COLOR_PATTERN.fullmatch(color):
                flash("Please choose valid About page background colors.", "error")
                return redirect(url_for("admin.dashboard") + "#tab-about")
            background_colors[key] = color.lower()

        about_images = {
            "about_hero_image_url": "about_hero_image_file",
            "about_image_url": "about_image_file",
            "mission_image_url": "mission_image_file",
            "goals_image_url": "goals_image_file",
        }
        for file_field in about_images.values():
            media_file = request.files.get(file_field)
            if media_file and media_file.filename and not allowed_file(media_file.filename):
                flash("About page photos must be valid image files.", "error")
                return redirect(url_for("admin.dashboard") + "#tab-about")

        set_setting("about_hero_title", request.form.get("about_hero_title", ""))
        set_setting("about_hero_subtitle", request.form.get("about_hero_subtitle", ""))
        set_setting("about_text", request.form.get("about_text", ""))
        set_setting("mission_statement", request.form.get("mission_statement", ""))
        set_setting("about_closing_heading", request.form.get("about_closing_heading", ""))
        set_setting("about_closing_text", request.form.get("about_closing_text", ""))
        for key, color in background_colors.items():
            set_setting(key, color)
        goals_raw = request.form.get("goals_raw", "")
        goals_list = [goal.strip() for goal in goals_raw.splitlines() if goal.strip()]
        set_setting("goals_json", json.dumps(goals_list))

        for setting_key, file_field in about_images.items():
            image_url = save_upload(file_field) or request.form.get(setting_key, "").strip()
            if image_url:
                set_setting(setting_key, image_url)

        flash("About Us content updated successfully!", "success")
        return redirect(url_for("admin.dashboard") + "#tab-about")

    @admin_bp.route("/partners-settings", methods=["POST"])
    @login_required
    @admin_required
    def partners_settings():
        return save_logo_group("partner", "Partners", "partners_heading")

    @admin_bp.route("/sponsors-settings", methods=["POST"])
    @login_required
    @admin_required
    def sponsors_settings():
        return save_logo_group("sponsor", "Sponsors", "sponsors_heading")

    def save_logo_group(prefix, group_name, heading_key):
        image_fields = [
            f"{prefix}_{number}_image_file" for number in range(1, 5)
        ]
        for number, file_field in enumerate(image_fields, start=1):
            if request.form.get(f"{prefix}_{number}_delete") == "1":
                continue
            media_file = request.files.get(file_field)
            if media_file and media_file.filename and not allowed_file(media_file.filename):
                flash(f"{group_name} logos must be valid image files.", "error")
                return redirect(url_for("admin.dashboard") + "#tab-partners")

        set_setting(heading_key, request.form.get(heading_key, "").strip())
        for number, file_field in enumerate(image_fields, start=1):
            if request.form.get(f"{prefix}_{number}_delete") == "1":
                set_setting(f"{prefix}_{number}_name", "")
                set_setting(f"{prefix}_{number}_image_url", "")
                continue

            set_setting(
                f"{prefix}_{number}_name",
                request.form.get(f"{prefix}_{number}_name", "").strip(),
            )
            image_url = save_upload(file_field) or request.form.get(
                f"{prefix}_{number}_image_url", ""
            ).strip()
            if image_url:
                set_setting(f"{prefix}_{number}_image_url", image_url)

        flash(f"{group_name} updated successfully!", "success")
        return redirect(url_for("admin.dashboard") + "#tab-partners")

    # --- Campaigns ---

    @admin_bp.route("/campaigns")
    @login_required
    @admin_required
    def campaigns():
        all_campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
        return render_template(
            "admin/campaigns.html",
            campaigns=all_campaigns,
            settings=get_settings(),
        )

    @admin_bp.route("/campaigns/create", methods=["POST"])
    @login_required
    @admin_required
    def campaign_create():
        title = request.form.get("title", "").strip()
        if not title:
            flash("Campaign title is required.", "error")
            return redirect(url_for("admin.campaigns"))

        try:
            image_url = save_campaign_media() or request.form.get("image_url", "").strip()
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("admin.campaigns"))

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
        try:
            new_media = save_campaign_media() or request.form.get("image_url", "").strip()
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("admin.campaigns"))

        c.title = request.form.get("title", c.title).strip()
        c.description = request.form.get("description", c.description)
        c.target_amount = float(request.form.get("target_amount", c.target_amount) or 0)
        c.raised_amount = float(request.form.get("raised_amount", c.raised_amount) or 0)
        c.is_active = request.form.get("is_active") == "on"
        if new_media:
            c.image_url = new_media
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
        return render_template(
            "admin/gallery.html",
            items=items,
            categories=GalleryItem.CATEGORIES,
            settings=get_settings(),
            manager_title="Gallery",
            collection_path="/admin/gallery",
            delete_endpoint="admin.gallery_delete",
        )

    @admin_bp.route("/recent-activities")
    @login_required
    @admin_required
    def recent_activities_admin():
        items = RecentActivity.query.order_by(RecentActivity.created_at.desc()).all()
        return render_template(
            "admin/gallery.html",
            items=items,
            categories=RecentActivity.CATEGORIES,
            settings=get_settings(),
            manager_title="Recent Activities",
            collection_path="/admin/recent-activities",
            delete_endpoint="admin.recent_activity_delete",
        )

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
        item = GalleryItem(
            title=title or "Untitled",
            description=request.form.get("description", "").strip(),
            category=category,
            image_url=image_url,
        )
        db.session.add(item)
        db.session.commit()
        flash("Gallery item added!", "success")
        return redirect(url_for("admin.gallery"))

    @admin_bp.route("/recent-activities/create", methods=["POST"])
    @login_required
    @admin_required
    def recent_activity_create():
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "Events")
        image_url = save_upload("image_file") or request.form.get("image_url", "")
        if not image_url:
            flash("An image file or URL is required.", "error")
            return redirect(url_for("admin.recent_activities_admin"))
        item = RecentActivity(
            title=title or "Untitled",
            description=request.form.get("description", "").strip(),
            category=category,
            image_url=image_url,
        )
        db.session.add(item)
        db.session.commit()
        flash("Recent activity added!", "success")
        return redirect(url_for("admin.recent_activities_admin"))

    @admin_bp.route("/gallery/<int:gid>/edit", methods=["POST"])
    @login_required
    @admin_required
    def gallery_edit(gid):
        item = GalleryItem.query.get_or_404(gid)
        item.title = request.form.get("title", item.title).strip() or item.title
        item.description = request.form.get("description", item.description or "").strip()
        item.category = request.form.get("category", item.category)
        new_img = save_upload("image_file") or request.form.get("image_url", "")
        if new_img:
            item.image_url = new_img
        db.session.commit()
        flash("Gallery item updated!", "success")
        return redirect(url_for("admin.gallery"))

    @admin_bp.route("/recent-activities/<int:gid>/edit", methods=["POST"])
    @login_required
    @admin_required
    def recent_activity_edit(gid):
        item = RecentActivity.query.get_or_404(gid)
        item.title = request.form.get("title", item.title).strip() or item.title
        item.description = request.form.get("description", item.description or "").strip()
        item.category = request.form.get("category", item.category)
        new_img = save_upload("image_file") or request.form.get("image_url", "")
        if new_img:
            item.image_url = new_img
        db.session.commit()
        flash("Recent activity updated!", "success")
        return redirect(url_for("admin.recent_activities_admin"))

    @admin_bp.route("/gallery/<int:gid>/delete", methods=["POST"])
    @login_required
    @admin_required
    def gallery_delete(gid):
        item = GalleryItem.query.get_or_404(gid)
        db.session.delete(item)
        db.session.commit()
        flash("Gallery item deleted.", "info")
        return redirect(url_for("admin.gallery"))

    @admin_bp.route("/recent-activities/<int:gid>/delete", methods=["POST"])
    @login_required
    @admin_required
    def recent_activity_delete(gid):
        item = RecentActivity.query.get_or_404(gid)
        db.session.delete(item)
        db.session.commit()
        flash("Recent activity deleted.", "info")
        return redirect(url_for("admin.recent_activities_admin"))

    # --- Donations ---

    @admin_bp.route("/donations")
    @login_required
    @admin_required
    def donations():
        donation_items = Donation.query.order_by(Donation.created_at.desc()).all()
        total_usd = sum(float(item.amount) for item in donation_items if item.currency == "USD")
        total_khr = sum(float(item.amount) for item in donation_items if item.currency == "KHR")
        return render_template(
            "admin/donations.html",
            donations=donation_items,
            total_usd=total_usd,
            total_khr=total_khr,
            settings=get_settings(),
        )

    @admin_bp.route("/donations/<int:did>/status", methods=["POST"])
    @login_required
    @admin_required
    def donation_status(did):
        donation = Donation.query.get_or_404(did)
        status = request.form.get("status", "").strip().lower()
        if status not in {"pending", "approved", "rejected"}:
            flash("Invalid donation status.", "error")
        else:
            donation.status = status
            db.session.commit()
            flash(f"Donation marked {status}.", "success")
        return redirect(url_for("admin.donations"))

    @admin_bp.route("/donations/<int:did>/delete", methods=["POST"])
    @login_required
    @admin_required
    def donation_delete(did):
        donation = Donation.query.get_or_404(did)
        db.session.delete(donation)
        db.session.commit()
        flash("Donation record deleted.", "info")
        return redirect(url_for("admin.donations"))

    # --- Stats ---

    @admin_bp.route("/stats")
    @login_required
    @admin_required
    def stats():
        return redirect(url_for("admin.dashboard") + "#tab-stats")

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
        return redirect(url_for("admin.dashboard") + "#tab-stats")

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
        return redirect(url_for("admin.dashboard") + "#tab-stats")

    @admin_bp.route("/stats/<int:sid>/delete", methods=["POST"])
    @login_required
    @admin_required
    def stat_delete(sid):
        s = Stat.query.get_or_404(sid)
        db.session.delete(s)
        db.session.commit()
        flash("Stat deleted.", "info")
        return redirect(url_for("admin.dashboard") + "#tab-stats")

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
        donation_columns = {column["name"] for column in inspect(db.engine).get_columns("donations")}
        if "proof_url" not in donation_columns:
            db.session.execute(text("ALTER TABLE donations ADD COLUMN proof_url VARCHAR(500)"))
            db.session.commit()
        if "status" not in donation_columns:
            db.session.execute(text("ALTER TABLE donations ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'"))
            db.session.commit()
        gallery_columns = {
            column["name"] for column in inspect(db.engine).get_columns("gallery_items")
        }
        if "description" not in gallery_columns:
            db.session.execute(text("ALTER TABLE gallery_items ADD COLUMN description TEXT"))
            db.session.commit()
        activity_migration = SiteSetting.query.filter_by(key="recent_activities_migrated_v1").first()
        if not activity_migration:
            # Keep the current homepage highlights when splitting them from Gallery.
            for gallery_item in GalleryItem.query.order_by(GalleryItem.created_at.desc()).limit(3).all():
                db.session.add(RecentActivity(
                    title=gallery_item.title,
                    description=gallery_item.description,
                    category=gallery_item.category,
                    image_url=gallery_item.image_url,
                    created_at=gallery_item.created_at,
                ))
            db.session.add(SiteSetting(key="recent_activities_migrated_v1", value="true"))
            db.session.commit()
        seed_defaults(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="0.0.0.0", port=5000)
