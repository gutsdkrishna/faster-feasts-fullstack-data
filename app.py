import datetime
import os
import qrcode
from pymongo import MongoClient
import certifi

os.environ['SSL_CERT_FILE'] = certifi.where()

# Define product class
class Product:
    def __init__(self, name, price, stock):
        self.name = name
        self.price = price
        self.stock = stock

# Function to display available products
def display_inventory(inventory):
    print("-" * 50)
    print("Available Bakery Items:")
    print("-" * 50)
    print("{:<5s}{:<20s}{:>10s}{:>10s}".format("No.", "Name", "Price", "Stock"))
    print("-" * 50)
    for index, product in enumerate(inventory):
        print("{:<5d}{:<20s}{:>10.2f}{:>10d}".format(index + 1, product.name, product.price, product.stock))
    print("-" * 50)

# Function to take order
def take_order(inventory):
    order = {}
    while True:
        display_inventory(inventory)
        product_index = input("Enter product number (or 'q' to quit): ")
        if product_index.lower() == 'q':
            break
        if product_index.isdigit():
            product_index = int(product_index) - 1
            if 0 <= product_index < len(inventory):
                product = inventory[product_index]
                quantity = int(input(f"Enter quantity for {product.name}: "))
                if quantity <= product.stock:
                    if product.name in order:
                        order[product.name] += quantity
                    else:
                        order[product.name] = quantity
                    product.stock -= quantity
                else:
                    print(f"Insufficient stock for {product.name}. Available stock: {product.stock}")
            else:
                print("Invalid product number.")
        else:
            print("Invalid input. Please enter a number.")
    return order

# Function to calculate bill
def calculate_bill(order, inventory):
    total = 0
    print("\nYour Order:")
    print("-" * 50)
    print("{:<20s}{:>10s}{:>10s}".format("Name", "Price", "Quantity"))
    print("-" * 50)
    for product_name, quantity in order.items():
        for product in inventory:
            if product.name == product_name:
                item_price = product.price
                total += item_price * quantity
                print("{:<20s}{:>10.2f}{:>10d}".format(product_name, item_price, quantity))
    print("-" * 50)
    print(f"Total: {total:.2f}")
    return total

# Function to generate QR code with safe filename
def generate_qr(data, filename):
    filename = filename.replace(" ", "_").strip("_")
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    if not os.path.exists("qr_codes"):
        os.makedirs("qr_codes")
    img.save(f"qr_codes/{filename}.png")
    print(f"QR code saved to qr_codes/{filename}.png")

# Function to insert order data into MongoDB
def insert_order_to_db(customer_name, order, total, timestamp):
    # Establish MongoDB connection
    client = MongoClient("mongodb+srv://randi:KboUc2P0KVAoOptx@kalki.ow7yktj.mongodb.net/?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE")
    db = client['bakery']  # Database name
    collection = db['orders']  # Collection name
    
    # Create order document
    order_document = {
        "customer_name": customer_name,
        "order": order,
        "total": total,
        "timestamp": timestamp
    }
    
    # Insert document into MongoDB
    collection.insert_one(order_document)
    print("Order data saved to MongoDB.")

# Main program
def main():
    # Sample inventory (replace with your actual data)
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

    # Prompt customer for name
    customer_name = input("Enter customer name: ")

    # Take order
    print("\nWelcome to the Bakery!")
    order = take_order(inventory)

    if order:
        # Calculate bill
        bill_amount = calculate_bill(order, inventory)
        print("\nThank you for your order!")

        # Generate order data for QR code
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        order_data = f"Customer: {customer_name}\nDate & Time: {current_time}\nOrder: {order}\nTotal: {bill_amount}"

        # Generate and save QR code
        generate_qr(order_data, f"{customer_name}_{current_time}")

        # Insert order into MongoDB
        insert_order_to_db(customer_name, order, bill_amount, current_time)

if __name__ == "__main__":
    main()
