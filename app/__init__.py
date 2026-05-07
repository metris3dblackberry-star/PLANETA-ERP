from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'solvior-secret-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///solvior.db')
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB max upload

    # SMTP / SendGrid-compatible email settings
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', '')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes', 'on')
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'false').lower() in ('1', 'true', 'yes', 'on')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

    # Optional Mailgun fallback
    app.config['MAILGUN_API_KEY'] = os.environ.get('MAILGUN_API_KEY', '')
    app.config['MAILGUN_DOMAIN'] = os.environ.get('MAILGUN_DOMAIN', '')
    app.config['MAILGUN_FROM'] = os.environ.get('MAILGUN_FROM', 'noreply@solvior.ee')

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Kérjük jelentkezzen be!'

    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprints
    from app.views.auth import auth_bp
    from app.views.main import main_bp
    from app.views.projects import projects_bp
    from app.views.clients import clients_bp
    from app.views.subcontractors import subcontractors_bp
    from app.views.invoices import invoices_bp
    from app.views.reports import reports_bp
    from app.views.inventory import inventory_bp
    from app.views.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(subcontractors_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()
        # Auto-migrate: add pdf columns to invoices if they don't exist yet
        try:
            from sqlalchemy import text, inspect as sa_inspect
            inspector = sa_inspect(db.engine)
            if inspector.has_table('invoices'):
                existing = {c['name'] for c in inspector.get_columns('invoices')}
                dialect = db.engine.dialect.name
                blob_type = 'BYTEA' if dialect == 'postgresql' else 'BLOB'
                with db.engine.connect() as conn:
                    if 'pdf_data' not in existing:
                        conn.execute(text(f'ALTER TABLE invoices ADD COLUMN pdf_data {blob_type}'))
                    if 'pdf_filename' not in existing:
                        conn.execute(text('ALTER TABLE invoices ADD COLUMN pdf_filename VARCHAR(255)'))
                    conn.commit()
        except Exception:
            pass  # fresh install: create_all handles it

    return app
