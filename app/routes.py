from flask import (Blueprint, request, render_template,
                   session, redirect, url_for, jsonify)
import sqlite3, os, json

main = Blueprint('main', __name__)
DB   = os.path.join(os.path.dirname(__file__), 'shop.db')

def db():
    return sqlite3.connect(DB)

# ══════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════
@main.route('/')
def index():
    conn = db()
    products = conn.execute(
        "SELECT * FROM products LIMIT 6"
    ).fetchall()
    conn.close()
    return render_template('index.html', products=products)

# ══════════════════════════════════════════════
# AUTH — LOGIN (SQLi volontaire)
# ══════════════════════════════════════════════
@main.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        u = request.form.get('username','')
        p = request.form.get('password','')
        conn = db()
        # FAILLE SQLi
        query = f"SELECT * FROM users WHERE username='{u}' AND password='{p}'"
        user  = conn.execute(query).fetchone()
        conn.close()
        if user:
            session['user_id']  = user[0]
            session['username'] = user[1]
            session['role']     = user[4]
            return redirect(url_for('main.index'))
        error = "Invalid username or password."
    return render_template('login.html', error=error)

# ══════════════════════════════════════════════
# AUTH — REGISTER (XSS volontaire)
# ══════════════════════════════════════════════
@main.route('/register', methods=['GET','POST'])
def register():
    error = None
    if request.method == 'POST':
        u = request.form.get('username','')
        e = request.form.get('email','')
        p = request.form.get('password','')
        conn = db()
        try:
            conn.execute(
                "INSERT INTO users (username,email,password) VALUES (?,?,?)",
                (u, e, p)   # FAILLE : mot de passe en clair
            )
            conn.commit()
            return redirect(url_for('main.login'))
        except:
            error = "Username or email already exists."
        finally:
            conn.close()
    return render_template('register.html', error=error)

# ══════════════════════════════════════════════
# LOGOUT
# ══════════════════════════════════════════════
@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

