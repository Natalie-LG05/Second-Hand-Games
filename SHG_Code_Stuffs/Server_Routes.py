from flask import Blueprint, render_template
from flask_login import login_required, current_user

"""also known as views from vid"""
"""the file is a blueprint of the website - a blueprint means there are just a bunch of routes defined; helps organize"""

server_routes = Blueprint('server_routes',__name__) #first argument is name of blueprint

@server_routes.route('/')
@login_required
def home():
    """function runs when going to / route"""
    return render_template("home.html")