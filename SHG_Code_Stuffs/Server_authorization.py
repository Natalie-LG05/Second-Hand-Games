from flask import Blueprint


"""the file is a blueprint of the website - a blueprint means there are just a bunch of routes defined; helps organize"""

server_authorization = Blueprint('server_auth',__name__) #first argument is name of blueprint

@server_authorization.route('/login')
def login():
    return "<p>Login</p>"

@server_authorization.route('/logout')
def logout():
    return "<p>logout</p>"

@server_authorization.route('/sign-up')
def sign_up():
    return "<p>Sign Up</p>"