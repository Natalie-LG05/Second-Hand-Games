from flask import Blueprint, render_template, request, flash

"""also known as auth in vid"""
"""the file is a blueprint of the website - a blueprint means there are just a bunch of routes defined; helps organize"""

server_authorization = Blueprint('server_auth',__name__) #first argument is name of blueprint


@server_authorization.route('/login', methods=['GET','POST'])
def login():
    return render_template("login.html", boolean=True)

@server_authorization.route('/logout')
def logout():
    return "<p>logout</p>"

@server_authorization.route('/sign-up', methods=['GET','POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        firstName = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        if len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(firstName) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords do not match.', category='error')
        elif len(password1) < 7:
            flash('Password must be greater than 6 characters.', category='error')
        else:
            # add user to database
            flash('Account created!', category='success')

    return render_template("sign_up.html")