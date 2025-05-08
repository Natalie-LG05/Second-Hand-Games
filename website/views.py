from flask import Blueprint, session, render_template, flash, redirect, request, jsonify, url_for, current_app as app, session
from flask import current_app as app
from .models import Product, Cart, Order, Wishlist, OrderItem
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
import cloudinary.uploader
import openai
import base64
import requests
import re
import json
from io import BytesIO



views = Blueprint('views', __name__)

API_PUBLISHABLE_KEY = 'YOUR_PUBLISHABLE_KEY'

API_TOKEN = 'YOUR_API_TOKEN'

cloudinary.config(
    cloud_name=("dtqohanvi"),
    api_key=("437918759626267"),
    api_secret=("ZJ8f3zSFYoMk7q__4EUy6gOf3yQ")
)

openai.api_key = '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'

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.',1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def cloudinary_url_to_base64(cloudinary_url):
    response = requests.get(cloudinary_url)
    if response.status_code == 200:
        content_type = response.headers.get("Content-Type", "image/png")
        encoded = base64.b64encode(response.content).decode("utf-8")
        return f"data:{content_type};base64,{encoded}"
    else:
        raise Exception("Failed to fetch image from Cloudinary")

@views.route('/')
def home():
    items = Product.query.all()
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


@views.route('/buy_now/<int:product_id>', methods=['POST'])
@login_required
def buy_now(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity',1))
    total = product.price * quantity
    # create order
    new_order = Order(user_id=current_user.id, total_price=total)
    db.session.add(new_order)
    db.session.commit()
    # add orderitem
    order_item = OrderItem(
        order_id=new_order.id,
        product_id=product.id,
        quantity=quantity,
        price=product.price
    )
    db.session.add(order_item)
    db.session.commit()

    flash('Order placed successfully!', 'success')
    return redirect(url_for('views.order'))


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
        image_file = request.files.get('image')
        image_data = request.form.get('camera_input')

        print(f"name: {name}, price: {price}, image file: {image_file}, image data: {image_data}")
        if (not name) or (not price) or ((not image_file) and (not image_data)):  # requires that image_file or image_data is entered
            flash('Name, price, and image are required.',category='error')
            return render_template('add_shop_items.html', user=current_user)

        image_bytes = None  # Defaults to None: when an image is uploaded
        if image_file:
            # If an image was uploaded, check that it is a valid file
            if not allowed_file(image_file.filename):
                flash('Invalid image format', category='error')
                return render_template('add_shop_items.html', user=current_user)
        elif image_data:
            image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)

        # Determine the filepath for the uploaded/taken image to be saved to within the server
        # First, count the number of files in the uploads folder; the filename will be one higher than that amount
        #   to ensure unique file names
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        num_files = len(files)

        filename = secure_filename(f'image_upload_{num_files+1}.png')
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

            # Upload to Cloudinary
            cloud_result = cloudinary.uploader.upload(filepath)
            image_url = cloud_result.get("secure_url")

            new_item = Product(
                product_name=name,
                price=price,
                description=description,
                image=filename,
                user_id=current_user.id,

            )
            db.session.add(new_item)
            db.session.commit()

            flash('Item added successfully!', category='success')
            return redirect(url_for('views.shop'))

        except ValueError:
            flash('Invalid price format', category='error')
        except Exception as e:
            flash(f'Error saving item: {str(e)}', category='error')

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
            amount += item.product.price * item.quantity

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
            amount += item.product.price * item.quantity

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
            amount += item.product.price * item.quantity

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
    try:
        # Fetch cart items from the database, not from the session
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()

        if not cart_items:
            flash('Your cart is empty. Please add items to your cart before placing an order.', 'warning')
            return redirect(url_for('views.show_cart'))

        order = Order(user_id=current_user.id)

        total_price = 0
        for cart_item in cart_items:
            product = Product.query.get(cart_item.product_id)
            if product:  # Ensure product exists
                order_item = OrderItem(
                    product_id=product.id,
                    quantity=cart_item.quantity,
                    price=product.price
                )
                order.order_items.append(order_item)
                total_price += product.price * cart_item.quantity

        # Set the total price for the order
        order.total_price = total_price
        db.session.add(order)

        # Commit the transaction to the database
        db.session.commit()

        # Optionally clear the cart after placing the order
        db.session.query(Cart).filter_by(user_id=current_user.id).delete()
        db.session.commit()

        flash('Your order has been placed successfully!', 'success')
        return redirect(url_for('views.order'))  # Redirect to order confirmation page or orders page

    except Exception as e:
        db.session.rollback()  # Rollback in case of an error
        flash(f"Error placing order: {str(e)}", 'danger')
        return redirect(url_for('views.show_cart'))  # Redirect back to cart page if error occurs


@views.route('/orders')
@login_required
def order():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.timestamp.desc()).all()
    return render_template('orders.html', orders=orders)


@views.route('/order_history')
@login_required
def order_history(): 
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.timestamp.desc()).all()
    return render_template('order_history.html',orders=orders)         


@views.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_query = request.form.get('search')
        items = Product.query.filter(Product.product_name.ilike(f'%{search_query}%')).all()
        return render_template('search.html', items=items, cart=Cart.query.filter_by(user_id=current_user.id).all()
                           if current_user.is_authenticated else [])

    return render_template('search.html')

@views.route('/analyze-image', methods=['POST'])
@login_required
def analyze_image():
    if request.method == 'POST':
        # Get the uploaded image file
        image_file = request.files.get('image')
        
        if not image_file:
            return jsonify({'error': 'No image uploaded'}), 400

        # Save the image temporarily
        filename = secure_filename(image_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        image_file.save(filepath)

        # Upload image to Cloudinary
        cloud_result = cloudinary.uploader.upload(filepath)
        image_url = cloud_result.get("secure_url")

        # Convert image to base64 for OpenAI
        base64_image = cloudinary_url_to_base64(image_url)

        # Call OpenAI to analyze the image
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Please analyze this image and return only a valid JSON object in this exact format:\n"
                            "{\n"
                            '  "console_brand": "PlayStation, Xbox, Nintendo, Sega, etc. or None",\n'
                            '  "console_model": "Model name if visible, e.g., PS5, Xbox Series X",\n'
                            '  "game_name": "The name of any visible or identifiable video game",\n'
                            '  "controller_type": "Description or type of any visible controller",\n'
                            '  "visible_text": "Any text visible on screen, disc, or console",\n'
                            '  "number_of_consoles": 0,\n'
                            '  "estimated_price": "Estimated resale or retail price in USD as a number, e.g., 399.99"\n'
                            "}\n"
                            "Return only valid JSON. No explanation or markdown formatting."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": base64_image}
                            }
                        ]
                    }
                ],
                max_tokens=1000  # <-- You were missing this comma before
            )

            raw_content = response.choices[0].message.content.strip()
            match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            ai_data = json.loads(match.group()) if match else {}

            return jsonify(ai_data)

        except Exception as e:
            return jsonify({'error': f'Error processing image: {str(e)}'}), 500
