from database.db import get_connection
from datetime import datetime

# --------------------------- UPDATE PRODUCT STOCK ---------------------------
def update_product_stock(cursor, product_id):
    """Recalculate stock for a product based on all batches."""
    cursor.execute("""
        SELECT SUM(remaining_quantity)
        FROM purchase_batches
        WHERE product_id=?
    """, (product_id,))
    new_stock = cursor.fetchone()[0] or 0

    cursor.execute(
        "UPDATE products SET stock=? WHERE id=?",
        (new_stock, product_id)
    )


# --------------------------- ADD PURCHASE (BATCH-AWARE) ---------------------------
def add_purchase(name, brand, category, quantity, cost_price, discount, selling_price):
    quantity = int(quantity)
    cost_price = float(cost_price)
    discount = float(discount or 0)
    selling_price = float(selling_price)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        total = (cost_price * quantity) - discount

        # Save purchase record
        cursor.execute("""
            INSERT INTO purchases
            (product_name, brand, category, quantity, cost_price, discount, total, selling_price, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, brand, category, quantity, cost_price, discount, total, selling_price, datetime.now()))

        # Get or create product (check if not permanently deleted)
        cursor.execute("""
            SELECT p.id 
            FROM products p
            LEFT JOIN deleted_products dp ON dp.product_id = p.id AND dp.action = 'PERMANENTLY DELETED' AND dp.source = 'product'
            WHERE p.name=? AND p.brand=? AND dp.id IS NULL
        """, (name, brand))
        product = cursor.fetchone()

        if product:
            product_id = product[0]
            # Only update category, NOT other fields
            cursor.execute("""
                UPDATE products
                SET category=?
                WHERE id=?
            """, (category, product_id))
        else:
            cursor.execute("""
                INSERT INTO products (name, brand, cost_price, selling_price, stock, category)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, brand, cost_price, selling_price, 0, category))
            product_id = cursor.lastrowid

        # Create batch
        cursor.execute("""
            INSERT INTO purchase_batches
            (product_id, quantity, remaining_quantity, cost_price, selling_price, discount, date, action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (product_id, quantity, quantity, cost_price, selling_price, discount, datetime.now(), "added"))

        batch_id = cursor.lastrowid

        # Recalculate stock
        update_product_stock(cursor, product_id)

        conn.commit()
        return batch_id

    finally:
        conn.close()


# --------------------------- UPDATE BATCH ONLY ---------------------------
def update_product(batch_id, name, brand, category, quantity, cost_price, discount, selling_price):
    quantity = int(quantity)
    cost_price = float(cost_price)
    discount = float(discount or 0)
    selling_price = float(selling_price)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Get linked product_id
        cursor.execute(
            "SELECT product_id FROM purchase_batches WHERE id=?",
            (batch_id,)
        )
        result = cursor.fetchone()

        if not result:
            raise ValueError("Batch not found")

        product_id = result[0]

        # Archive old batch data
        cursor.execute("""
            SELECT quantity, remaining_quantity, cost_price, selling_price, discount, date, action
            FROM purchase_batches
            WHERE id=?
        """, (batch_id,))
        old = cursor.fetchone()
        if old:
            cursor.execute("""
                INSERT INTO deleted_products
                (name, brand, cost_price, selling_price, stock, category, discount, action, product_id, source, batch_id, batch_quantity, batch_remaining)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, brand, old[2], old[3], old[1], category, old[4], "updated", product_id, "product", batch_id, old[0], old[1]))

        # Update only the batch record
        cursor.execute("""
            UPDATE purchase_batches
            SET quantity=?, remaining_quantity=?, cost_price=?, selling_price=?, discount=?, date=?, action=?
            WHERE id=?
        """, (quantity, quantity, cost_price, selling_price, discount, datetime.now(), "updated", batch_id))

        # Update only category in products table
        cursor.execute("""
            UPDATE products
            SET category=?
            WHERE id=?
        """, (category, product_id))

        # Recalculate stock
        update_product_stock(cursor, product_id)

        conn.commit()
    finally:
        conn.close()


