import os
import re
from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from dotenv import load_dotenv
from models import init_db, db, User, Product, DiscountCode, Order, OrderItem
from datetime import datetime, timedelta
import bleach
import json

# Login rate limiting
login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5 
LOCKOUT_TIME = 15

# Categories for products
PRODUCT_CATEGORIES = ['Chocolate', 'Cookies', 'Cakes', 'Pastries', 'Candy', 'Other']

# Order statuses
ORDER_STATUSES = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']

# Load environment variables
load_dotenv()
app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', '')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
init_db(app)

# Helper functions
def validate_email(e):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, e) is not None

def validate_password(p):
    if len(p) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', p):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', p):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', p):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', p):
        return False, "Password must contain at least one special character"
    
    return True, "Password is okay"

def is_rate_limited(ip):
    now = datetime.now()
    if ip in login_attempts:
        login_attempts[ip] = [
            timestamp for timestamp in login_attempts[ip] 
            if (now - timestamp).total_seconds() < (LOCKOUT_TIME * 60)
        ]
        return len(login_attempts[ip]) >= MAX_LOGIN_ATTEMPTS
    return False

def record_login_attempt(ip):
    now = datetime.now()
    if ip not in login_attempts:
        login_attempts[ip] = []
    login_attempts[ip].append(now)

def sanitize_input(text):
    return bleach.clean(text, strip=True) if text else ""

def validate_price(price_str):
    try:
        price = float(price_str)
        if price < 0:
            return 0, False
        return price, True
    except (ValueError, TypeError):
        return 0, False

def validate_url(u):
    return re.match(r'^https?://[^\s/$.?#].[^\s]*$', u) is not None

def is_admin():
    return session.get('is_admin') is True

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash("You have to be an administrator to access this page!", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Home route - serve the static Vue.js frontend
@app.route('/')
def home():
    return app.send_static_file('index.html')

# Authentication routes
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        e = sanitize_input(request.form.get('email', '').strip())
        p = request.form.get('password', '')
        if not validate_email(e):
            flash("Invalid email format.", "danger")
            return redirect(url_for('register'))
        if User.query.filter_by(email=e).first():
            flash("Email already used.", "danger")
            return redirect(url_for('register'))
        
        is_valid, message = validate_password(p)
        if not is_valid:
            flash(message, "danger")
            return redirect(url_for('register'))    
        
        h = generate_password_hash(p)
        u = User(email=e, password=h, is_admin=False)
        db.session.add(u)
        db.session.commit()
        flash("Registered successfully. Please login.", "success")
        return redirect(url_for('login'))
    return render_template('register.html', now=datetime.utcnow())

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        e = sanitize_input(request.form.get('email', '').strip())
        p = request.form.get('password', '')
        ip = request.remote_addr
        
        if is_rate_limited(ip):
            flash("Too many login attempts. Please try again later.", "danger")
            return redirect(url_for('login'))
            
        u = User.query.filter_by(email=e).first()
        if u and check_password_hash(u.password, p):
            session.clear()
            session['user_id'] = u.id
            session['email'] = u.email
            session['is_admin'] = u.is_admin
            session.permanent = True
            flash("Logged in!", "success")
            return redirect(url_for('home'))
        
        record_login_attempt(ip)        
        flash("Invalid credentials.", "danger")
        return redirect(url_for('login'))
    return render_template('login.html', now=datetime.utcnow())

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('login'))

# API Routes
@app.route('/api/current_user')
def api_current_user():
    if 'user_id' not in session:
        return jsonify({"logged_in": False})
    
    return jsonify({
        "logged_in": True,
        "user_id": session.get('user_id'),
        "email": session.get('email'),
        "is_admin": session.get('is_admin', False)
    })

@app.route('/api/products')
def api_products():
    ps = Product.query.order_by(Product.id.desc()).all()
    return jsonify([p.to_dict() for p in ps])

@app.route('/api/products/<int:product_id>')
def api_product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())

@app.route('/api/categories')
def api_categories():
    return jsonify(PRODUCT_CATEGORIES)

@app.route('/api/validate-discount', methods=['POST'])
def api_validate_discount():
    if not request.is_json:
        return jsonify({"success": False, "error": "Invalid request format"}), 400
    
    code = request.json.get('code', '').strip().upper()
    if not code:
        return jsonify({"success": False, "error": "No discount code provided"}), 400
    
    discount = DiscountCode.query.filter_by(code=code, active=True).first()
    
    if not discount or not discount.is_valid():
        return jsonify({"success": False, "error": "Invalid or expired discount code"}), 404
    
    return jsonify({
        "success": True,
        "type": discount.type,
        "amount": discount.amount
    })


