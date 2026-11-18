from flask import Flask
from database import create_database
from billing import (
    add_to_cart,
    calculate_total,
    generate_receipt
)

from camera import scan_product

app = Flask(__name__)

create_database()

@app.route("/")
def home():

    return """
    <h1>TrolleyWise Smart Cart</h1>

    <a href='/scan'>
    Scan Product
    </a>

    <br><br>

    <a href='/bill'>
    View Bill
    </a>

    <br><br>

    <a href='/receipt'>
    Receipt
    </a>
    """

@app.route("/scan")
def scan():

    product_id = scan_product()

    if product_id:

        status = add_to_cart(product_id)

        if status:

            return """
            Product Added Successfully
            <br><br>
            <a href='/'>Home</a>
            """

    return """
    Product Not Found
    <br><br>
    <a href='/'>Home</a>
    """

@app.route("/bill")
def bill():

    total = calculate_total()

    return f"""
    <h2>Current Bill</h2>

    ₹{total}

    <br><br>

    <a href='/'>Home</a>
    """

@app.route("/receipt")
def receipt():

    return f"""
    <pre>
    {generate_receipt()}
    </pre>

    <a href='/'>Home</a>
    """

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )