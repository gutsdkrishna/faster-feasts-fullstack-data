from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
import datetime
import qrcode
import os
import certifi

app = Flask(__name__)
app.secret_key = "supersecretkey"  # For flash messages

# Establish MongoDB connection
client = MongoClient("mongodb+srv://randi:KboUc2P0KVAoOptx@kalki.ow7yktj.mongodb.net/bakery?retryWrites=true&w=majority",
                     tls=True,
                     tlsCAFile=certifi.where())
db = client['bakery']  # Database name
orders_collection = db['orders']  # Collection name

# Product class
class Product:
    def __init__(self, name, price, stock):
        self.name = name
        self.price = price
        self.stock = stock

# Sample inventory
inventory = [
    Product("Bread", 2.50, 10),
    Product("Cupcakes", 1.00, 15),
    Product("Cookies", 3.00, 8),
    Product("Croissant", 2.00, 12),
    Product("Donuts", 1.50, 20),
    Product("Muffins", 1.20, 10),
    Product("Bagels", 1.00, 15),
    Product("Brownies", 2.50, 10),
    Product("Pies", 5.00, 5),
    Product("Cakes", 15.00, 3)
]

@app.context_processor
def utility_processor():
    return dict(enumerate=enumerate)

@app.route('/')
def index():
    return render_template('index.html', inventory=inventory)

@app.route('/order', methods=['POST'])
def order():
    customer_name = request.form.get('customer_name')
    order_items = {}
    total_amount = 0

    for i, product in enumerate(inventory):
        quantity = int(request.form.get(f'quantity_{i}', 0))
        if quantity > 0:
            if quantity <= product.stock:
                product.stock -= quantity
                order_items[product.name] = quantity
                total_amount += product.price * quantity
            else:
                flash(f'Insufficient stock for {product.name}. Available stock: {product.stock}', 'error')

    if not order_items:
        flash('No items ordered', 'error')
        return redirect(url_for('index'))

    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    order_data = {
        "customer_name": customer_name,
        "order": order_items,
        "total": total_amount,
        "timestamp": current_time
    }
    orders_collection.insert_one(order_data)

    order_summary = f"Customer: {customer_name}\nDate & Time: {current_time}\nOrder: {order_items}\nTotal: {total_amount}"
    generate_qr(order_summary, f"{customer_name}_{current_time}")

    flash('Order placed successfully', 'success')
    return redirect(url_for('confirmation'))

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

def generate_qr(data, filename):
    filename = filename.replace(" ", "_").strip("_")
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    if not os.path.exists("static/qr_codes"):
        os.makedirs("static/qr_codes")
    img.save(f"static/qr_codes/{filename}.png")
    print(f"QR code saved to static/qr_codes/{filename}.png")

if __name__ == '__main__':
    app.run(debug=True)
