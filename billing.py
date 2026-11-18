from database import get_product
from inventory import reduce_stock

cart = []

def add_to_cart(product_id):

    product = get_product(product_id)

    if product:

        cart.append({
            "id":product[0],
            "name":product[1],
            "price":product[2]
        })

        reduce_stock(product_id)

        return True

    return False


def calculate_total():

    total = 0

    for item in cart:
        total += item["price"]

    return total


def generate_receipt():

    total = calculate_total()

    receipt = "\n===== TROLLEYWISE RECEIPT =====\n"

    for item in cart:

        receipt += (
            f"{item['name']}  ₹{item['price']}\n"
        )

    receipt += "--------------------------\n"
    receipt += f"TOTAL : ₹{total}\n"

    return receipt