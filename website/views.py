from flask import Blueprint, render_template, flash, redirect, request, jsonify, url_for, current_app as app, session
from flask import current_app as app
from .models import Product, Cart, Order, Wishlist
from flask_login import login_required, current_user
from . import db
from intasend import APIService
import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from PIL import Image, ImageOps
from flask_mail import Message, Mail
from . import mail
import base64
from .forms import ShopItemsForm


views = Blueprint('views', __name__)

API_PUBLISHABLE_KEY = 'YOUR_PUBLISHABLE_KEY'

API_TOKEN = 'YOUR_API_TOKEN'


def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.',1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


@views.route('/')
def home():

    items = Product.query.filter_by(flash_sale=True)

    return render_template('home.html', items=items, cart=Cart.query.filter_by(user_id=current_user.id).all()
                           if current_user.is_authenticated else [])


@views.route('/contact', methods=['GET','POST'])
def contact():
    if request.method =='POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message_body = request.form.get('message')
        
        # creates a message object
        msg = Message(f"Contact Us Message from {name}", sender = email, recipients=["secondhandgames3@gmail.com"], body=f"From: {name} <{email}\n\n{message_body}")

        try:
            #sends email
            mail.send(msg)
            flash('Your message has been sent successfully!', category='success')
        except Exception as e:
            flash(f"An error occurred while sending the message: {e}", category='error')
    

        return redirect(url_for('views.contact'))
    return render_template('contact.html')


@views.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    username = request.form.get('username')
    email = request.form.get('email')
    phone_number = request.form.get('phone_number')

    current_user.username = username
    current_user.email = email
    current_user.phone_number = phone_number

    try:
        db.session.commit()
        flash('Profile updated successuflly!', category='success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating profile: {e}", category='error')
    
    return redirect(url_for('views.profile'))


@views.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')

    if not current_user._password:
        flash("you dont' have a password set yet. Please contact support.", category='error')
        return redirect(url_for('views.profile'))
    # verifies password hash
    if current_user.verify_password(current_password):
        if new_password:
            current_user.password = new_password
            try:
                db.session.commit()
                flash(f'Password updated successfully!', category='success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating password: {e}', category='error')
        else:
            flash("New password can't be empty", category='error')
    else:
        flash('Current password is incorrect.', category='error')
    
    return redirect(url_for('views.profile'))


@views.route('/view_product/<int:product_id>')
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    #adding product to session's recently viewed list with a max of 5 products showing
    recently_viewed = session.get('recently_viewed', [])

    if product_id not in recently_viewed:
        if len(recently_viewed) >= 5:
            recently_viewed.pop(0) # removes oldest if more than 5
        recently_viewed.append(product_id)
        session['recently_viewed'] = recently_viewed

    return render_template('product_details.html', product=product)


@views.route('/add-item',methods=['GET','POST'])
@login_required
def add_item():
    if request.method == 'POST':
        print('form_submitted!')

        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')

        # At least one of these fields is required to have data; if both have data than:
        #   an uploaded image takes priority over an image taken with the user's camera via the website's interface
        image_file = request.files.get('image_file')
        image_data = request.form.get('camera_input')

        if (not name) or (not price) or ((not image_file) and (not image_data)):  # requires that image_file or image_data is entered
            flash('Name, price, and image are required.',category='error')
            return render_template('add_shop_items.html', user=current_user)

        image_bytes = None  # Defaults to None: when an image is uploaded
        if image_file:
            # If an image was uploaded, check that it is a valid file
            if not allowed_file(image_file.filename):
                flash('Invalid image format', category='error')
        elif not image_file:
            # If no image was uploaded, then use the image data from the image taken with the user's camera
            image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)

        # Determine the filepath for the uploaded/taken image to be saved to within the server
        # First, count the number of files in the uploads folder; the filename will be one higher than that amount
        #   to ensure unique file names
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        num_files = len(files)

        filename = secure_filename(f'image_upload_{num_files+1}')
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        if image_file:
            image_file.save(filepath)
        elif image_bytes:
            # If no image was uploaded, then an image was taken using the user's camera
            # Writes the image data bytes to the file
            with open(filepath, 'w') as _:
                pass
            with open(filepath, 'wb') as f:
                f.write(image_bytes)

        try:
            price = float(price)

            # Code to generate the AI price rating goes around here
            # price_rating = 0

            new_item = Product(
                product_name=name,
                current_price=price,
                description=description,
                image=filename,  # saves the name not the path,
                user_id=current_user.id,

                # Once the DB models are updated, the price rating will go here
                # price_rating=price_rating,
            )
            db.session.add(new_item)
            db.session.commit()
            flash('Item added successfully!', category='success')
            return redirect(url_for('views.shop'))
        except ValueError:
            flash('Invalid price format', category='error')

    return render_template('add_shop_items.html', user=current_user)


@views.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    #fetches recently viewed form session
    recently_viewed_ids = session.get('recently_viewed', [])
    recently_viewed = Product.query.filter(Product.id.in_(recently_viewed_ids)).all()

    if request.method == 'POST':
        image = request.files.get('profile_picture')
        if image and image.filename != '' and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            upload_folder = os.path.join(app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, unique_filename)
            image.save(filepath)
            image = Image.open(filepath)
            image = ImageOps.fit(image, (400,400), method=Image.Resampling.LANCZOS) # resizes uploaded pic while not distorting it
            image.save(filepath) # overwrite original file with resized image

            current_user.profile_picture = unique_filename # updates profile pic
            db.session.commit()

            flash('Profile picture updated!', 'success')
        else:
            flash('No image file selected or image format is invalid.', 'error')
        
        return redirect(url_for('views.profile'))
    
    return render_template('profile.html', user=current_user, orders=orders, recently_viewed=recently_viewed)


