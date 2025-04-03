from flask import Flask

def web_creation():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'IDONTKNOWYET'

    from .Server_Routes import server_routes
    from .Server_authorization import server_authorization

    app.register_blueprint(server_routes,url_prefix='/')
    app.register_blueprint(server_authorization,url_prefix='/')
    

    return app