from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
import datetime
import qrcode
import io
from bson.binary import Binary
from bson import ObjectId
import base64
import certifi
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")  # For flash messages

try:
    mongo_uri = os.environ.get("MONGO_URI")
    print(f"Mongo URI: {mongo_uri}")
    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
    db = client['bakery']  # Database name
    orders_collection = db['orders']  # Collection name
    products_collection = db['products']  # Collection for products
    print("Connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# Ensure the products are stored in the database
def initialize_products():
    sample_inventory = [
        {"name": "Bread", "price": 2.50, "stock": 10},
        {"name": "Cupcakes", "price": 1.00, "stock": 15},
        {"name": "Cookies", "price": 3.00, "stock": 8},
        {"name": "Croissant", "price": 2.00, "stock": 12},
        {"name": "Donuts", "price": 1.50, "stock": 20},
        {"name": "Muffins", "price": 1.20, "stock": 10},
        {"name": "Bagels", "price": 1.00, "stock": 15},
        {"name": "Brownies", "price": 2.50, "stock": 10},
        {"name": "Pies", "price": 5.00, "stock": 5},
        {"name": "Cakes", "price": 15.00, "stock": 3}
    ]

    for product in sample_inventory:
        if not products_collection.find_one({"name": product['name']}):
            products_collection.insert_one(product)

# Product class
class Product:
    def __init__(self, name, price, stock):
        self.name = name
        self.price = price
        self.stock = stock

# Initialize products in the database
initialize_products()

# Function to generate QR code
def generate_qr(order_summary):
    receipt_link = f"http://localhost:5000/receipt/{str(order_summary['_id'])}"  # Assuming Flask runs on localhost:5000
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(receipt_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Convert image bytes to Base64 string
    img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    
    return img_base64

# Context processor for utility functions
@app.context_processor
def utility_processor():
    return dict(enumerate=enumerate)

# Route for home page
@app.route('/')
def index():
    inventory = [Product(p['name'], p['price'], p['stock']) for p in products_collection.find()]
    orders = list(orders_collection.find())

    # Convert the timestamp from string to datetime object
    for order in orders:
        order['timestamp'] = datetime.datetime.strptime(order['timestamp'], "%Y-%m-%d_%H-%M-%S")

    return render_template('index.html', inventory=inventory, orders=orders)

# Route for placing an order
@app.route('/order', methods=['POST'])
def order():
    customer_name = request.form.get('customer_name')
    order_items = {}
    total_amount = 0

    for i, product in enumerate(products_collection.find()):
        quantity = int(request.form.get(f'quantity_{i}', 0))
        if quantity > 0:
            if quantity <= product['stock']:
                products_collection.update_one({'name': product['name']}, {'$inc': {'stock': -quantity}})
                order_items[product['name']] = quantity
                total_amount += product['price'] * quantity
            else:
                flash(f'Insufficient stock for {product["name"]}. Available stock: {product["stock"]}', 'error')

    if not order_items:
        flash('No items ordered', 'error')
        return redirect(url_for('index'))

    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    order_summary = {
        "_id": ObjectId(),  # Generate new ObjectId for the order
        "customer_name": customer_name,
        "timestamp": current_time,
        "order": order_items,
        "total": total_amount
    }

    # Generate QR code
    qr_img_src = generate_qr(order_summary)

    # Save order and QR code in MongoDB
    order_data = {
        "_id": order_summary["_id"],  # Assign the same ObjectId to order_data
        "customer_name": customer_name,
        "order": order_items,
        "total": total_amount,
        "timestamp": current_time,
        "qr_code": qr_img_src
    }
    orders_collection.insert_one(order_data)

    flash('Order placed successfully', 'success')
    return redirect(url_for('confirmation', order_id=str(order_summary['_id']), qr_img_src=qr_img_src))  # Pass order_id and qr_img_src as parameters

@app.route('/confirmation/<order_id>')
def confirmation(order_id):
    order_data = orders_collection.find_one({'_id': ObjectId(order_id)})
    if order_data:
        # Process order_data and display confirmation page
        qr_img_src = order_data.get('qr_code')
        return render_template('confirmation.html', order=order_data, qr_img_src=qr_img_src)
    else:
        flash('Order not found', 'error')
        return redirect(url_for('index'))

# Route for displaying receipt after placing an order
@app.route('/receipt/<order_id>')
def receipt(order_id):
    order_data = orders_collection.find_one({'_id': ObjectId(order_id)})
    if not order_data:
        flash('Order not found', 'error')
        return redirect(url_for('index'))

    order_summary = {
        "customer_name": order_data['customer_name'],
        "timestamp": order_data['timestamp'],
        "order": order_data['order'],
        "total": order_data['total']
    }

    return render_template('receipt.html', order=order_summary)

# Route for admin login
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'adminpassword':  # Replace with a more secure password or use environment variables
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect password', 'error')
            return redirect(url_for('index'))
    else:
        return render_template('admin.html')

# Route for admin dashboard
@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    inventory = [Product(p['name'], p['price'], p['stock']) for p in products_collection.find()]
    
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        new_stock = int(request.form.get('new_stock'))
        products_collection.update_one({'name': product_name}, {'$set': {'stock': new_stock}})
        flash(f'Stock for {product_name} updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_dashboard.html', inventory=inventory)

@app.route('/admin/update_stock', methods=['POST'])
def update_stock():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    product_name = request.form.get('product_name')
    new_stock = int(request.form.get('new_stock'))

    # Retrieve current stock
    current_stock = products_collection.find_one({'name': product_name})['stock']

    # Update stock by adding previous stock with new stock
    total_stock = current_stock + new_stock

    # Update the database
    products_collection.update_one({'name': product_name}, {'$set': {'stock': total_stock}})

    flash(f'Stock for {product_name} updated successfully', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
