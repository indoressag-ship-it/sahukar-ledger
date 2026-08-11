import os
import re
import sqlite3
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime

# PDF Generation Library
try:
    from reportlab.lib.pagesizes import letter, A6
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ==========================================
# 1. DATABASE, SECURITY & CONFIG SETUP
# ==========================================
DB_NAME = "sahukar_ledger_pro.db"
PIN_FILE = "app_pin.txt"
LANG_FILE = "app_lang.txt"

def get_saved_pin():
    if not os.path.exists(PIN_FILE):
        with open(PIN_FILE, "w") as f:
            f.write("1234")
        return "1234"
    with open(PIN_FILE, "r") as f:
        return f.read().strip()

def save_new_pin(new_pin):
    with open(PIN_FILE, "w") as f:
        f.write(new_pin.strip())

def get_saved_lang():
    if not os.path.exists(LANG_FILE):
        with open(LANG_FILE, "w") as f:
            f.write("HI")
        return "HI"
    with open(LANG_FILE, "r") as f:
        return f.read().strip()

def save_lang(lang):
    with open(LANG_FILE, "w") as f:
        f.write(lang)

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

# Helper function to create clean file names
def sanitize_filename(name):
    clean = re.sub(r'[^\w\s-]', '', name).strip()
    clean = re.sub(r'[-\s]+', '_', clean)
    return clean if clean else "Customer"

