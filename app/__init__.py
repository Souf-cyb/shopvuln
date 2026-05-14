from flask import Flask
import sqlite3
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = "shopvuln-super-secret-key-2024"

    db_path = os.path.join(os.path.dirname(__file__), 'shop.db')

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Tables
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            address TEXT,
            phone TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 100,
            category TEXT,
            image_url TEXT
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            address TEXT,
            card_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price REAL
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            user_id INTEGER,
            username TEXT,
            content TEXT,
            rating INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1
        );
    ''')

    # Seed data
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.executescript('''
            INSERT INTO users (username, email, password, role)
            VALUES
                ('admin', 'admin@shopvuln.com', 'admin123', 'admin'),
                ('alice', 'alice@email.com', 'alice123', 'user'),
                ('bob', 'bob@email.com', 'bob123', 'user');

            INSERT INTO products (name, description, price, stock, category, image_url)
            VALUES
                ('Laptop ProSecure X1',
                 'High-performance laptop with hardware encryption, TPM 2.0 and biometric authentication.',
                 1299.99, 50, 'Laptops',
                 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400'),

                ('YubiKey 5 NFC',
                 'Hardware security key supporting FIDO2, WebAuthn, OTP. Compatible with most platforms.',
                 55.00, 200, 'Security Keys',
                 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400'),

                ('Encrypted USB Drive 256GB',
                 'Military-grade AES-256 hardware encrypted USB drive with PIN protection.',
                 89.99, 150, 'Storage',
                 'https://images.unsplash.com/photo-1618424181497-157f25b6ddd5?w=400'),

                ('Network Security Camera',
                 'IP security camera with end-to-end encryption, local storage and VPN support.',
                 199.99, 75, 'Surveillance',
                 'https://images.unsplash.com/photo-1557597774-9d273605dfa9?w=400'),

                ('Firewall Appliance Mini',
                 'Compact hardware firewall for home and small business. Supports pfSense and OPNsense.',
                 349.99, 30, 'Network',
                 'https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=400'),

                ('Privacy Screen Filter 15.6"',
                 'Anti-spy privacy filter for laptops. Blocks side-angle viewing up to 60 degrees.',
                 34.99, 300, 'Accessories',
                 'https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400');

            INSERT INTO reviews (product_id, user_id, username, content, rating)
            VALUES
                (1, 2, 'alice', 'Excellent laptop, very fast and secure!', 5),
                (2, 3, 'bob', 'Perfect for 2FA, works great with GitHub.', 5),
                (3, 2, 'alice', 'Reliable and easy to use.', 4);
        ''')

    conn.commit()
    conn.close()

    from app.routes import main
    app.register_blueprint(main)

    return app