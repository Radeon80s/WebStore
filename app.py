"""
Run this script to modify the database schema to allow product deletion
by altering the constraint on the order_items table.

This script will:
1. Add product_name and product_price columns to order_items (if they don't exist)
2. Transfer product data to these columns
3. Drop the NOT NULL constraint on product_id
4. Re-add the foreign key with ON DELETE SET NULL

After this change, deleting products will set product_id to NULL in order_items,
but order history will be preserved with the name and price.
"""

import os
from flask import Flask
from models import db, Product, OrderItem
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a minimal Flask app for this script
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def run_schema_update():
    with app.app_context():
        try:
            # 1. Add product_name and product_price columns if they don't exist
            db.session.execute("""
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
            """)
            print("✅ Added product_name and product_price columns if needed")

            # 2. Copy product data to the backup columns
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
            db.session.execute("""
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
            """)
            print("✅ Dropped foreign key constraint")

            # 4. Make product_id nullable
            db.session.execute("ALTER TABLE order_items ALTER COLUMN product_id DROP NOT NULL;")
            print("✅ Made product_id nullable")

            # 5. Re-add the foreign key with ON DELETE SET NULL
            db.session.execute("""
            ALTER TABLE order_items
            ADD CONSTRAINT fk_order_items_product
            FOREIGN KEY (product_id)
            REFERENCES products(id)
            ON DELETE SET NULL;
            """)
            print("✅ Added new foreign key with ON DELETE SET NULL")

            print("\n✅ Schema update completed successfully!")
            print("\nNow you can delete products, and they will be safely removed from the database.")
            print("Past orders will still show product names and prices, but will have product_id set to NULL.")

        except Exception as e:
            print(f"❌ Error updating schema: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    run_schema_update()