# ══════════════════════════════════════════════
# PRODUCTS — SEARCH (SQLi volontaire)
# ══════════════════════════════════════════════
@main.route('/products')
def products():
    q    = request.args.get('q', '')
    conn = db()
    if q:
        # FAILLE SQLi
        rows = conn.execute(
            f"SELECT * FROM products WHERE name LIKE '%{q}%' OR description LIKE '%{q}%'"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template('products.html', products=rows, query=q)

# ══════════════════════════════════════════════
# PRODUCT DETAIL + REVIEWS (XSS volontaire)
# ══════════════════════════════════════════════
@main.route('/product/<int:pid>')
def product_detail(pid):
    conn    = db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    reviews = conn.execute("SELECT * FROM reviews WHERE product_id=?", (pid,)).fetchall()
    conn.close()
    return render_template('product_detail.html', product=product, reviews=reviews)

@main.route('/product/<int:pid>/review', methods=['POST'])
def add_review(pid):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    content = request.form.get('content', '')
    rating  = request.form.get('rating', 5)
    conn    = db()
    # FAILLE XSS : contenu non échappé stocké tel quel
    conn.execute(
        "INSERT INTO reviews (product_id,user_id,username,content,rating) VALUES (?,?,?,?,?)",
        (pid, session['user_id'], session['username'], content, rating)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('main.product_detail', pid=pid))

# ══════════════════════════════════════════════
# CART
# ══════════════════════════════════════════════
@main.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    conn  = db()
    items = conn.execute('''
        SELECT p.id, p.name, p.price, p.image_url, c.quantity
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    total = sum(i[2] * i[4] for i in items)
    return render_template('cart.html', items=items, total=total)

@main.route('/cart/add/<int:pid>', methods=['POST'])
def add_to_cart(pid):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    conn = db()
    existing = conn.execute(
        "SELECT id, quantity FROM cart WHERE user_id=? AND product_id=?",
        (session['user_id'], pid)
    ).fetchone()
    if existing:
        conn.execute("UPDATE cart SET quantity=? WHERE id=?",
                     (existing[1]+1, existing[0]))
    else:
        conn.execute("INSERT INTO cart (user_id,product_id,quantity) VALUES (?,?,1)",
                     (session['user_id'], pid))
    conn.commit()
    conn.close()
    return redirect(url_for('main.cart'))

@main.route('/cart/remove/<int:pid>', methods=['POST'])
def remove_from_cart(pid):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    conn = db()
    conn.execute("DELETE FROM cart WHERE user_id=? AND product_id=?",
                 (session['user_id'], pid))
    conn.commit()
    conn.close()
    return redirect(url_for('main.cart'))

# ══════════════════════════════════════════════
# CHECKOUT (données sensibles en clair)
# ══════════════════════════════════════════════
@main.route('/checkout', methods=['GET','POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    conn  = db()
    items = conn.execute('''
        SELECT p.id, p.name, p.price, p.image_url, c.quantity
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (session['user_id'],)).fetchall()
    total = sum(i[2] * i[4] for i in items)

    if request.method == 'POST':
        address     = request.form.get('address','')
        card_number = request.form.get('card_number','')
        # FAILLE : numéro de carte stocké en clair
        conn.execute(
            "INSERT INTO orders (user_id,total,status,address,card_number) VALUES (?,?,?,?,?)",
            (session['user_id'], total, 'confirmed', address, card_number)
        )
        order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for item in items:
            conn.execute(
                "INSERT INTO order_items (order_id,product_id,quantity,price) VALUES (?,?,?,?)",
                (order_id, item[0], item[4], item[2])
            )
        conn.execute("DELETE FROM cart WHERE user_id=?", (session['user_id'],))
        conn.commit()
        conn.close()
        return redirect(url_for('main.orders'))

    conn.close()
    return render_template('checkout.html', items=items, total=total)

# ══════════════════════════════════════════════
# ORDERS — IDOR volontaire
# ══════════════════════════════════════════════
@main.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    conn = db()
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return render_template('orders.html', orders=rows)

@main.route('/order/<int:oid>')
def order_detail(oid):
    # FAILLE IDOR : pas de vérification que l'ordre appartient à l'utilisateur
    conn  = db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    items = conn.execute('''
        SELECT p.name, oi.quantity, oi.price
        FROM order_items oi JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', (oid,)).fetchall()
    conn.close()
    return render_template('orders.html', order=order, items=items)

# ══════════════════════════════════════════════
# ADMIN — Broken Access Control volontaire
# ══════════════════════════════════════════════
@main.route('/admin')
def admin():
    # FAILLE : vérification côté client uniquement
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    conn  = db()
    users  = conn.execute("SELECT * FROM users").fetchall()
    orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('admin.html', users=users, orders=orders)

# ══════════════════════════════════════════════
# API — Sans authentification (volontaire)
# ══════════════════════════════════════════════
@main.route('/api/products')
def api_products():
    conn = db()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return jsonify([{
        "id": r[0], "name": r[1], "description": r[2],
        "price": r[3], "stock": r[4], "category": r[5]
    } for r in rows])

@main.route('/api/users')
def api_users():
    # FAILLE : exposition des mots de passe sans auth
    conn = db()
    rows = conn.execute("SELECT id,username,email,password,role FROM users").fetchall()
    conn.close()
    return jsonify([{
        "id": r[0], "username": r[1],
        "email": r[2], "password": r[3], "role": r[4]
    } for r in rows])

@main.route('/api/orders')
def api_orders():
    # FAILLE : exposition des numéros de carte sans auth
    conn = db()
    rows = conn.execute("SELECT * FROM orders").fetchall()
    conn.close()
    return jsonify([{
        "id": r[0], "user_id": r[1], "total": r[2],
        "status": r[3], "card_number": r[5]
    } for r in rows])