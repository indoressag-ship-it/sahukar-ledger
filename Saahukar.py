import os
import re
import sqlite3
import shutil
from datetime import datetime
import streamlit as st

# PDF Generation Library
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ==========================================
# 1. DATABASE & CONFIG SETUP
# ==========================================
DB_NAME = "sahukar_ledger_pro.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            address TEXT,
            gov_id TEXT,
            principal REAL NOT NULL,
            interest_rate REAL NOT NULL,
            loan_date TEXT NOT NULL,
            collateral TEXT,
            gold_weight REAL,
            photo_path TEXT,
            notes TEXT,
            status TEXT DEFAULT 'ACTIVE'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            payment_date TEXT NOT NULL,
            total_paid REAL NOT NULL,
            interest_paid REAL NOT NULL,
            principal_paid REAL NOT NULL,
            remaining_principal REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')
    conn.commit()
    conn.close()

def sanitize_filename(name):
    clean = re.sub(r'[^\w\s-]', '', name).strip()
    clean = re.sub(r'[-\s]+', '_', clean)
    return clean if clean else "Customer"

def calculate_interest(principal, rate, loan_date_str):
    try:
        loan_date = datetime.strptime(loan_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        days = (today - loan_date).days
        if days < 0:
            days = 0
        interest = (principal * rate * days) / 3000.0
        return days, round(interest, 2), round(principal + interest, 2)
    except Exception:
        return 0, 0.0, principal

def generate_pdf_receipt(filename, cust, date_str, paid_amt, int_paid, princ_paid, rem_princ, payment_seq):
    if not HAS_REPORTLAB:
        return False

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    elements = []
    styles = getSampleStyleSheet()

    PRIMARY_COLOR = colors.HexColor("#1e293b")
    SECONDARY_COLOR = colors.HexColor("#2563eb")
    TEXT_MUTED = colors.HexColor("#64748b")

    style_header_title = ParagraphStyle('HeaderTitle', fontName='Helvetica-Bold', fontSize=18, textColor=colors.white, alignment=0)
    style_header_sub = ParagraphStyle('HeaderSub', fontName='Helvetica', fontSize=10, textColor=colors.HexColor("#93c5fd"), alignment=0)
    style_receipt_id = ParagraphStyle('ReceiptID', fontName='Helvetica-Bold', fontSize=12, textColor=colors.white, alignment=2)
    style_receipt_date = ParagraphStyle('ReceiptDate', fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#cbd5e1"), alignment=2)

    header_data = [
        [
            Paragraph("<b>SAHUKAR LEDGER PRO</b>", style_header_title),
            Paragraph(f"<b>PAYMENT RECEIPT</b><br/>Receipt No: #{payment_seq:04d}", style_receipt_id)
        ],
        [
            Paragraph("Authorized Loan & Ledger Management System", style_header_sub),
            Paragraph(f"Date: {date_str} | Time: {datetime.now().strftime('%I:%M %p')}", style_receipt_date)
        ]
    ]
    header_table = Table(header_data, colWidths=[330, 222])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    style_sec_heading = ParagraphStyle('SecHeading', fontName='Helvetica-Bold', fontSize=11, textColor=SECONDARY_COLOR, spaceAfter=4)
    style_cell_label = ParagraphStyle('CellLabel', fontName='Helvetica-Bold', fontSize=9, textColor=PRIMARY_COLOR)
    style_cell_val = ParagraphStyle('CellVal', fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#334155"))

    cust_info_data = [
        [Paragraph("<b>CUSTOMER DETAILS</b>", style_sec_heading), Paragraph("<b>LOAN SUMMARY</b>", style_sec_heading)],
        [Paragraph("Customer ID:", style_cell_label), Paragraph(f"#{cust['id']}", style_cell_val), Paragraph("Initial Principal:", style_cell_label), Paragraph(f"INR {cust['principal']:,.2f}", style_cell_val)],
        [Paragraph("Name:", style_cell_label), Paragraph(str(cust['name']), style_cell_val), Paragraph("Interest Rate:", style_cell_label), Paragraph(f"{cust['rate']}% / month", style_cell_val)],
        [Paragraph("Mobile:", style_cell_label), Paragraph(str(cust['mobile']), style_cell_val), Paragraph("Days Elapsed:", style_cell_label), Paragraph(f"{cust['days']} Days", style_cell_val)],
        [Paragraph("Address:", style_cell_label), Paragraph(str(cust['address']), style_cell_val), Paragraph("Accrued Interest:", style_cell_label), Paragraph(f"INR {cust['interest']:,.2f}", style_cell_val)],
        [Paragraph("Govt ID:", style_cell_label), Paragraph(str(cust['gov_id']), style_cell_val), Paragraph("Collateral Item:", style_cell_label), Paragraph(str(cust['collateral']), style_cell_val)]
    ]
    cust_table = Table(cust_info_data, colWidths=[90, 186, 110, 166])
    cust_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (2, 0), (3, 0)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    elements.append(cust_table)
    elements.append(Spacer(1, 15))

    style_t_head = ParagraphStyle('THead', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)
    style_t_cell = ParagraphStyle('TCell', fontName='Helvetica', fontSize=9, textColor=PRIMARY_COLOR)

    pay_table_data = [
        [Paragraph("Description", style_t_head), Paragraph("Amount Paid", style_t_head)],
        [Paragraph("Interest Payment Settled", style_t_cell), Paragraph(f"INR {int_paid:,.2f}", style_t_cell)],
        [Paragraph("Principal Deduction Settled", style_t_cell), Paragraph(f"INR {princ_paid:,.2f}", style_t_cell)],
        [Paragraph("<b>TOTAL AMOUNT RECEIVED</b>", style_t_cell), Paragraph(f"<b>INR {paid_amt:,.2f}</b>", style_t_cell)]
    ]
    pay_table = Table(pay_table_data, colWidths=[380, 172])
    pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SECONDARY_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
    ]))
    elements.append(pay_table)
    elements.append(Spacer(1, 15))

    rem_text = f"<b>REMAINING PRINCIPAL BALANCE: INR {rem_princ:,.2f}</b>"
    style_rem = ParagraphStyle('RemStyle', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#dc2626"), alignment=2)
    elements.append(Paragraph(rem_text, style_rem))
    elements.append(Spacer(1, 20))

    footer_p = Paragraph("This is a computer-generated receipt. No signature required.", ParagraphStyle('Foot', fontName='Helvetica-Oblique', fontSize=8, textColor=TEXT_MUTED, alignment=1))
    elements.append(footer_p)

    doc.build(elements)
    return True

# Initialize Database
init_db()

# Page Configuration
st.set_page_config(page_title="Sahukar Ledger Pro", layout="wide")
st.title("💼 Sahukar Ledger Pro (साहूकार लेजर प्रो)")

# Sidebar Menu
menu = ["📊 डैशबोर्ड", "➕ ग्राहक जोड़ें", "📜 ग्राहक निर्देशिका", "💳 पार्ट पेमेंट", "📁 बैकअप"]
choice = st.sidebar.selectbox("मेनू चुनें / Choose Menu", menu)

# 1. DASHBOARD
if choice == "📊 डैशबोर्ड":
    st.header("व्यापार का विवरण (Business Overview)")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT principal, interest_rate, loan_date FROM customers WHERE status = 'ACTIVE'")
    rows = cursor.fetchall()
    cursor.execute("SELECT SUM(total_paid) FROM payments")
    paid_res = cursor.fetchone()[0] or 0.0
    conn.close()

    total_cust = len(rows)
    total_principal = sum(r[0] for r in rows)
    total_interest = sum(calculate_interest(r[0], r[1], r[2])[1] for r in rows)
    overdue_count = sum(1 for r in rows if calculate_interest(r[0], r[1], r[2])[0] >= 30)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("कुल सक्रिय ग्राहक", total_cust)
    col2.metric("बकाया मूलधन", f"₹{total_principal:,.2f}")
    col3.metric("कुल देय ब्याज", f"₹{total_interest:,.2f}")
    col4.metric("कुल वसूल राशि", f"₹{paid_res:,.2f}")
    col5.metric("ओवरड्यू (≥30 दिन)", overdue_count)

# 2. ADD CUSTOMER
elif choice == "➕ ग्राहक जोड़ें":
    st.header("नया ग्राहक जोड़ें")
    with st.form("add_customer_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("ग्राहक का नाम*")
            mobile = st.text_input("मोबाइल नंबर*")
            address = st.text_input("पता")
            gov_id = st.text_input("सरकारी पहचान पत्र (Govt ID)")
            notes = st.text_area("नोट्स")
        with col2:
            principal = st.number_input("मूलधन राशि (₹)*", min_value=0.0)
            rate = st.number_input("ब्याज दर (%/माह)*", min_value=0.0, value=2.0)
            loan_date = st.date_input("ऋण तिथि", datetime.now()).strftime("%Y-%m-%d")
            collateral = st.text_input("बंधक/गिरवी सामान")
            weight = st.number_input("सोने का वजन (ग्राम)", min_value=0.0)
        
        submitted = st.form_submit_button("💾 ग्राहक रिकॉर्ड सहेजें")
        if submitted:
            if name and mobile and principal > 0:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO customers (name, mobile, address, gov_id, principal, interest_rate, loan_date, collateral, gold_weight, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, mobile, address, gov_id, principal, rate, loan_date, collateral, weight, notes))
                conn.commit()
                conn.close()
                st.success("नया ग्राहक रिकॉर्ड सफलतापूर्वक सहेजा गया!")
            else:
                st.error("कृपया सभी आवश्यक (*) फ़ील्ड भरें!")

# 3. CUSTOMER DIRECTORY
elif choice == "📜 ग्राहक निर्देशिका":
    st.header("ग्राहक निर्देशिका")
    search_q = st.text_input("खोजें (नाम या मोबाइल नंबर):")
    show_overdue = st.checkbox("केवल ओवरड्यू (≥30 दिन) दिखाएं")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if search_q:
        cursor.execute("SELECT id, name, mobile, principal, interest_rate, loan_date FROM customers WHERE (name LIKE ? OR mobile LIKE ?) AND status = 'ACTIVE'", (f"%{search_q}%", f"%{search_q}%"))
    else:
        cursor.execute("SELECT id, name, mobile, principal, interest_rate, loan_date FROM customers WHERE status = 'ACTIVE'")
    
    rows = cursor.fetchall()
    conn.close()

    data = []
    for r in rows:
        cid, name, mobile, principal, rate, loan_date = r
        days, interest, total = calculate_interest(principal, rate, loan_date)
        if show_overdue and days < 30:
            continue
        data.append({
            "ID": cid,
            "नाम": name,
            "मोबाइल": mobile,
            "मूलधन": f"₹{principal:,.2f}",
            "ब्याज दर": f"{rate}%",
            "दिन": days,
            "ब्याज": f"₹{interest:,.2f}",
            "कुल देय": f"₹{total:,.2f}"
        })

    if data:
        st.dataframe(data, use_container_width=True)
    else:
        st.info("कोई रिकॉर्ड नहीं मिला।")

# 4. PART PAYMENT
elif choice == "💳 पार्ट पेमेंट":
    st.header("पार्ट पेमेंट दर्ज करें एवं PDF रसीद जनरेट करें")
    cid = st.number_input("ग्राहक ID दर्ज करें:", min_value=1, step=1)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, mobile, address, gov_id, principal, interest_rate, loan_date, collateral FROM customers WHERE id = ? AND status = 'ACTIVE'", (cid,))
    row = cursor.fetchone()
    conn.close()

    if row:
        cid, name, mobile, address, gov_id, principal, rate, loan_date, collateral = row
        days, interest, total = calculate_interest(principal, rate, loan_date)

        st.info(f"👤 **नाम:** {name} | 📱 **मोबाइल:** {mobile} | 💰 **मूलधन:** ₹{principal:,.2f} | 📅 **दिन:** {days} | 📈 **ब्याज:** ₹{interest:,.2f} | 📌 **कुल:** ₹{total:,.2f}")

        paid_amt = st.number_input("भुगतान राशि (₹):", min_value=1.0)
        if st.button("💳 भुगतान सहेजें एवं PDF बनाएं"):
            if paid_amt <= interest:
                int_paid = paid_amt
                princ_paid = 0.0
            else:
                int_paid = interest
                princ_paid = paid_amt - interest

            new_principal = round(principal - princ_paid, 2)
            today_str = datetime.now().strftime("%Y-%m-%d")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM payments WHERE customer_id = ?", (cid,))
            seq = (cursor.fetchone()[0] or 0) + 1

            if new_principal <= 0:
                cursor.execute("UPDATE customers SET principal = 0, status = 'CLOSED' WHERE id = ?", (cid,))
                new_principal = 0.0
            else:
                cursor.execute("UPDATE customers SET principal = ?, loan_date = ? WHERE id = ?", (new_principal, today_str, cid))

            cursor.execute('''
                INSERT INTO payments (customer_id, payment_date, total_paid, interest_paid, principal_paid, remaining_principal)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (cid, today_str, paid_amt, int_paid, princ_paid, new_principal))
            conn.commit()
            conn.close()

            # Generate PDF
            receipts_dir = "payments_receipts"
            os.makedirs(receipts_dir, exist_ok=True)
            safe_name = sanitize_filename(name)
            pdf_path = os.path.join(receipts_dir, f"{safe_name}_Receipt_{seq}.pdf")

            cust_dict = {"id": cid, "name": name, "mobile": mobile, "address": address, "gov_id": gov_id, "principal": principal, "rate": rate, "days": days, "interest": interest, "collateral": collateral}
            generate_pdf_receipt(pdf_path, cust_dict, today_str, paid_amt, int_paid, princ_paid, new_principal, seq)

            st.success(f"भुगतान सफलतापूर्वक दर्ज हुआ! PDF रसीद `{pdf_path}` पर सहेजी गई।")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 PDF रसीद डाउनलोड करें", f, file_name=os.path.basename(pdf_path))
    else:
        st.warning("कृपया मान्य ग्राहक ID दर्ज करें।")

# 5. BACKUP
elif choice == "📁 बैकअप":
    st.header("डेटाबेस बैकअप")
    if st.button("📁 पूरा डेटाबेस बैकअप बनाएं"):
        backup_dir = "database_backups"
        os.makedirs(backup_dir, exist_ok=True)
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        dest = os.path.join(backup_dir, filename)
        shutil.copyfile(DB_NAME, dest)
        st.success(f"डेटाबेस बैकअप बन गया: `{dest}`")
