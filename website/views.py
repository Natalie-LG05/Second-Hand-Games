from flask import Blueprint, render_template, flash, redirect, request, jsonify, url_for, current_app as app
from .models import Product, Cart, Order
from flask_login import login_required, current_user
from . import db
from intasend import APIService
import os
from werkzeug.utils import secure_filename


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

@views.route('/add-item',methods=['GET','POST'])
@login_required
def add_item():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')
        image_file = request.files.get('image')

        if not name or not price or not image_file:
            flash('Name, price, and image are required.',category='error')
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
                new_item = Product(
                    product_name=name,
                    current_price=price,
                    description=description,
                    image=filename, # saves the name not the path,
                    user_id=current_user.id,
                    previous_price=previous_price
                )
                db.session.add(new_item)
                db.session.commit()
                flash('Item aded successfully!', category='success')
                return redirect(url_for('views.shop'))
            except ValueError:
                flash('Invalid price format', category='error')

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
    return render_template('shop_items.html', product=product)

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