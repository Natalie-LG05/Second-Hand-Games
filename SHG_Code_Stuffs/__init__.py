from flask import Flask

def web_creation():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'IDONTKNOWYET'

    return app