@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    if not request.is_json:
        return jsonify({"success": False, "error": "Invalid request format"}), 400
    
    # Get data from request
    data = request.json
    cart_items = data.get('items', [])
    
    if not cart_items:
        return jsonify({"success": False, "error": "No items in cart"}), 400
    
    # Calculate order totals
    subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)
    discount_amount = 0
    shipping_cost = data.get('shipping_cost', 0.0)
    
    # Apply discount code if provided
    discount_code = None
    if data.get('discount_code'):
        discount = DiscountCode.query.filter_by(code=data['discount_code'], active=True).first()
        if discount and discount.is_valid():
            if discount.type == 'percent':
                discount_amount = subtotal * (discount.amount / 100)
            else:  # flat
                discount_amount = min(discount.amount, subtotal)
            discount_code = discount
    
    # Calculate total
    total = subtotal - discount_amount + shipping_cost
    
    # Create order
    order = Order(
        user_id=session.get('user_id'),
        subtotal=subtotal,
        discount_amount=discount_amount,
        shipping_cost=shipping_cost,
        total=total,
        customer_name=data.get('customer_name'),
        customer_email=data.get('customer_email', session.get('email')),
        shipping_address=data.get('shipping_address'),
        discount_code=discount_code
    )
    
    db.session.add(order)
    db.session.flush()  # Get the order ID
    
    # Create order items
    for item in cart_items:
        product_id = item.get('id')
        quantity = item.get('quantity', 1)
        price = item.get('price', 0)
        
        if product_id and quantity > 0:
            # Get product to store its details
            product = Product.query.get(product_id)
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                price=price,
                # Store product details for future reference in case product is deleted
                product_name=product.name if product else None,
                product_price=product.price if product else price
            )
            db.session.add(order_item)
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "order_id": order.id,
        "total": order.total,
        "message": "Order placed successfully!"
    })

@app.route('/api/orders')
@login_required
def api_orders():
    user_id = session.get('user_id')
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    return jsonify([order.to_dict() for order in orders])

@app.route('/api/orders/<int:order_id>')
@login_required
def api_order_detail(order_id):
    user_id = session.get('user_id')
    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    
    if not order and not is_admin():
        abort(404)
    
    # For admins, allow access to any order
    if not order and is_admin():
        order = Order.query.get_or_404(order_id)
    
    return jsonify(order.to_dict())

# Admin routes - Products
@app.route('/admin')
@admin_required
def admin_dashboard():
    # Get counts for dashboard
    product_count = Product.query.count()
    order_count = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    discount_count = DiscountCode.query.count()
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

    discounts = DiscountCode.query.order_by(DiscountCode.created_at.desc()).all()
    
    # Calculate total revenue
    total_revenue = db.session.query(db.func.sum(Order.total)).scalar() or 0
    
    return render_template(
        'admin/dashboard.html', 
        active_tab='dashboard',
        product_count=product_count,
        order_count=order_count,
        pending_orders=pending_orders,
        discount_count=discount_count,
        recent_orders=recent_orders,
        total_revenue=total_revenue,
        discounts=discounts,
        now=datetime.utcnow(),
        timedelta=timedelta
    )

@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.order_by(Product.id.desc()).all()
    categories = PRODUCT_CATEGORIES
    return render_template(
        'admin/products.html', 
        products=products, 
        categories=categories,
        active_tab='products',
        now=datetime.utcnow()
    )

@app.route('/admin/products/create', methods=['POST'])
@admin_required
def admin_create_product():
    name = sanitize_input(request.form.get('name', '').strip())
    price_str = request.form.get('price', '0')
    image = sanitize_input(request.form.get('image', '').strip())
    category = sanitize_input(request.form.get('category', '').strip())
    description = sanitize_input(request.form.get('description', '').strip())
    
    if not name or not image:
        flash("Name & image are required", "danger")
        return redirect(url_for('admin_products'))
    
    price, is_valid = validate_price(price_str)
    if not is_valid:
        flash("Price must be a positive number", "danger")
        return redirect(url_for('admin_products'))
        
    if not validate_url(image):
        flash("Please enter a valid image URL", "danger")
        return redirect(url_for('admin_products'))
    
    product = Product(
        name=name, 
        price=price, 
        image=image,
        category=category,
        description=description
    )
    
    db.session.add(product)
    db.session.commit()
    flash("Product created successfully!", "success")
    return redirect(url_for('admin_products'))

