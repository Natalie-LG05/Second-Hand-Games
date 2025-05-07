from . import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(100))
    _password = db.Column(db.String(150), nullable=True)

    cart_items = db.relationship('Cart', backref='user', lazy=True)
    orders = db.relationship('Order', backref=db.backref('user', lazy=True))
    products = db.relationship('Product', backref='user', lazy=True)
    wishlist = db.relationship('Wishlist', back_populates='user')
    profile_picture = db.Column(db.String(150), default='default.jpeg')

    # Extra stuff that isn't being used, but I'm leaving in in case we need the info in the future
    phone_number = db.Column(db.String(15), nullable=True)
    date_joined = db.Column(db.DateTime(), default=datetime.utcnow)

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute')

    @password.setter
    def password(self, password):
        self._password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self._password, password)

    def __str__(self):
        return '<User %r>' % self.username


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    image = db.Column(db.String(300), nullable=True)
    price_rating = db.Column(db.Float)

    # Extra stuff that isn't being used, but I'm leaving in in case we need the info in the future
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    in_stock = db.Column(db.Boolean, nullable=False, default=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __str__(self):
        return '<Product %r>' % self.product_name


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    product = db.relationship('Product', backref='cart_items')

    def __repr__(self):
        return '<Cart %r>' % self.id


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(100), nullable=False)
    payment_id = db.Column(db.String(1000), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    def __str__(self):
        return '<Order %r>' % self.id
    
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product', backref='order_items')
    
class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    user = db.relationship('User', back_populates='wishlist')
    product = db.relationship('Product', backref=db.backref('wishlist_items', lazy=True))

    def __repr__(self):
        return f'<Wishlist {self.id}>'