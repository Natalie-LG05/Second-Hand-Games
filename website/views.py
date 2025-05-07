from flask import Blueprint, session, render_template, flash, redirect, request, jsonify, url_for, current_app as app
from .models import Product, Cart, Order
from flask_login import login_required, current_user
from . import db
from intasend import APIService
import os
from werkzeug.utils import secure_filename
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

    items = Product.query.filter_by(flash_sale=True)

    return render_template('home.html', items=items, cart=Cart.query.filter_by(user_id=current_user.id).all()
                           if current_user.is_authenticated else [])

@views.route('/add-item', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')
        image_file = request.files.get('image')

        if not name or not price or not image_file:
            flash('Name, price, and image are required.', category='error')
            return render_template('add_shop_items.html', user=current_user)

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            image_file.save(filepath)

            try:
                price = float(price)
                previous_price_input = request.form.get('previous_price')
                previous_price = float(previous_price_input) if previous_price_input else None

                # Upload to Cloudinary (still needed for product display/storage)
                cloud_result = cloudinary.uploader.upload(filepath)
                image_url = cloud_result.get("secure_url")

                new_item = Product(
                    product_name=name,
                    current_price=price,
                    description=description,
                    image=filename,
                    user_id=current_user.id,
                    previous_price=previous_price
                )
                db.session.add(new_item)
                db.session.commit()

                flash('Item added successfully!', category='success')
                return redirect(url_for('views.shop'))

            except ValueError:
                flash('Invalid price format', category='error')
            except Exception as e:
                flash(f'Error saving item: {str(e)}', category='error')
        else:
            flash('Invalid image format', category='error')

    return render_template('add_shop_items.html', user=current_user)

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