# Translations Dictionary
I18N = {
    "HI": {
        "title": "Sahukar Ledger Pro (साहूकार लेजर प्रो)",
        "tab_dash": " 📊 डैशबोर्ड ",
        "tab_add": " ➕ ग्राहक जोड़ें ",
        "tab_dir": " 📜 ग्राहक निर्देशिका ",
        "tab_pay": " 💳 पार्ट पेमेंट ",
        "tab_tools": " ⚙️ बैकअप व टूल्स ",
        "biz_overview": "व्यापार का विवरण (Business Overview)",
        "card_cust": "कुल सक्रिय ग्राहक",
        "card_princ": "बकाया मूलधन (Principal)",
        "card_int": "कुल देय ब्याज (Interest)",
        "card_rec": "कुल वसूल की गई राशि",
        "card_overdue": "ओवरड्यू खाते (≥30 दिन)",
        "btn_refresh": "↻ डैशबोर्ड रिफ्रेश करें",
        "cust_due": "ग्राहक देय हैं",
        "lbl_name": "ग्राहक का नाम*",
        "lbl_mobile": "मोबाइल नंबर*",
        "lbl_addr": "पता",
        "lbl_govid": "सरकारी पहचान पत्र (Govt ID)",
        "lbl_princ": "मूलधन राशि (₹)*",
        "lbl_rate": "ब्याज दर (%/माह)*",
        "lbl_date": "ऋण तिथि (YYYY-MM-DD)*",
        "lbl_collat": "बंधक/गिरवी सामान",
        "lbl_weight": "सोने का वजन (ग्राम)",
        "lbl_notes": "नोट्स",
        "lbl_photo": "सामान/सोने की फोटो",
        "btn_browse": "ब्राउज़ करें",
        "btn_save_cust": "💾 ग्राहक रिकॉर्ड सहेजें",
        "search_lbl": "खोजें (नाम/मोबाइल):",
        "btn_search": "🔍 खोजें",
        "btn_overdue": "🚨 ओवरड्यू दिखाएं (≥30 दिन)",
        "btn_reset": "रीसेट",
        "cust_id": "ग्राहक आईडी:",
        "btn_fetch": "विवरण लोड करें",
        "pay_prompt": "कृपया ग्राहक आईडी दर्ज करके विवरण लोड करें।",
        "paid_amt": "भुगतान राशि (₹):",
        "btn_pay_pdf": "💳 पार्ट पेमेंट दर्ज करें व PDF रसीद जनरेट करें",
        "backup_sec": "डेटाबेस बैकअप एवं रखरखाव",
        "btn_backup": "📁 पूरा डेटाबेस बैकअप बनाएं",
        "sec_sec": "सुरक्षा सेटिंग्स",
        "btn_change_pin": "🔑 सुरक्षा PIN बदलें",
        "pin_prompt": "4-अंकों का सुरक्षा PIN दर्ज करें:",
        "pin_err": "गलत PIN! एप्लिकेशन बंद हो रहा है।",
        "fill_req": "कृपया सभी आवश्यक (*) फ़ील्ड भरें!",
        "invalid_input": "अमान्य इनपुट या तारीख (YYYY-MM-DD) सही करें!",
        "cust_saved": "नया ग्राहक रिकॉर्ड सफलतापूर्वक सहेजा गया!",
        "enter_valid_id": "वैध ग्राहक ID दर्ज करें!",
        "cust_not_found": "ग्राहक नहीं मिला!",
        "enter_valid_amt": "वैध भुगतान राशि दर्ज करें!",
        "pay_success": "भुगतान सफलतापूर्वक दर्ज किया गया!\nPDF रसीद 'payments_receipts' फोल्डर में सेव हुई: ",
        "db_not_found": "डेटाबेस फ़ाइल मौजूद नहीं है!",
        "backup_success": "डेटाबेस बैकअप सफलतापूर्वक बनाया गया:\n",
        "old_pin": "पुराना PIN:",
        "new_pin": "नया 4-अंकीय PIN:",
        "conf_pin": "PIN की पुष्टि करें:",
        "btn_update_pin": "🔑 PIN अपडेट करें",
        "old_pin_err": "पुराना PIN गलत है!",
        "pin_digit_err": "नया PIN केवल 4 अंकों का होना चाहिए!",
        "pin_match_err": "नया PIN और Confirm PIN मेल नहीं खा रहे!",
        "pin_change_success": "PIN सफलतापूर्वक बदल दिया गया है!"
    },
    "EN": {
        "title": "Sahukar Ledger Pro - Loan Management System",
        "tab_dash": " 📊 Dashboard ",
        "tab_add": " ➕ Add Customer ",
        "tab_dir": " 📜 Customer Directory ",
        "tab_pay": " 💳 Part Payment ",
        "tab_tools": " ⚙️ Backup & Tools ",
        "biz_overview": "Business Overview",
        "card_cust": "Total Active Customers",
        "card_princ": "Outstanding Principal",
        "card_int": "Accrued Live Interest",
        "card_rec": "Total Recovered Payments",
        "card_overdue": "Overdue Accounts (≥30 Days)",
        "btn_refresh": "↻ Refresh Dashboard",
        "cust_due": "Customers Due",
        "lbl_name": "Customer Name*",
        "lbl_mobile": "Mobile Number*",
        "lbl_addr": "Address",
        "lbl_govid": "Govt ID Doc",
        "lbl_princ": "Principal Amount (₹)*",
        "lbl_rate": "Interest Rate (%/month)*",
        "lbl_date": "Loan Date (YYYY-MM-DD)*",
        "lbl_collat": "Collateral Item",
        "lbl_weight": "Gold Weight (Grams)",
        "lbl_notes": "Notes",
        "lbl_photo": "Item Photo",
        "btn_browse": "Browse",
        "btn_save_cust": "💾 Save Customer Record",
        "search_lbl": "Search (Name/Mobile):",
        "btn_search": "🔍 Search",
        "btn_overdue": "🚨 Show Overdue (≥30 Days)",
        "btn_reset": "Reset",
        "cust_id": "Customer ID:",
        "btn_fetch": "Fetch Details",
        "pay_prompt": "Please enter Customer ID and click Fetch Details.",
        "paid_amt": "Paid Amount (₹):",
        "btn_pay_pdf": "💳 Process Part Payment & Generate PDF Receipt",
        "backup_sec": "Database Backup & Maintenance",
        "btn_backup": "📁 Create Full Database Backup",
        "sec_sec": "Security Settings",
        "btn_change_pin": "🔑 Change Security PIN",
        "pin_prompt": "Enter 4-Digit Security PIN:",
        "pin_err": "Invalid PIN! Closing application.",
        "fill_req": "Please fill all mandatory (*) fields!",
        "invalid_input": "Please fix invalid input or date format (YYYY-MM-DD)!",
        "cust_saved": "New customer record saved successfully!",
        "enter_valid_id": "Enter a valid Customer ID!",
        "cust_not_found": "Customer not found!",
        "enter_valid_amt": "Enter a valid payment amount!",
        "pay_success": "Payment recorded successfully!\nPDF Receipt Saved in 'payments_receipts' Folder: ",
        "db_not_found": "Database file not found!",
        "backup_success": "Database backup created successfully:\n",
        "old_pin": "Current PIN:",
        "new_pin": "New 4-Digit PIN:",
        "conf_pin": "Confirm New PIN:",
        "btn_update_pin": "🔑 Update PIN",
        "old_pin_err": "Old PIN is incorrect!",
        "pin_digit_err": "New PIN must be exactly 4 digits!",
        "pin_match_err": "New PIN and Confirm PIN do not match!",
        "pin_change_success": "PIN updated successfully!"
    }
}

