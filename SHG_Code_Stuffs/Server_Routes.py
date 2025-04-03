from flask import Blueprint


"""the file is a blueprint of the website - a blueprint means there are just a bunch of routes defined; helps organize"""

server_routes = Blueprint('server_routes',__name__) #first argument is name of blueprint

@server_routes.route('/')
def homepage():
    """function runs when going to / route"""
    return "<h1>Test</h1>"