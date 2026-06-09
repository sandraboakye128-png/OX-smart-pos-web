import os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm

from database.db import get_connection

REPORT_FOLDER = "reports"
os.makedirs(REPORT_FOLDER, exist_ok=True)

def generate_sales_report():
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch today's sales with batch info
    cursor.execute("""
        SELECT 
            products.name,
            products.brand,
            sales_items.quantity,
            (sales_items.quantity * sales_items.selling_price) AS total,
            sales_items.profit,
            purchase_batches.id AS batch_id,
            purchase_batches.cost_price,
            sales.date
        FROM sales
        JOIN sales_items ON sales.id = sales_items.sale_id
        JOIN products ON products.id = sales_items.product_id
        JOIN purchase_batches ON purchase_batches.id = sales_items.batch_id
        WHERE DATE(sales.date) = DATE('now','localtime')
        ORDER BY sales.date DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    # Totals
    total_qty = sum(r[2] for r in rows)
    total_sales = sum(r[3] for r in rows)
    total_profit = sum(r[4] for r in rows)

    today_str = datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(REPORT_FOLDER, f"sales_report_{today_str}.pdf")

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Retail System", styles['Title']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Daily Sales Report - {today_str}", styles['Heading2']))
    elements.append(Spacer(1, 15))

    # Summary
    elements.append(Paragraph(f"Total Items Sold: {total_qty}", styles['Normal']))
    elements.append(Paragraph(f"Total Sales: ₵{total_sales:.2f}", styles['Normal']))
    elements.append(Paragraph(f"Total Profit: ₵{total_profit:.2f}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Table data
    table_data = [
        ["Product", "Brand", "Batch", "Qty", "Cost (₵)", "Total (₵)", "Profit (₵)", "Time"]
    ]

    for r in rows:
        time_str = str(r[7]).split(" ")[1] if " " in str(r[7]) else str(r[7])
        table_data.append([
            r[0],
            r[1],
            f"#{r[5]}",
            r[2],
            f"{r[6]:.2f}",
            f"{r[3]:.2f}",
            f"{r[4]:.2f}",
            time_str
        ])

    # Add totals row
    table_data.append([
        "TOTAL", "", "", total_qty, "", f"{total_sales:.2f}", f"{total_profit:.2f}", ""
    ])

    # Column widths
    col_widths = [6*cm, 4*cm, 2*cm, 1.5*cm, 3*cm, 3*cm, 3*cm, 2*cm]

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#00CFCF")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (3,1), (6,-2), "CENTER"),
        ("ALIGN", (3,-1), (6,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
    ]))

    elements.append(table)

    doc = SimpleDocTemplate(filename, pagesize=A4)
    doc.build(elements)

    return filename