@app.route('/admin/products/<int:pid>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(pid):
    product = Product.query.get_or_404(pid)
    
    if request.method == 'POST':
        product.name = sanitize_input(request.form.get('name', '').strip())
        
        price_str = request.form.get('price', '0')
        price, is_valid = validate_price(price_str)
        if not is_valid:
            flash("Price must be a positive number", "danger")
            return redirect(url_for('admin_edit_product', pid=pid))
        product.price = price
        
        image = sanitize_input(request.form.get('image', '').strip())
        if not validate_url(image):
            flash("Please enter a valid image URL", "danger")
            return redirect(url_for('admin_edit_product', pid=pid))
        product.image = image
        
        product.category = sanitize_input(request.form.get('category', '').strip())
        product.description = sanitize_input(request.form.get('description', '').strip())
        
        db.session.commit()
        flash("Product updated successfully!", "success")
        return redirect(url_for('admin_products'))
    
    categories = PRODUCT_CATEGORIES
    return render_template(
        'admin/edit_product.html', 
        product=product, 
        categories=categories,
        active_tab='products',
        now=datetime.utcnow()
    )

@app.route('/admin/products/<int:pid>/delete', methods=['POST'])
@admin_required
def admin_delete_product(pid):
    product = Product.query.get_or_404(pid)
    try:
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting product: {str(e)}", "danger")
    
    return redirect(url_for('admin_products'))

@app.route('/admin/discounts')
@admin_required
def admin_discounts():
    discounts = DiscountCode.query.order_by(DiscountCode.created_at.desc()).all()
    return render_template(
        'admin/discounts.html', 
        discounts=discounts,
        active_tab='discounts',
        now=datetime.utcnow(),
        timedelta=timedelta
    )

@app.route('/admin/discounts/create', methods=['POST'])
@admin_required
def admin_create_discount():
    code = sanitize_input(request.form.get('code', '').strip().upper())
    discount_type = sanitize_input(request.form.get('type', '').strip())
    amount_str = request.form.get('amount', '0')
    expires_str = request.form.get('expires_at', '')
    
    # Validate required fields
    if not code or not discount_type:
        flash("Code and type are required", "danger")
        return redirect(url_for('admin_discounts'))
    
    # Check if discount code already exists
    if DiscountCode.query.filter_by(code=code).first():
        flash("Discount code already exists", "danger")
        return redirect(url_for('admin_discounts'))
    
    # Validate amount
    try:
        amount = float(amount_str)
        if amount <= 0:
            flash("Amount must be greater than 0", "danger")
            return redirect(url_for('admin_discounts'))
        
        # Additional validation for percentage type
        if discount_type == 'percent' and (amount < 1 or amount > 100):
            flash("Percentage must be between 1 and 100", "danger")
            return redirect(url_for('admin_discounts'))
    except ValueError:
        flash("Invalid amount", "danger")
        return redirect(url_for('admin_discounts'))
    
    # Validate discount type
    if discount_type not in ['percent', 'flat']:
        flash("Type must be 'percent' or 'flat'", "danger")
        return redirect(url_for('admin_discounts'))
    
    # Parse expiry date if provided
    expires_at = None
    if expires_str:
        try:
            expires_at = datetime.strptime(expires_str, '%Y-%m-%d')
        except ValueError:
            flash("Invalid expiry date format. Use YYYY-MM-DD", "danger")
            return redirect(url_for('admin_discounts'))
    
    # Create and save the discount
    try:
        discount = DiscountCode(
            code=code,
            type=discount_type,
            amount=amount,
            active=True,
            expires_at=expires_at
        )
        
        db.session.add(discount)
        db.session.commit()
        
        flash("Discount code created successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating discount: {str(e)}", "danger")
    
    return redirect(url_for('admin_discounts'))

@app.route('/admin/discounts/<int:discount_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_discount(discount_id):
    discount = DiscountCode.query.get_or_404(discount_id)
    discount.active = not discount.active
    db.session.commit()
    
    status = "activated" if discount.active else "deactivated"
    flash(f"Discount code {status} successfully!", "success")
    return redirect(url_for('admin_discounts'))

@app.route('/admin/discounts/<int:discount_id>/delete', methods=['POST'])
@admin_required
def admin_delete_discount(discount_id):
    discount = DiscountCode.query.get_or_404(discount_id)
    db.session.delete(discount)
    db.session.commit()
    
    flash("Discount code deleted successfully!", "success")
    return redirect(url_for('admin_discounts'))

# Admin routes - Orders
@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template(
        'admin/orders.html', 
        orders=orders,
        statuses=ORDER_STATUSES,
        active_tab='orders',
        now=datetime.utcnow()
    )

@app.route('/admin/orders/<int:order_id>')
@admin_required
def admin_view_order(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template(
        'admin/view_order.html', 
        order=order,
        statuses=ORDER_STATUSES,
        active_tab='orders',
        now=datetime.utcnow()
    )

@app.route('/admin/orders/<int:order_id>/update', methods=['POST'])
@admin_required
def admin_update_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    status = request.form.get('status')
    if status and status in ORDER_STATUSES:
        order.status = status
        db.session.commit()
        flash("Order status updated successfully!", "success")
    
    return redirect(url_for('admin_view_order', order_id=order_id))

@app.errorhandler(404)
def not_found(e):
    # For API routes, return JSON error
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "Resource not found"}), 404
    
    # For web routes, send the SPA
    return app.send_static_file('index.html')
    
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

if __name__=='__main__':
    app.run(debug=False)