@views.route('/shop')
def shop():
    products = Product.query.all()
    return render_template('shop.html', products=products)


@views.route('/product/<int:product_id>')
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_details.html', product=product)


@views.route('/add-to-cart/<int:item_id>', methods=['POST'])
@login_required
def add_to_cart(item_id):
    product = Product.query.get(item_id)
    if product:
        cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product.id).first()
        if cart_item:
            cart_item.quantity +=1
        else:
            cart_item = Cart(user_id=current_user.id, product_id=product.id, quantity=1)
            db.session.add(cart_item)

        db.session.commit()
        print(f"added to cart: {product.product_name}")
        
    return redirect(url_for('views.show_cart'))


@views.route('/debug_cart')
def debug_cart():
    cart_items = Cart.query.all()
    return "<br>".join([f"User: {item.user_id}, Product: {item.product_id}, Quantity: {item.quantity}" for item in cart_items])


@views.route('/cart')
@login_required
def show_cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    return render_template('cart.html', cart=cart_items)


@views.route('/pluscart')
@login_required
def plus_cart():
    if request.method == 'GET':
        cart_id = request.args.get('cart_id')
        cart_item = Cart.query.get(cart_id)
        cart_item.quantity = cart_item.quantity + 1
        db.session.commit()

        cart = Cart.query.filter_by(user_id=current_user.id).all()

        amount = 0

        for item in cart:
            amount += item.product.current_price * item.quantity

        data = {
            'quantity': cart_item.quantity,
            'amount': amount,
            'total': amount + 200
        }

        return jsonify(data)


@views.route('/minuscart')
@login_required
def minus_cart():
    if request.method == 'GET':
        cart_id = request.args.get('cart_id')
        cart_item = Cart.query.get(cart_id)
        cart_item.quantity = cart_item.quantity - 1
        db.session.commit()

        cart = Cart.query.filter_by(user_id=current_user.id).all()

        amount = 0

        for item in cart:
            amount += item.product.current_price * item.quantity

        data = {
            'quantity': cart_item.quantity,
            'amount': amount,
            'total': amount + 200
        }

        return jsonify(data)


@views.route('removecart')
@login_required
def remove_cart():
    if request.method == 'GET':
        cart_id = request.args.get('cart_id')
        cart_item = Cart.query.get(cart_id)
        db.session.delete(cart_item)
        db.session.commit()

        cart = Cart.query.filter_by(user_id=current_user.id).all()

        amount = 0

        for item in cart:
            amount += item.product.current_price * item.quantity

        data = {
            'quantity': cart_item.quantity,
            'amount': amount,
            'total': amount + 200
        }

        return jsonify(data)


@views.route('/add-to-wishlist/<int:product_id>', methods=['POST'])
@login_required
def add_to_wishlist(product_id):
    product = Product.query.get_or_404(product_id)

    # checking whether product is in wishlist already or not
    existing_wishlist_item = Wishlist.query.filter_by(user_id=current_user.id, product_id=product.id).first()

    if not existing_wishlist_item:
        new_wishlist_item = Wishlist(user_id=current_user.id, product_id=product.id)
        db.session.add(new_wishlist_item)
        db.session.commit()
        flash('Product added to your wishlist!')
    else:
        flash('This product is already in your wishlist.', category='warning')

    return redirect(url_for('views.product_details', product_id=product.id))


@views.route('/wishlist')
@login_required
def wishlist():
    wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).all()
    return render_template('wishlist.html', wishlist=wishlist_items)


@views.route('/remove-from-wishlist/<int:item_id>', methods=['POST'])
@ login_required
def remove_from_wishlist(item_id):
    wishlist_item = Wishlist.query.get_or_404(item_id)

    if wishlist_item.user_id == current_user.id:
        db.session.delete(wishlist_item)
        db.session.commit()
        flash('Product removed from your wishlist', category='success')
    else:
        flash('You are not authorized to remove this item', category='danger')

    return redirect(url_for('views.wishlist'))


@views.route('/place-order')
@login_required
def place_order():
    customer_cart = Cart.query.filter_by(user_id=current_user.id)
    if customer_cart:
        try:
            total = 0
            for item in customer_cart:
                total += item.product.current_price * item.quantity

            service = APIService(token=API_TOKEN, publishable_key=API_PUBLISHABLE_KEY, test=True)
            create_order_response = service.collect.mpesa_stk_push(phone_number='YOUR_NUMBER ', email=current_user.email,
                                                                   amount=total + 200, narrative='Purchase of goods')

            for item in customer_cart:
                new_order = Order()
                new_order.quantity = item.quantity
                new_order.price = item.product.current_price
                new_order.status = create_order_response['invoice']['state'].capitalize()
                new_order.payment_id = create_order_response['id']

                new_order.product_id = item.product_id
                new_order.user_id = item.user_id

                db.session.add(new_order)

                product = Product.query.get(item.product_id)

                product.in_stock -= item.quantity

                db.session.delete(item)

                db.session.commit()

            flash('Order Placed Successfully')

            return redirect('/orders')
        except Exception as e:
            print(e)
            flash('Order not placed')
            return redirect('/')
    else:
        flash('Your cart is Empty')
        return redirect('/')


@views.route('/orders')
@login_required
def order():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('orders.html', orders=orders)


@views.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_query = request.form.get('search')
        items = Product.query.filter(Product.product_name.ilike(f'%{search_query}%')).all()
        return render_template('search.html', items=items, cart=Cart.query.filter_by(user_id=current_user.id).all()
                           if current_user.is_authenticated else [])

    return render_template('search.html')