# --------------------------- GET ALL PURCHASES (FIXED - EXCLUDE ONLY PERMANENTLY DELETED PRODUCTS) ---------------------------
def get_all_purchases():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # FIXED: Only exclude products that are PERMANENTLY DELETED as a WHOLE PRODUCT
        # Not batches that were permanently deleted
        cursor.execute("""
            SELECT b.id, p.name, p.brand, p.category,
                   b.quantity, b.remaining_quantity,
                   b.cost_price, b.discount, b.selling_price,
                   (b.cost_price*b.quantity - b.discount) AS total,
                   b.date, b.action
            FROM purchase_batches b
            JOIN products p ON p.id = b.product_id
            WHERE NOT EXISTS (
                SELECT 1 FROM deleted_products dp 
                WHERE dp.product_id = p.id 
                AND dp.action = 'PERMANENTLY DELETED' 
                AND dp.source = 'product'
            )
            ORDER BY b.date DESC
        """)
        rows = cursor.fetchall()
        print(f"Found {len(rows)} batches in database")  # Debug print
        
        return [
            {
                "batch_id": r[0],
                "name": r[1],
                "brand": r[2],
                "category": r[3],
                "quantity": r[4],
                "remaining_quantity": r[5],
                "cost_price": r[6],
                "discount": r[7],
                "selling_price": r[8],
                "total_cost": r[9],
                "date": r[10],
                "action": r[11]
            }
            for r in rows
        ]
    finally:
        conn.close()


# --------------------------- GET PURCHASES BY DATE RANGE (FIXED) ---------------------------
def get_purchases_by_date_range(start_date, end_date):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.id, p.name, p.brand, p.category,
                   b.quantity, b.remaining_quantity,
                   b.cost_price, b.discount, b.selling_price,
                   (b.cost_price*b.quantity - b.discount) AS total,
                   b.date, b.action
            FROM purchase_batches b
            JOIN products p ON p.id = b.product_id
            WHERE DATE(b.date) BETWEEN ? AND ?
            AND NOT EXISTS (
                SELECT 1 FROM deleted_products dp 
                WHERE dp.product_id = p.id 
                AND dp.action = 'PERMANENTLY DELETED' 
                AND dp.source = 'product'
            )
            ORDER BY b.date DESC
        """, (start_date, end_date))
        rows = cursor.fetchall()
        return [
            {
                "batch_id": r[0],
                "name": r[1],
                "brand": r[2],
                "category": r[3],
                "quantity": r[4],
                "remaining_quantity": r[5],
                "cost_price": r[6],
                "discount": r[7],
                "selling_price": r[8],
                "total_cost": r[9],
                "date": r[10],
                "action": r[11]
            }
            for r in rows
        ]
    finally:
        conn.close()


# --------------------------- AUTOCOMPLETE SUGGESTIONS (FIXED) ---------------------------
def get_product_suggestions(keyword):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT p.name, p.brand, p.category
            FROM products p
            WHERE p.name LIKE ? 
            AND NOT EXISTS (
                SELECT 1 FROM deleted_products dp 
                WHERE dp.product_id = p.id 
                AND dp.action = 'PERMANENTLY DELETED' 
                AND dp.source = 'product'
            )
            ORDER BY p.name ASC
            LIMIT 5
        """, (f"%{keyword}%",))
        results = cursor.fetchall()
        return [
            {"name": r[0], "brand": r[1], "category": r[2] or ""}
            for r in results
        ]
    finally:
        conn.close()


def get_category_suggestions(keyword):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT p.category
            FROM products p
            WHERE p.category LIKE ? 
            AND NOT EXISTS (
                SELECT 1 FROM deleted_products dp 
                WHERE dp.product_id = p.id 
                AND dp.action = 'PERMANENTLY DELETED' 
                AND dp.source = 'product'
            )
            ORDER BY p.category ASC
            LIMIT 5
        """, (f"%{keyword}%",))
        results = cursor.fetchall()
        return [
            {"category": r[0]} for r in results if r[0]
        ]
    finally:
        conn.close()