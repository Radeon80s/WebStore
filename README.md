# SweetBites - Webstore

[![Flask](https://img.shields.io/badge/Flask-blue.svg)](https://flask.palletsprojects.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.3-purple.svg)](https://getbootstrap.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-orange.svg)](https://www.sqlalchemy.org/)
[![Railway](https://img.shields.io/badge/Railway-Deployment-brightgreen.svg)](https://railway.app/)

## ✨ Features

### Customer Features
- **Product Catalog** - Browse products with search functionality
- **Shopping Cart** - Add items to cart with persistent browser storage
- **Wishlist** - Save favorite products for later

### Admin Features
- **Product Management** - Add, edit, and delete products
- **User Authentication** - Secure login with role-based access
- **Admin Dashboard** - Manage product catalog

## 🌐 Demo

A live demo is available at: [https://web-production-2b47.up.railway.app/](https://web-production-2b47.up.railway.app/)

## 🔧 Tech Stack

### Backend
- **Python** with **Flask** framework
- **SQLAlchemy** ORM
- **PostgreSQL** database
- **Werkzeug** for hashing

### Frontend
- **HTML5/CSS3/JavaScript**
- **Bootstrap 5** for UI components
- **LocalStorage API** client-side

### Ops
- **Railway** for deployment
- **Gunicorn** as WSGI HTTP Server

## 🚀 Installation

### Prerequisites
- Python 3.7+
- PostgreSQL
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/Radeon80s/Webstore.git
   cd Webstore
   ```


## 🔐 Environment Variables

| Variable | Description | Env Variable |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `server-side` |
| `SECRET_KEY` | Flask secret key for session security | `server-side` |

## 📁 Project Structure

```
Webstore/
│
├── app.py                 
├── models.py              
├── requirements.txt       # Project dependencies
├── Procfile               # Railway deployment 
│
├── static/                # Static
│   └── index.html
│
└── templates/
    ├── admin_products.html    # Admin product management
    ├── edit_product.html      # Product edit form
    ├── index.html             # Main interface
    ├── login.html             # User login page
    └── register.html          # User registration page
```

## 📝 Usage

### Customer Interface

1. **Browse Products**: View all products on the home page
2. **Search**: Use the search bar to find specific products
3. **Wishlist**: Click the heart icon to add items to your wishlist
4. **Shopping Cart**: Add items to your cart and proceed to checkout
5. **Checkout**: Fill in your details and apply discount codes (`SAVE10`)

### User Authentication

1. **Register**: Create a new account with your email
2. **Login**: Access your account with your credentials

## 👩‍💼 Admin

### Managing Products

- **Add Products**: Fill in the product details in the form at the top of the admin panel
- **Edit Products**: Click the Edit button next to a product
- **Delete Products**: Click the Delete button next to a product

## 🔌 API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|--------------|
| `/api/products` | GET | List all products | No |
| `/api/current_user` | GET | Get current user info | Yes (session) |
| `/api/validate-discount` | POST | Validate discount code | No |
| `/admin/products` | GET | Admin product list | Yes (admin) |
| `/admin/products/create` | POST | Create a product | Yes (admin) |
| `/admin/products/<id>/edit` | GET/POST | Edit a product | Yes (admin) |
| `/admin/products/<id>/delete` | POST | Delete a product | Yes (admin) |
| `/admin/discounts` | GET | List discount codes | Yes (admin) |
| `/admin/discounts/create` | POST | Create a discount code | Yes (admin) |
| `/admin/discounts/<id>/toggle` | POST | Toggle discount code status | Yes (admin) |
| `/admin/discounts/<id>/delete` | POST | Delete a discount code | Yes (admin) |


## 🚢 Deployment

### Deploying to Railway
```
web: gunicorn app:app --bind 0.0.0.0:$PORT
```
