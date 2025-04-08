from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager

db = SQLAlchemy()
DB_NAME = "database.db"


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'IDONTKNOWYET'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    from .Server_routes import server_routes
    from .Server_authorization import server_authorization

    app.register_blueprint(server_routes,url_prefix='/')
    app.register_blueprint(server_authorization,url_prefix='/')

    from .Server_models import User, Note

    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_server_route = 'Server_authorization.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app

def create_database(app):
    """checks if database exists; if it doesn't it creates database"""
    if not path.exists('SHG_Code_Stuffs/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')