from datetime import datetime
import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import json

load_dotenv()

db = SQLAlchemy()

def init_db(app):
    db_uri = os.getenv('DATABASE_URL')

    if db_uri.startswith('postgres://'):
        db_uri = db_uri.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('Order', backref='user', lazy=True)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "img": self.image,
            "category": self.category,
            "description": self.description
        }


class DiscountCode(db.Model):
    __tablename__ = 'discount_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'percent' or 'flat'
    amount = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    orders = db.relationship('Order', backref='discount_code', lazy=True)
    
    def is_valid(self):
        if not self.active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for guest checkout
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, completed, cancelled
    total = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)
    shipping_cost = db.Column(db.Float, nullable=False, default=0.0)
    discount_code_id = db.Column(db.Integer, db.ForeignKey('discount_codes.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=True)
    customer_email = db.Column(db.String(120), nullable=True)
    shipping_address = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "total": self.total,
            "subtotal": self.subtotal,
            "discount_amount": self.discount_amount,
            "shipping_cost": self.shipping_cost,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "shipping_address": self.shipping_address,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "items": [item.to_dict() for item in self.items],
            "discount_code": self.discount_code.code if self.discount_code else None
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Price at time of purchase
    
    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name,
            "quantity": self.quantity,
            "price": self.price,
            "total": self.price * self.quantity
        }
