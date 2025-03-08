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
         
         if not Product.query.first():
             products = [
                 {
                     'name': 'Premium Dark Chocolate Bar',
                     'price': 5.99,
                     'image': 'https://images.pexels.com/photos/65882/chocolate-dark-coffee-confiserie-65882.jpeg',
                     'category': 'Chocolate',
                     'description': 'Indulge in the rich, velvety smoothness of our premium dark chocolate bar. Made with the finest cocoa beans, this bar is perfect for chocolate lovers who appreciate a deep, intense flavor.'
                 },
                 {
                     'name': 'White Chocolate Delight',
                     'price': 4.99,
                     'image': 'https://images.pexels.com/photos/4791257/pexels-photo-4791257.jpeg',
                     'category': 'Chocolate',
                     'description': 'Experience the sweet, delicate flavor of our white chocolate bar. Made with high-quality ingredients, it\'s the perfect treat for those who prefer a lighter, more vanilla-forward chocolate taste.'
                 },
                 {
                     'name': 'Chocolate Chip Cookies (pack of 3)',
                     'price': 9.99,
                     'image': 'https://images.pexels.com/photos/230325/pexels-photo-230325.jpeg',
                     'category': 'Cookies',
                     'description': 'These classic chocolate chip cookies are baked to golden perfection, featuring chunks of semi-sweet chocolate in a soft, buttery dough. A timeless favorite for any occasion.'
                 },
                 {
                     'name': 'Chocolate Lava Cake',
                     'price': 19.99,
                     'image': 'https://images.pexels.com/photos/14309255/pexels-photo-14309255.jpeg',
                     'category': 'Cakes',
                     'description': 'Indulge in the decadence of our chocolate lava cake, with its rich chocolate exterior and a molten chocolate center that oozes out when you cut into it.'
                 },
                 {
                     'name': 'New York Style Cheesecake',
                     'price': 29.99,
                     'image': 'https://images.pexels.com/photos/3185509/pexels-photo-3185509.png',
                     'category': 'Cakes',
                     'description': 'Our creamy and smooth cheesecake is a timeless classic, made with a graham cracker crust and topped with your choice of fruit or chocolate sauce. It\'s the perfect balance of tangy and sweet.'
                 },
                 {
                     'name': 'Strawberry Lattice Pie',
                     'price': 24.99,
                     'image': 'https://images.pexels.com/photos/31020416/pexels-photo-31020416.jpeg',
                     'category': 'Cakes',
                     'description': 'Delight in the fresh, summery taste of our strawberry lattice pie. Made with a flaky pastry crust and filled with juicy strawberries, it\'s a light and refreshing dessert.'
                 },
                 {
                     'name': 'Fudge Brownies (pack of 4)',
                     'price': 14.99,
                     'image': 'https://images.pexels.com/photos/2067396/pexels-photo-2067396.jpeg',
                     'category': 'Cakes',
                     'description': 'Our fudgy brownies are rich, chocolatey, and perfectly moist. Each bite is an indulgence in chocolate heaven.'
                 },
                 {
                     'name': 'Nutella and Strawberry Croissant',
                     'price': 5.99,
                     'image': 'https://images.pexels.com/photos/27411773/pexels-photo-27411773.jpeg',
                     'category': 'Pastries',
                     'description': 'Start your day with our flaky and buttery croissant, filled with Nutella and topped with fresh strawberries. It\'s a delightful treat for breakfast or a mid-day snack.'
                 },
                 {
                     'name': 'Sour Patch Kids (bag)',
                     'price': 2.99,
                     'image': 'https://images.pexels.com/photos/7110191/pexels-photo-7110191.jpeg',
                     'category': 'Candy',
                     'description': 'These tangy and sweet Sour Patch Kids are a favorite among candy lovers. They start sour and end sweet, providing a fun and flavorful experience.'
                 },
                 {
                     'name': 'Vanilla Ice Cream Cone',
                     'price': 3.99,
                     'image': 'https://images.pexels.com/photos/1362534/pexels-photo-1362534.jpeg',
                     'category': 'Other',
                     'description': 'Enjoy our classic vanilla ice cream in a wafer cone, a timeless favorite that pairs well with any topping or dessert.'
                 }
             ]
             
             for product_data in products:
                 product = Product(**product_data)
                 db.session.add(product)
             
             db.session.commit()
             print("Products added successfully!")
         else:
             print("Database is not empty. No products added.")

def add_missing_columns(app):
    with app.app_context():
        from sqlalchemy import text, inspect
        
        engine = db.engine
        inspector = inspect(engine)
        
        try:
            existing_product_columns = [col['name'] for col in inspector.get_columns('products')]
            
            if 'category' not in existing_product_columns:
                db.session.execute(text("ALTER TABLE products ADD COLUMN category VARCHAR(50)"))
                print("Added 'category' column to products table")
            
            if 'description' not in existing_product_columns:
                db.session.execute(text("ALTER TABLE products ADD COLUMN description TEXT"))
                print("Added 'description' column to products table")
                
            if 'created_at' not in existing_product_columns:
                db.session.execute(text("ALTER TABLE products ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                print("Added 'created_at' column to products table")
            
            existing_user_columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'created_at' not in existing_user_columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                print("Added 'created_at' column to users table")
            
            db.session.commit()
            print("All missing columns added successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error adding missing columns: {str(e)}")
            raise

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
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='SET NULL'), nullable=True)
    product_name = db.Column(db.String(120), nullable=True)  # Store product name for history
    product_price = db.Column(db.Float, nullable=True)  # Store product price for history
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Price at time of purchase
    
    def to_dict(self):
        product_name = self.product_name
        if not product_name and self.product:
            product_name = self.product.name
            
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": product_name or "Deleted Product",
            "quantity": self.quantity,
            "price": self.price,
            "total": self.price * self.quantity
        }
