
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
import os

mail = Mail()
db = SQLAlchemy()
DB_NAME = 'database.sqlite3'


def create_database():
    db.create_all()
    print('Database Created')

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.',1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'hbnwdvbn ajnbsjn ahe'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'secondhandgames3@gmail.com'
    app.config['MAIL_PASSWORD'] = 'iybk acuz oibx mzre'
    app.config['MAIL_DEFAULT_SENDER'] = 'secondhandgames3@gmail.com'

    mail.init_app(app)
    
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max upload size
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

    db.init_app(app)

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('404.html')

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    from .views import views
    from .auth import auth
    from .admin import admin
    from .models import User, Cart, Product, Order

    app.register_blueprint(views, url_prefix='/') # localhost:5000/about-us
    app.register_blueprint(auth, url_prefix='/') # localhost:5000/auth/change-password
    app.register_blueprint(admin, url_prefix='/')

    with app.app_context():
        create_database()

    return app
