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
        
        # Run the one-time migration
        run_one_time_migration(app)


def run_one_time_migration(app):
    """
    Run a one-time migration to fix the product deletion constraint issue.
    This function will:
    1. Add product_name and product_price columns to order_items if they don't exist
    2. Copy product data to these columns for existing orders
    3. Drop the NOT NULL constraint on product_id
    4. Add ON DELETE SET NULL to the foreign key constraint
    """
    # Import text from sqlalchemy
    from sqlalchemy import text
    
    # Check if migration has already been run (using a table column as indicator)
    with app.app_context():
        # First, check if the columns already exist, which indicates migration was done
        column_check = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name='order_items' AND column_name='product_name'
        );
        """)).scalar()
        
        # If product_name column exists, migration might have been done already
        if column_check:
            # Check if product_id is already nullable
            nullable_check = db.session.execute(text("""
            SELECT is_nullable 
            FROM information_schema.columns 
            WHERE table_name='order_items' AND column_name='product_id';
            """)).scalar()
            
            if nullable_check == 'YES':
                # Migration already completed
                print("✅ Product deletion migration already completed")
                return
        
        try:
            print("🔄 Running one-time migration to fix product deletion...")
            
            # 1. Add product_name and product_price columns if they don't exist
            db.session.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                            WHERE table_name='order_items' AND column_name='product_name') THEN
                    ALTER TABLE order_items ADD COLUMN product_name VARCHAR(120);
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                            WHERE table_name='order_items' AND column_name='product_price') THEN
                    ALTER TABLE order_items ADD COLUMN product_price FLOAT;
                END IF;
            END
            $$;
            """))
            print("✅ Added product_name and product_price columns if needed")

            # 2. Copy product data to the backup columns for existing orders
            order_items = OrderItem.query.all()
            for item in order_items:
                if item.product_id and (item.product_name is None or item.product_price is None):
                    product = Product.query.get(item.product_id)
                    if product:
                        item.product_name = product.name
                        item.product_price = product.price
            db.session.commit()
            print("✅ Copied product data to backup columns")

            # 3. Drop the foreign key constraint
            db.session.execute(text("""
            DO $$
            DECLARE
                constraint_name VARCHAR;
            BEGIN
                SELECT tc.constraint_name INTO constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = 'order_items' 
                AND tc.constraint_type = 'FOREIGN KEY' 
                AND ccu.column_name = 'product_id';
                
                IF constraint_name IS NOT NULL THEN
                    EXECUTE 'ALTER TABLE order_items DROP CONSTRAINT ' || constraint_name;
                END IF;
            END
            $$;
            """))
            print("✅ Dropped foreign key constraint")

            # 4. Make product_id nullable
            db.session.execute(text("ALTER TABLE order_items ALTER COLUMN product_id DROP NOT NULL;"))
            print("✅ Made product_id nullable")

            # 5. Re-add the foreign key with ON DELETE SET NULL
            db.session.execute(text("""
            ALTER TABLE order_items
            ADD CONSTRAINT fk_order_items_product
            FOREIGN KEY (product_id)
            REFERENCES products(id)
            ON DELETE SET NULL;
            """))
            print("✅ Added new foreign key with ON DELETE SET NULL")
            
            print("✅ Migration completed successfully! You can now delete products without constraints.")
            
        except Exception as e:
            print(f"❌ Error during migration: {str(e)}")
            db.session.rollback()

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