# ==========================================
# 2. MAIN APPLICATION CLASS
# ==========================================
class SahukarProApp:
    def __init__(self, root):
        self.root = root
        self.current_lang = get_saved_lang()
        self.t = I18N[self.current_lang]

        self.root.title(self.t["title"])
        self.root.geometry("1280x820")
        self.root.configure(bg="#f1f5f9")

        init_db()

        if not self.authenticate_user():
            self.root.destroy()
            return

        # Header Frame
        header = tk.Frame(self.root, bg="#0f172a", height=70)
        header.pack(fill=tk.X)
        
        self.header_title = tk.Label(
            header, text=self.t["title"], 
            font=("Helvetica", 22, "bold"), fg="#f8fafc", bg="#0f172a", pady=12
        )
        self.header_title.pack(side=tk.LEFT, padx=20)

        # Language Switch Button
        lang_btn = tk.Button(
            header, text="🌐 " + ("English Me Dekhein" if self.current_lang == "HI" else "हिंदी में देखें"),
            font=("Helvetica", 11, "bold"), bg="#2563eb", fg="white", padx=12, pady=6,
            command=self.toggle_language
        )
        lang_btn.pack(side=tk.RIGHT, padx=20, pady=10)

        # Style configuration for Navigation Tabs
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TNotebook.Tab", font=("Helvetica", 15, "bold"), padding=[12, 8])

        # Tabs Layout
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_add_customer = ttk.Frame(self.notebook)
        self.tab_customer_list = ttk.Frame(self.notebook)
        self.tab_payment = ttk.Frame(self.notebook)
        self.tab_backup = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_dashboard, text=self.t["tab_dash"])
        self.notebook.add(self.tab_add_customer, text=self.t["tab_add"])
        self.notebook.add(self.tab_customer_list, text=self.t["tab_dir"])
        self.notebook.add(self.tab_payment, text=self.t["tab_pay"])
        self.notebook.add(self.tab_backup, text=self.t["tab_tools"])

        # UI Setup
        self.build_dashboard()
        self.build_add_customer()
        self.build_customer_list()
        self.build_payment_tab()
        self.build_backup_tab()

        self.refresh_dashboard()

    def toggle_language(self):
        new_lang = "EN" if self.current_lang == "HI" else "HI"
        save_lang(new_lang)
        messagebox.showinfo("Language Switch", "भाषा बदलने के लिए एप्लिकेशन रीस्टार्ट हो रहा है / Restarting app to change language.")
        self.root.destroy()
        main()

    def authenticate_user(self):
        saved_pin = get_saved_pin()
        user_pin = simpledialog.askstring("Security Lock", self.t["pin_prompt"], show='*')
        if user_pin == saved_pin:
            return True
        else:
            messagebox.showerror("Access Denied", self.t["pin_err"])
            return False

    def calculate_interest(self, principal, rate, loan_date_str):
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

    # ------------------------------------------
    # 1. DASHBOARD
    # ------------------------------------------
    def build_dashboard(self):
        frame = tk.Frame(self.tab_dashboard, bg="#f1f5f9", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=self.t["biz_overview"], font=("Helvetica", 18, "bold"), bg="#f1f5f9").grid(row=0, column=0, sticky="w", pady=(0, 15))

        self.card_cust = self.create_card(frame, self.t["card_cust"], "0", 1, 0, "#2563eb")
        self.card_princ = self.create_card(frame, self.t["card_princ"], "₹0.00", 1, 1, "#059669")
        self.card_int = self.create_card(frame, self.t["card_int"], "₹0.00", 2, 0, "#d97706")
        self.card_rec = self.create_card(frame, self.t["card_rec"], "₹0.00", 2, 1, "#7c3aed")
        self.card_overdue = self.create_card(frame, self.t["card_overdue"], "0", 3, 0, "#dc2626")

        btn_refresh = tk.Button(
            frame, text=self.t["btn_refresh"], font=("Helvetica", 13, "bold"),
            bg="#0f172a", fg="white", padx=15, pady=8, command=self.refresh_dashboard
        )
        btn_refresh.grid(row=3, column=1, pady=20)

    def create_card(self, parent, title, initial_val, row, col, color):
        card = tk.Frame(parent, bg=color, padx=20, pady=15)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(card, text=title, font=("Helvetica", 13, "bold"), fg="white", bg=color).pack(anchor="w")
        val_label = tk.Label(card, text=initial_val, font=("Helvetica", 20, "bold"), fg="white", bg=color)
        val_label.pack(anchor="w", pady=(5, 0))
        return val_label

    def refresh_dashboard(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT principal, interest_rate, loan_date FROM customers WHERE status = 'ACTIVE'")
        rows = cursor.fetchall()

        cursor.execute("SELECT SUM(total_paid) FROM payments")
        paid_res = cursor.fetchone()[0] or 0.0
        conn.close()

        total_customers = len(rows)
        total_principal = sum(r[0] for r in rows)
        total_interest = sum(self.calculate_interest(r[0], r[1], r[2])[1] for r in rows)
        overdue_count = sum(1 for r in rows if self.calculate_interest(r[0], r[1], r[2])[0] >= 30)

        self.card_cust.config(text=str(total_customers))
        self.card_princ.config(text=f"₹{total_principal:,.2f}")
        self.card_int.config(text=f"₹{total_interest:,.2f}")
        self.card_rec.config(text=f"₹{paid_res:,.2f}")
        self.card_overdue.config(text=f"{overdue_count} {self.t['cust_due']}")

    # ------------------------------------------
    # 2. ADD CUSTOMER
    # ------------------------------------------
    def build_add_customer(self):
        container = tk.Frame(self.tab_add_customer, padx=20, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        fields = [
            (self.t["lbl_name"], "entry_name"),
            (self.t["lbl_mobile"], "entry_mobile"),
            (self.t["lbl_addr"], "entry_address"),
            (self.t["lbl_govid"], "entry_gov_id"),
            (self.t["lbl_princ"], "entry_principal"),
            (self.t["lbl_rate"], "entry_rate"),
            (self.t["lbl_date"], "entry_date"),
            (self.t["lbl_collat"], "entry_collateral"),
            (self.t["lbl_weight"], "entry_weight"),
            (self.t["lbl_notes"], "entry_notes")
        ]

        self.inputs = {}
        for i, (label_text, var_name) in enumerate(fields):
            row = i // 2
            col = (i % 2) * 2
            tk.Label(container, text=label_text, font=("Helvetica", 13, "bold")).grid(row=row, column=col, sticky="w", padx=10, pady=10)
            entry = tk.Entry(container, font=("Helvetica", 12, "bold"), width=28)
            entry.grid(row=row, column=col+1, sticky="w", padx=10, pady=10)
            self.inputs[var_name] = entry

        self.inputs["entry_date"].insert(0, datetime.now().strftime("%Y-%m-%d"))

        tk.Label(container, text=self.t["lbl_photo"], font=("Helvetica", 13, "bold")).grid(row=5, column=0, sticky="w", padx=10, pady=10)
        photo_frame = tk.Frame(container)
        photo_frame.grid(row=5, column=1, sticky="w", padx=10, pady=10)
        self.photo_path_var = tk.StringVar()
        tk.Entry(photo_frame, textvariable=self.photo_path_var, font=("Helvetica", 11), width=18, state="readonly").pack(side=tk.LEFT)
        tk.Button(photo_frame, text=self.t["btn_browse"], font=("Helvetica", 11, "bold"), command=self.browse_photo).pack(side=tk.LEFT, padx=5)

        tk.Button(
            container, text=self.t["btn_save_cust"], font=("Helvetica", 14, "bold"),
            bg="#059669", fg="white", padx=20, pady=10, command=self.save_customer
        ).grid(row=6, column=0, columnspan=4, pady=25)

    def browse_photo(self):
        filename = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if filename:
            self.photo_path_var.set(filename)

    def save_customer(self):
        name = self.inputs["entry_name"].get().strip()
        mobile = self.inputs["entry_mobile"].get().strip()
        address = self.inputs["entry_address"].get().strip()
        gov_id = self.inputs["entry_gov_id"].get().strip()
        principal = self.inputs["entry_principal"].get().strip()
        rate = self.inputs["entry_rate"].get().strip()
        loan_date = self.inputs["entry_date"].get().strip()
        collateral = self.inputs["entry_collateral"].get().strip()
        weight = self.inputs["entry_weight"].get().strip() or "0"
        notes = self.inputs["entry_notes"].get().strip()
        photo = self.photo_path_var.get()

        if not name or not mobile or not principal or not rate or not loan_date:
            messagebox.showerror("Error", self.t["fill_req"])
            return

        try:
            principal = float(principal)
            rate = float(rate)
            weight = float(weight)
            datetime.strptime(loan_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", self.t["invalid_input"])
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO customers (name, mobile, address, gov_id, principal, interest_rate, loan_date, collateral, gold_weight, photo_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, mobile, address, gov_id, principal, rate, loan_date, collateral, weight, photo, notes))
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", self.t["cust_saved"])
        for key, entry in self.inputs.items():
            entry.delete(0, tk.END)
        self.inputs["entry_date"].insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.photo_path_var.set("")

        self.refresh_dashboard()
        self.load_customers()

    # ------------------------------------------
    # 3. CUSTOMER DIRECTORY
    # ------------------------------------------
    def build_customer_list(self):
        frame = tk.Frame(self.tab_customer_list, padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        search_frame = tk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(search_frame, text=self.t["search_lbl"], font=("Helvetica", 13, "bold")).pack(side=tk.LEFT, padx=5)
        self.search_entry = tk.Entry(search_frame, font=("Helvetica", 12, "bold"), width=20)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(search_frame, text=self.t["btn_search"], bg="#0f172a", fg="white", font=("Helvetica", 11, "bold"), command=self.load_customers).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text=self.t["btn_overdue"], bg="#dc2626", fg="white", font=("Helvetica", 11, "bold"), command=self.load_overdue_customers).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text=self.t["btn_reset"], font=("Helvetica", 11, "bold"), command=self.reset_search).pack(side=tk.LEFT, padx=5)

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))
        style.configure("Treeview", font=("Helvetica", 11), rowheight=32)

        columns = ("ID", "Name", "Mobile", "Principal", "Rate", "Days", "Live Interest", "Total Payable")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)
        self.tree.column("Name", width=180)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.tag_configure('overdue', background='#fecaca', foreground='#991b1b')
        self.load_customers()

    def reset_search(self):
        self.search_entry.delete(0, tk.END)
        self.load_customers()

    def load_customers(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        q = self.search_entry.get().strip()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        if q:
            cursor.execute('''
                SELECT id, name, mobile, principal, interest_rate, loan_date 
                FROM customers WHERE (name LIKE ? OR mobile LIKE ?) AND status = 'ACTIVE'
            ''', (f"%{q}%", f"%{q}%"))
        else:
            cursor.execute('SELECT id, name, mobile, principal, interest_rate, loan_date FROM customers WHERE status = "ACTIVE"')

        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            cid, name, mobile, principal, rate, loan_date = r
            days, interest, total = self.calculate_interest(principal, rate, loan_date)
            tag = 'overdue' if days >= 30 else ''
            self.tree.insert("", tk.END, values=(
                cid, name, mobile, f"₹{principal:,.2f}", f"{rate}%", f"{days} Days", f"₹{interest:,.2f}", f"₹{total:,.2f}"
            ), tags=(tag,))

    def load_overdue_customers(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, mobile, principal, interest_rate, loan_date FROM customers WHERE status = "ACTIVE"')
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            cid, name, mobile, principal, rate, loan_date = r
            days, interest, total = self.calculate_interest(principal, rate, loan_date)
            if days >= 30:
                self.tree.insert("", tk.END, values=(
                    cid, name, mobile, f"₹{principal:,.2f}", f"{rate}%", f"{days} Days", f"₹{interest:,.2f}", f"₹{total:,.2f}"
                ), tags=('overdue',))

    # ------------------------------------------
    # 4. PART PAYMENT & PDF RECEIPT
    # ------------------------------------------
    def build_payment_tab(self):
        frame = tk.Frame(self.tab_payment, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        p_frame = tk.Frame(frame)
        p_frame.pack(fill=tk.X, pady=10)

        tk.Label(p_frame, text=self.t["cust_id"], font=("Helvetica", 13, "bold")).grid(row=0, column=0, padx=5, pady=5)
        self.pay_id_entry = tk.Entry(p_frame, font=("Helvetica", 12, "bold"), width=10)
        self.pay_id_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Button(p_frame, text=self.t["btn_fetch"], bg="#0f172a", fg="white", font=("Helvetica", 11, "bold"), command=self.fetch_pay_details).grid(row=0, column=2, padx=10)

        self.pay_info_lbl = tk.Label(frame, text=self.t["pay_prompt"], font=("Helvetica", 13, "bold"), fg="#475569", justify="left")
        self.pay_info_lbl.pack(anchor="w", pady=15)

        input_f = tk.Frame(frame)
        input_f.pack(fill=tk.X, pady=10)

        tk.Label(input_f, text=self.t["paid_amt"], font=("Helvetica", 13, "bold")).grid(row=0, column=0, padx=5, pady=5)
        self.pay_amt_entry = tk.Entry(input_f, font=("Helvetica", 12, "bold"), width=15)
        self.pay_amt_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Button(
            input_f, text=self.t["btn_pay_pdf"], font=("Helvetica", 12, "bold"),
            bg="#2563eb", fg="white", padx=15, pady=6, command=self.process_payment
        ).grid(row=0, column=2, padx=15)

    def fetch_pay_details(self):
        cid = self.pay_id_entry.get().strip()
        if not cid.isdigit():
            messagebox.showerror("Error", self.t["enter_valid_id"])
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, mobile, address, gov_id, principal, interest_rate, loan_date, collateral FROM customers WHERE id = ? AND status = 'ACTIVE'", (cid,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Error", self.t["cust_not_found"])
            return

        cid, name, mobile, address, gov_id, principal, rate, loan_date, collateral = row
        days, interest, total = self.calculate_interest(principal, rate, loan_date)

        self.current_pay_cust = {
            "id": cid, "name": name, "mobile": mobile, "address": address, "gov_id": gov_id,
            "principal": principal, "rate": rate, "days": days, 
            "interest": interest, "total": total, "collateral": collateral
        }

        info_text = (
            f"👤 Name: {name} | Mobile: {mobile}\n"
            f"💰 Principal: ₹{principal:,.2f} | Rate: {rate}%/month\n"
            f"📅 Days: {days} | Accrued Interest: ₹{interest:,.2f}\n"
            f"📌 Total Payable: ₹{total:,.2f}"
        )
        self.pay_info_lbl.config(text=info_text, fg="#0f172a")

    def process_payment(self):
        if not hasattr(self, 'current_pay_cust') or not self.current_pay_cust:
            messagebox.showerror("Error", self.t["pay_prompt"])
            return

        paid_str = self.pay_amt_entry.get().strip()
        try:
            paid_amt = float(paid_str)
            if paid_amt <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", self.t["enter_valid_amt"])
            return

        cust = self.current_pay_cust
        interest_due = cust["interest"]
        principal = cust["principal"]

        if paid_amt <= interest_due:
            interest_paid = paid_amt
            principal_paid = 0.0
        else:
            interest_paid = interest_due
            principal_paid = paid_amt - interest_due

        new_principal = round(principal - principal_paid, 2)
        today_str = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Get previous payment count to construct sequential payment number
        cursor.execute("SELECT COUNT(*) FROM payments WHERE customer_id = ?", (cust["id"],))
        prev_count = cursor.fetchone()[0] or 0
        payment_seq = prev_count + 1

        if new_principal <= 0:
            cursor.execute("UPDATE customers SET principal = 0, status = 'CLOSED' WHERE id = ?", (cust["id"],))
            new_principal = 0.0
        else:
            cursor.execute("UPDATE customers SET principal = ?, loan_date = ? WHERE id = ?", (new_principal, today_str, cust["id"]))

        cursor.execute('''
            INSERT INTO payments (customer_id, payment_date, total_paid, interest_paid, principal_paid, remaining_principal)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cust["id"], today_str, paid_amt, interest_paid, principal_paid, new_principal))

        conn.commit()
        conn.close()

        # Ensure receipts folder exists
        receipts_dir = "payments_receipts"
        os.makedirs(receipts_dir, exist_ok=True)

        # Named PDF saved inside payments_receipts folder
        safe_name = sanitize_filename(cust['name'])
        pdf_file = os.path.join(receipts_dir, f"{safe_name}_Payment_Receipt_{payment_seq}.pdf")
        
        self.generate_pdf_receipt(pdf_file, cust, today_str, paid_amt, interest_paid, principal_paid, new_principal, payment_seq)

        messagebox.showinfo("Success", f"{self.t['pay_success']}{pdf_file}")
        
        self.pay_amt_entry.delete(0, tk.END)
        self.pay_info_lbl.config(text="Payment Processed Successfully.")
        self.current_pay_cust = None

        self.refresh_dashboard()
        self.load_customers()

    def generate_pdf_receipt(self, filename, cust, date_str, paid_amt, int_paid, princ_paid, rem_princ, payment_seq):
        if not HAS_REPORTLAB:
            messagebox.showerror("Error", "ReportLab library not installed! Run 'pip install reportlab' to generate PDF receipts.")
            return

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

        # Professional Color Palette
        PRIMARY_COLOR = colors.HexColor("#1e293b")   # Dark Navy Slate
        SECONDARY_COLOR = colors.HexColor("#2563eb") # Vibrant Blue
        BG_LIGHT = colors.HexColor("#f8fafc")        # Soft Light Gray
        TEXT_MUTED = colors.HexColor("#64748b")      # Slate Gray

        # Custom Typography Styles with auto text-wrapping
        style_header_title = ParagraphStyle('HeaderTitle', fontName='Helvetica-Bold', fontSize=22, textColor=colors.white, alignment=0)
        style_header_sub = ParagraphStyle('HeaderSub', fontName='Helvetica', fontSize=10, textColor=colors.HexColor("#93c5fd"), alignment=0)
        
        style_receipt_id = ParagraphStyle('ReceiptID', fontName='Helvetica-Bold', fontSize=14, textColor=PRIMARY_COLOR, alignment=2)
        style_receipt_date = ParagraphStyle('ReceiptDate', fontName='Helvetica', fontSize=9, textColor=TEXT_MUTED, alignment=2)
        
        style_sec_heading = ParagraphStyle('SecHeading', fontName='Helvetica-Bold', fontSize=11, textColor=SECONDARY_COLOR, spaceAfter=4)
        style_cell_label = ParagraphStyle('CellLabel', fontName='Helvetica-Bold', fontSize=9, textColor=PRIMARY_COLOR)
        style_cell_val = ParagraphStyle('CellVal', fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#334155"))
        
        style_table_header = ParagraphStyle('THead', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=0)
        style_table_header_r = ParagraphStyle('THeadR', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=2)
        
        style_table_cell = ParagraphStyle('TCell', fontName='Helvetica', fontSize=9, textColor=PRIMARY_COLOR, alignment=0)
        style_table_cell_r = ParagraphStyle('TCellR', fontName='Helvetica', fontSize=9, textColor=PRIMARY_COLOR, alignment=2)
        
        style_rem_bal = ParagraphStyle('RemBal', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor("#dc2626"), alignment=2)
        style_footer_text = ParagraphStyle('FooterText', fontName='Helvetica-Oblique', fontSize=8, textColor=TEXT_MUTED, alignment=1)

        # 1. TOP HEADER BANNER
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
            ('PADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 15))

        # 2. CUSTOMER & LOAN SUMMARY SECTION
        elements.append(Paragraph("CUSTOMER & LOAN DETAILS", style_sec_heading))
        elements.append(HRFlowable(width="100%", thickness=1, color=SECONDARY_COLOR, spaceAfter=8))

        cust_addr = cust.get('address') or "N/A"
        cust_govid = cust.get('gov_id') or "N/A"
        cust_collat = cust.get('collateral') or "N/A"

        info_data = [
            [
                Paragraph("Customer ID:", style_cell_label), Paragraph(str(cust['id']), style_cell_val),
                Paragraph("Principal Amount:", style_cell_label), Paragraph(f"INR {cust['principal']:,.2f}", style_cell_val)
            ],
            [
                Paragraph("Customer Name:", style_cell_label), Paragraph(cust['name'], style_cell_val),
                Paragraph("Interest Rate:", style_cell_label), Paragraph(f"{cust['rate']}% / Month", style_cell_val)
            ],
            [
                Paragraph("Mobile Number:", style_cell_label), Paragraph(cust['mobile'], style_cell_val),
                Paragraph("Tenure Duration:", style_cell_label), Paragraph(f"{cust['days']} Days Accrued", style_cell_val)
            ],
            [
                Paragraph("Address:", style_cell_label), Paragraph(cust_addr, style_cell_val),
                Paragraph("Collateral Item:", style_cell_label), Paragraph(cust_collat, style_cell_val)
            ],
            [
                Paragraph("Govt ID Ref:", style_cell_label), Paragraph(cust_govid, style_cell_val),
                Paragraph("Accrued Interest:", style_cell_label), Paragraph(f"INR {cust['interest']:,.2f}", style_cell_val)
            ]
        ]

        info_table = Table(info_data, colWidths=[100, 176, 110, 166])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 15))

        # 3. PAYMENT BREAKDOWN TABLE
        elements.append(Paragraph("TRANSACTION FINANCIAL BREAKDOWN", style_sec_heading))
        elements.append(HRFlowable(width="100%", thickness=1, color=SECONDARY_COLOR, spaceAfter=8))

        breakdown_data = [
            [
                Paragraph("Description / Transaction Item", style_table_header),
                Paragraph("Amount (INR)", style_table_header_r)
            ],
            [
                Paragraph("Total Amount Paid in Transaction", style_table_cell),
                Paragraph(f"<b>INR {paid_amt:,.2f}</b>", style_table_cell_r)
            ],
            [
                Paragraph("   ↳ Accrued Interest Settled", style_table_cell),
                Paragraph(f"INR {int_paid:,.2f}", style_table_cell_r)
            ],
            [
                Paragraph("   ↳ Principal Amount Deducted", style_table_cell),
                Paragraph(f"INR {princ_paid:,.2f}", style_table_cell_r)
            ],
            [
                Paragraph("<b>REMAINING OUTSTANDING PRINCIPAL BALANCE</b>", style_table_cell),
                Paragraph(f"<b>INR {rem_princ:,.2f}</b>", style_rem_bal)
            ]
        ]

        breakdown_table = Table(breakdown_data, colWidths=[382, 170])
        breakdown_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 7),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor("#e2e8f0")),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#fef2f2")),
            ('BOX', (0, 0), (-1, -1), 1, PRIMARY_COLOR),
        ]))
        elements.append(breakdown_table)
        elements.append(Spacer(1, 25))

        # 4. AUTHORIZATION & SIGNATURE SECTION
        sig_data = [
            [
                Paragraph("<b>Customer Signature:</b> ____________________", style_cell_val),
                Paragraph("<b>Authorized Signatory</b><br/>(Sahukar Ledger Pro)", ParagraphStyle('SigRight', parent=style_cell_val, alignment=2))
            ]
        ]
        sig_table = Table(sig_data, colWidths=[276, 276])
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(sig_table)
        elements.append(Spacer(1, 20))

        # 5. FOOTER DISCLAIMER
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
        elements.append(Paragraph("This is a computer-generated official payment receipt and does not require a physical signature.", style_footer_text))
        elements.append(Paragraph("Thank you for your timely payment!", ParagraphStyle('Thank', parent=style_footer_text, fontName='Helvetica-Bold', textColor=PRIMARY_COLOR)))

        doc.build(elements)

    # ------------------------------------------
    # 5. BACKUP & TOOLS
    # ------------------------------------------
    def build_backup_tab(self):
        frame = tk.Frame(self.tab_backup, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=self.t["backup_sec"], font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))

        btn_backup = tk.Button(
            frame, text=self.t["btn_backup"], font=("Helvetica", 12, "bold"),
            bg="#059669", fg="white", padx=15, pady=8, command=self.create_backup
        )
        btn_backup.pack(anchor="w", pady=10)

        tk.Label(frame, text=self.t["sec_sec"], font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(25, 15))

        btn_change_pin = tk.Button(
            frame, text=self.t["btn_change_pin"], font=("Helvetica", 12, "bold"),
            bg="#0f172a", fg="white", padx=15, pady=8, command=self.change_pin_dialog
        )
        btn_change_pin.pack(anchor="w", pady=5)

    def create_backup(self):
        if not os.path.exists(DB_NAME):
            messagebox.showerror("Error", self.t["db_not_found"])
            return

        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        
        try:
            shutil.copy2(DB_NAME, backup_path)
            messagebox.showinfo("Success", f"{self.t['backup_success']}{backup_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Backup Failed: {str(e)}")

    def change_pin_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(self.t["sec_sec"])
        dialog.geometry("350x250")
        dialog.resizable(False, False)
        
        tk.Label(dialog, text=self.t["old_pin"], font=("Helvetica", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 2))
        old_entry = tk.Entry(dialog, show="*", font=("Helvetica", 11))
        old_entry.pack(fill=tk.X, padx=20)

        tk.Label(dialog, text=self.t["new_pin"], font=("Helvetica", 11, "bold")).pack(anchor="w", padx=20, pady=(10, 2))
        new_entry = tk.Entry(dialog, show="*", font=("Helvetica", 11))
        new_entry.pack(fill=tk.X, padx=20)

        tk.Label(dialog, text=self.t["conf_pin"], font=("Helvetica", 11, "bold")).pack(anchor="w", padx=20, pady=(10, 2))
        conf_entry = tk.Entry(dialog, show="*", font=("Helvetica", 11))
        conf_entry.pack(fill=tk.X, padx=20)

        def save_pin_action():
            old_p = old_entry.get().strip()
            new_p = new_entry.get().strip()
            conf_p = conf_entry.get().strip()

            if old_p != get_saved_pin():
                messagebox.showerror("Error", self.t["old_pin_err"])
                return
            if len(new_p) != 4 or not new_p.isdigit():
                messagebox.showerror("Error", self.t["pin_digit_err"])
                return
            if new_p != conf_p:
                messagebox.showerror("Error", self.t["pin_match_err"])
                return

            save_new_pin(new_p)
            messagebox.showinfo("Success", self.t["pin_change_success"])
            dialog.destroy()

        tk.Button(dialog, text=self.t["btn_update_pin"], bg="#2563eb", fg="white", font=("Helvetica", 11, "bold"), command=save_pin_action).pack(pady=15)


def main():
    root = tk.Tk()
    app = SahukarProApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
