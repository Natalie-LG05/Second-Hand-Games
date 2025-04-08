from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
DB_NAME = "database.db"


def web_creation():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'IDONTKNOWYET'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    from .Server_routes import server_routes
    from .Server_authorization import server_authorization

    app.register_blueprint(server_routes,url_prefix='/')
    app.register_blueprint(server_authorization,url_prefix='/')
    

    return app