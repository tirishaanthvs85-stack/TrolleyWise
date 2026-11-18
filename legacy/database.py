import sqlite3

DB_NAME = "products.db"

def create_database():

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY,
        name TEXT,
        price REAL,
        stock INTEGER
    )
    """)

    products = [
        (1,"Milk",45,100),
        (2,"Bread",30,80),
        (3,"Rice",65,120),
        (4,"Soap",25,150),
        (5,"Chocolate",20,200)
    ]

    cur.executemany(
        "INSERT OR REPLACE INTO products VALUES(?,?,?,?)",
        products
    )

    conn.commit()
    conn.close()


def get_product(product_id):

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM products WHERE id=?",
        (product_id,)
    )

    row = cur.fetchone()

    conn.close()

    return row