import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, abort

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DATABASE = Path(__file__).with_name("shop.db")

#this is a new comment
def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_db_connection()
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)

    count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        sample_products = [
            ("Notebook", 50, "A ruled notebook suitable for everyday notes and classwork."),
            ("Pen", 10, "A smooth-writing blue ballpoint pen."),
            ("School Bag", 650, "A spacious school bag with multiple compartments."),
            ("Water Bottle", 150, "A reusable water bottle for school, office and travel."),
            ("Pencil Box", 100, "A handy pencil box to organize stationery.")
        ]
        connection.executemany(
            "INSERT INTO products (name, price, description) VALUES (?, ?, ?)",
            sample_products
        )
    connection.commit()
    connection.close()


@app.route("/")
def home():
    connection = get_db_connection()
    products = connection.execute("SELECT * FROM products ORDER BY id").fetchall()
    connection.close()
    return render_template("home.html", products=products)


@app.route("/product/<int:id>")
def product_details(id):
    connection = get_db_connection()
    product = connection.execute(
        "SELECT * FROM products WHERE id = ?", (id,)
    ).fetchone()
    connection.close()
    if product is None:
        return render_template("not_found.html", message="The product you requested was not found."), 404
    return render_template("product.html", product=product)


@app.route("/order/<int:id>", methods=["GET", "POST"])
def order(id):
    connection = get_db_connection()
    product = connection.execute(
        "SELECT * FROM products WHERE id = ?", (id,)
    ).fetchone()

    if product is None:
        connection.close()
        return render_template("not_found.html", message="The product you requested was not found."), 404

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        quantity_text = request.form.get("quantity", "").strip()

        if not customer_name:
            flash("Please enter your name.", "error")
            connection.close()
            return render_template("order.html", product=product), 400

        try:
            quantity = int(quantity_text)
            if quantity <= 0:
                raise ValueError
        except (TypeError, ValueError):
            flash("Quantity must be a positive whole number.", "error")
            connection.close()
            return render_template("order.html", product=product), 400

        cursor = connection.execute(
            "INSERT INTO orders (customer_name, product_id, quantity) VALUES (?, ?, ?)",
            (customer_name, id, quantity)
        )
        order_id = cursor.lastrowid
        connection.commit()
        connection.close()
        return redirect(url_for("confirmation", id=order_id))

    connection.close()
    return render_template("order.html", product=product)


@app.route("/confirmation/<int:id>")
def confirmation(id):
    connection = get_db_connection()
    saved_order = connection.execute("""
        SELECT orders.id, orders.customer_name, orders.quantity,
               products.id AS product_id, products.name AS product_name,
               products.price AS price
        FROM orders
        JOIN products ON orders.product_id = products.id
        WHERE orders.id = ?
    """, (id,)).fetchone()
    connection.close()

    if saved_order is None:
        return render_template("not_found.html", message="The order you requested was not found."), 404

    total = saved_order["price"] * saved_order["quantity"]
    return render_template("confirmation.html", order=saved_order, total=total)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("not_found.html", message="The page you requested does not exist."), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
#this is a comment