import sqlite3

DB_NAME = "products.db"

def reduce_stock(product_id):

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    UPDATE products
    SET stock = stock - 1
    WHERE id=?
    """,(product_id,))

    conn.commit()
    conn.close()