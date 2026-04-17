import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtWidgets import QDateEdit
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView
from PyQt6.QtWidgets import QComboBox, QTextEdit
from quotation_tool import Database, QuotePDF, QuotationService, InvoiceService, default_terms
from decimal import Decimal
# ---------- Customers Tab ----------
class CustomersTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        # Form fields
        self.name = QLineEdit()
        self.contact = QLineEdit()
        self.phone = QLineEdit()
        self.email = QLineEdit()
        self.address = QTextEdit()
        self.layout.addWidget(QLabel("Customer Name:"))
        self.layout.addWidget(self.name)
        self.layout.addWidget(QLabel("Contact Person:"))
        self.layout.addWidget(self.contact)
        self.layout.addWidget(QLabel("Phone:"))
        self.layout.addWidget(self.phone)
        self.layout.addWidget(QLabel("Email:"))
        self.layout.addWidget(self.email)
        self.layout.addWidget(QLabel("Address:"))
        self.layout.addWidget(self.address)
        # Add button
        self.add_btn = QPushButton("Add Customer")
        self.add_btn.clicked.connect(self.add_customer)
        self.layout.addWidget(self.add_btn)
        # Table
        self.customer_table = QTableWidget(0, 6)
        self.customer_table.setHorizontalHeaderLabels(["ID","Name","Contact","Phone","Email","Address"])
        self.customer_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.layout.addWidget(QLabel("Customer List:"))
        self.layout.addWidget(self.customer_table)
        # Delete button
        self.del_btn = QPushButton("Delete Selected Customer")
        self.del_btn.clicked.connect(self.delete_customer)
        self.layout.addWidget(self.del_btn)
        self.refresh_table()
    def add_customer(self):
        if not self.name.text():
            QMessageBox.warning(self, "Error", "Customer name required")
            return
        self.db.add_customer(
            self.name.text(),
            self.contact.text(),
            self.phone.text(),
            self.email.text(),
            self.address.toPlainText()
        )
        QMessageBox.information(self, "Success", "Customer added!")
        self.name.clear()
        self.contact.clear()
        self.phone.clear()
        self.email.clear()
        self.address.clear()
        self.refresh_table()
    def refresh_table(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id, name, contact_person, phone, email, address FROM customers ORDER BY name")
        rows = cur.fetchall()
        self.customer_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.customer_table.setItem(r, c, QTableWidgetItem(str(val)))
    def delete_customer(self):
        row = self.customer_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "No customer selected")
            return
        customer_id = int(self.customer_table.item(row, 0).text())  # ID is in first column
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this customer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            cur = self.db.conn.cursor()
            cur.execute("DELETE FROM customers WHERE id=?", (customer_id,))
            self.db.conn.commit()
            QMessageBox.information(self, "Deleted", "Customer deleted successfully")
            self.refresh_table()
from PyQt6.QtGui import QColor
class ItemsTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # ---- Search bar ----
        search_layout = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search items by description or unit...")
        self.search.textChanged.connect(self.refresh_table)  # live search
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search)
        self.layout.addLayout(search_layout)

        # ---- Input fields ----
        self.desc = QLineEdit()
        self.unit = QLineEdit()
        self.price = QDoubleSpinBox()
        self.price.setMaximum(1_000_000)
        self.price.setDecimals(0)
        self.sac = QLineEdit()
        self.layout.addWidget(QLabel("SAC/HSN:"))
        self.layout.addWidget(self.sac)


        self.layout.addWidget(QLabel("Description:"))
        self.layout.addWidget(self.desc)
        self.layout.addWidget(QLabel("Unit:"))
        self.layout.addWidget(self.unit)
        self.layout.addWidget(QLabel("Unit Price:"))
        self.layout.addWidget(self.price)

        # ---- Buttons ----
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Item")
        self.add_btn.clicked.connect(self.add_item)
        self.edit_btn = QPushButton("Edit Selected Item")
        self.edit_btn.clicked.connect(self.edit_item)
        self.del_btn = QPushButton("Delete Selected Item")
        self.del_btn.clicked.connect(self.delete_item)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.del_btn)
        self.layout.addLayout(btn_layout)

        # ---- Table ----
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Description","Code",  "Unit", "Unit Price", "SAC/HSN"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.load_selected_item)  # double-click loads fields
        self.layout.addWidget(self.table)

        self.refresh_table()

    def refresh_table(self):
        """Reload items from DB, applying search if given"""
        filter_text = self.search.text().strip()
        if filter_text:
            rows = self.db.search_items(filter_text)
        else:
            rows = self.db.get_items()

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val))

                # Highlight search matches
                if filter_text and filter_text.lower() in str(val).lower():
                    item.setBackground(QColor("yellow"))

                self.table.setItem(r, c, item)



    def add_item(self):
        if not self.desc.text() or not self.unit.text():
            QMessageBox.warning(self, "Error", "Description and Unit required")
            return
        self.db.add_item(self.desc.text(), self.unit.text(), self.price.value(), self.sac.text())
        QMessageBox.information(self, "Success", "Item added!")
        self.clear_fields()
        self.refresh_table()

    def edit_item(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select an item to edit")
            return
        item_id = int(self.table.item(row, 0).text())
        desc = self.desc.text()
        unit = self.unit.text()
        price = self.price.value()
        if not desc or not unit:
            QMessageBox.warning(self, "Error", "Description and Unit required")
            return
        cur = self.db.conn.cursor()
        cur.execute("UPDATE items SET description=?, unit=?, unit_price=?, sac_hsn=? WHERE id=?",
            (desc, unit, price, self.sac.text(), item_id))
        self.db.conn.commit()
        QMessageBox.information(self, "Success", "Item updated!")
        self.refresh_table()

    def delete_item(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select an item to delete")
            return
        item_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(self, "Confirm", "Delete selected item?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            cur = self.db.conn.cursor()
            cur.execute("DELETE FROM items WHERE id=?", (item_id,))
            self.db.conn.commit()
            QMessageBox.information(self, "Deleted", "Item removed")
            self.refresh_table()

    def load_selected_item(self, row, column):
        """Auto-fill fields when user double-clicks a row"""
        # Correct column indices: ID, Description, Code, Unit, Unit Price, SAC/HSN
        # The description is at index 1, not 2.
        self.desc.setText(self.table.item(row, 1).text())
        self.unit.setText(self.table.item(row, 3).text())
        self.price.setValue(float(self.table.item(row, 4).text()))
        self.sac.setText(self.table.item(row, 5).text())

    def clear_fields(self):
        """Reset input fields after add/update"""
        self.desc.clear()
        self.unit.clear()
        self.price.setValue(0.0)
        self.sac.clear()
# ---------- Quotations Tab ----------
class QuotationsTab(QWidget):

    def __init__(self, db: Database, service: QuotationService):
        super().__init__()
        self.db = db
        self.service = service
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        # Customer selection
        self.customer_combo = QComboBox()
        self.layout.addWidget(QLabel("Select Customer:"))
        self.layout.addWidget(self.customer_combo)
        # Customer details view
        self.customer_details = QTextEdit()
        self.customer_details.setReadOnly(True)
        self.layout.addWidget(QLabel("Customer Details:"))
        self.layout.addWidget(self.customer_details)
        self.load_customers()
        self.customer_combo.currentIndexChanged.connect(self.show_customer_details)
        # Items table
        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(["Description", "Qty", "Unit", "Unit Price", "SAC/HSN"])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(QLabel("Line Items:"))
        self.layout.addWidget(self.items_table)
        btn_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Item Row")
        self.add_row_btn.clicked.connect(self.add_row)
        self.del_row_btn = QPushButton("Delete Selected Row")
        self.del_row_btn.clicked.connect(self.del_row)
        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.del_row_btn)
        self.layout.addLayout(btn_layout)
        # Notes
        self.notes = QTextEdit()
        self.layout.addWidget(QLabel("Notes:"))
        self.layout.addWidget(self.notes)
        # Generate button
        self.gen_btn = QPushButton("Generate Quotation PDF")
        self.gen_btn.clicked.connect(self.generate_quote)
        self.layout.addWidget(self.gen_btn)

    def load_customers(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id, name FROM customers ORDER BY name")
        self.customers = cur.fetchall()
        self.customer_combo.clear()
        for cid, name in self.customers:
            self.customer_combo.addItem(name, cid)

    def show_customer_details(self):
        idx = self.customer_combo.currentIndex()
        if idx < 0: return
        cid = self.customer_combo.currentData()
        cust = self.db.get_customer(cid)
        if cust:
            details = f"""
            Name: {cust['name']}
            Contact: {cust['contact_person']}
            Phone: {cust['phone']}
            Email: {cust['email']}
            Address: {cust['address']}
            """
            self.customer_details.setText(details)

    def add_row(self):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        combo = QComboBox()
        items = self.db.get_items()  # (id, code, description, unit, unit_price, sac_hsn)
        for it in items:
            combo.addItem(it[2], it)  # show description, store full item data

        # Connect to a lambda that passes the row and the combo box itself
        combo.currentIndexChanged.connect(lambda index, r=row, c=combo: self.fill_item_details(r, c))
        self.items_table.setCellWidget(row, 0, combo)

        # Set default Qty and make other cells editable
        self.items_table.setItem(row, 1, QTableWidgetItem("1")) # Qty
        self.items_table.setItem(row, 2, QTableWidgetItem("")) # Unit
        self.items_table.setItem(row, 3, QTableWidgetItem("0.00")) # Unit Price
        self.items_table.setItem(row, 4, QTableWidgetItem("")) # SAC/HSN

    def fill_item_details(self, row, combo):
        if combo.currentIndex() < 0:
            return
        item_id, code, desc, unit, price, sac_hsn = combo.currentData()

        # Set unit, price, sac_hsn
        self.items_table.setItem(row, 2, QTableWidgetItem(unit))
        self.items_table.setItem(row, 3, QTableWidgetItem(str(price)))
        self.items_table.setItem(row, 4, QTableWidgetItem(sac_hsn)) # SAC/HSN


    def del_row(self):
        row = self.items_table.currentRow()
        if row >= 0:
            self.items_table.removeRow(row)

    def generate_quote(self):
        customer_id = self.customer_combo.currentData()
        if customer_id is None:
            QMessageBox.warning(self, "Error", "Please select a customer.")
            return
        customer_id = self.customer_combo.currentData()
        items = []
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 0)
            qty_item = self.items_table.item(row, 1)
            unit_item = self.items_table.item(row, 2)
            price_item = self.items_table.item(row, 3)
            sac_item = self.items_table.item(row, 4)

            if not combo or qty_item is None or price_item is None or not qty_item.text() or not price_item.text():
                QMessageBox.warning(self, "Error", f"Missing or invalid item details at row {row+1}.")
                return

            try:
                qty = float(qty_item.text())
                price = float(price_item.text())
            except ValueError:
                QMessageBox.warning(self, "Error", f"Invalid number in Qty or Unit Price at row {row+1}.")
                return

            # Get item description and code from the combo box's current data
            item_data = combo.currentData()
            if item_data:
                item_id, item_code, desc, _, _, _ = item_data # desc is from combo, others from table
            else:
                desc = combo.currentText() # Fallback if no data stored (manual entry)
                item_code = "" # No code if manually entered

            items.append({
                'description': desc,
                'item_code': item_code,
                'qty': qty,
                'unit': unit_item.text() if unit_item else "",
                'unit_price': price,
                'sac_hsn': sac_item.text() if sac_item else ""
            })

        if not items:
            QMessageBox.warning(self, "Error", "No line items to generate quotation.")
            return

        try:
            result = self.service.create_quotation(
                customer_id=customer_id,
                line_items=items,
                notes=self.notes.toPlainText()
            )
            QMessageBox.information(
                self, "Success",
                f"Quotation {result['quote_no']} created!\nPDF: {result['pdf_path']}"
            )
            # Clear fields after successful generation
            self.customer_combo.setCurrentIndex(-1)
            self.customer_details.clear()
            self.items_table.setRowCount(0)
            self.notes.clear()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# ---------- Invoices Tab ----------
from PyQt6.QtCore import QDate

class InvoicesTab(QWidget):
    def __init__(self, db: Database, invoice_service: InvoiceService, quotation_service: QuotationService):
        super().__init__()
        self.db = db
        self.invoice_service = invoice_service
        self.quotation_service = quotation_service # To get quotation details
        self.current_invoice_id = None # To track if we are editing an existing invoice
        self.original_invoice_id = None # To track the original invoice for versioning

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Top section: Quotation selection, Invoice details
        top_layout = QHBoxLayout()
        left_col_layout = QVBoxLayout()
        right_col_layout = QVBoxLayout()

        # Quotation Selection
        self.quotation_combo = QComboBox()
        self.quotation_combo.addItem("-- Select Quotation (Optional) --", None) # Option for no quotation
        self.load_quotations()
        self.quotation_combo.currentIndexChanged.connect(self.load_quotation_data)
        left_col_layout.addWidget(QLabel("Select Quotation:"))
        left_col_layout.addWidget(self.quotation_combo)

        # Customer Selection (for invoices not based on quotes, or to change customer)
        self.customer_combo = QComboBox()
        self.load_customers()
        self.customer_combo.currentIndexChanged.connect(self.show_customer_details)
        left_col_layout.addWidget(QLabel("Select Customer:"))
        left_col_layout.addWidget(self.customer_combo)

        # Customer details view
        self.customer_details = QTextEdit()
        self.customer_details.setReadOnly(True)
        self.customer_details.setFixedHeight(100)
        left_col_layout.addWidget(QLabel("Customer Details:"))
        left_col_layout.addWidget(self.customer_details)

        # Invoice Number
        self.invoice_number_label = QLabel("Invoice Number:")
        self.invoice_number = QLineEdit()
        self.invoice_number.setReadOnly(True) # Usually auto-generated
        right_col_layout.addWidget(self.invoice_number_label)
        right_col_layout.addWidget(self.invoice_number)

        # Invoice Date
        self.invoice_date_label = QLabel("Invoice Date:")
        self.invoice_date = QDateEdit(QDate.currentDate())
        self.invoice_date.setCalendarPopup(True)
        right_col_layout.addWidget(self.invoice_date_label)
        right_col_layout.addWidget(self.invoice_date)

        # Current Version Label
        self.version_label = QLabel("Version: 1 (New)")
        right_col_layout.addWidget(self.version_label)

        top_layout.addLayout(left_col_layout)
        top_layout.addLayout(right_col_layout)
        self.layout.addLayout(top_layout)

        # Items Table
        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(
            ["Description", "Qty", "Unit", "Unit Price", "SAC/HSN"]
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.items_table.itemChanged.connect(self.calculate_total) # Recalculate on item change
        self.layout.addWidget(QLabel("Invoice Line Items:"))
        self.layout.addWidget(self.items_table)

        # Add / Delete Row Buttons
        btn_layout = QHBoxLayout()
        self.add_item_row_btn = QPushButton("Add Item Row")
        self.add_item_row_btn.clicked.connect(self.add_item_row)
        self.delete_item_row_btn = QPushButton("Delete Selected Row")
        self.delete_item_row_btn.clicked.connect(self.delete_item_row)
        btn_layout.addWidget(self.add_item_row_btn)
        btn_layout.addWidget(self.delete_item_row_btn)
        self.layout.addLayout(btn_layout)

        # Notes
        self.notes_label = QLabel("Notes:")
        self.notes = QTextEdit()
        self.notes.setFixedHeight(80)
        self.layout.addWidget(self.notes_label)
        self.layout.addWidget(self.notes)

        # Total
        self.total_label = QLabel("Total: 0.00")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.layout.addWidget(self.total_label)

        # Action Buttons
        action_btn_layout = QHBoxLayout()
        self.new_invoice_btn = QPushButton("New Invoice")
        self.new_invoice_btn.clicked.connect(self.clear_form)
        self.save_draft_btn = QPushButton("Save Draft")
        self.save_draft_btn.clicked.connect(lambda: self.save_invoice(status='Draft'))
        self.generate_invoice_btn = QPushButton("Generate & Issue Invoice")
        self.generate_invoice_btn.clicked.connect(lambda: self.save_invoice(status='Issued'))
        action_btn_layout.addWidget(self.new_invoice_btn)
        action_btn_layout.addWidget(self.save_draft_btn)
        action_btn_layout.addWidget(self.generate_invoice_btn)
        self.layout.addLayout(action_btn_layout)

        # Existing Invoices Table
        self.existing_invoices_table = QTableWidget(0, 5) # Added Status column
        self.existing_invoices_table.setHorizontalHeaderLabels(["ID", "Invoice No", "Date", "Total", "Status"])
        self.existing_invoices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.existing_invoices_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.existing_invoices_table.cellDoubleClicked.connect(self.load_invoice_for_editing)
        self.layout.addWidget(QLabel("Existing Invoices (Double-click to Edit):"))
        self.layout.addWidget(self.existing_invoices_table)

        self.refresh_invoice_list()
        self.generate_invoice_number() # Generate initial invoice number
        self.calculate_total() # Initial total calculation

    def load_quotations(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id, quote_no FROM quotations ORDER BY quote_no DESC")
        quotations = cur.fetchall()
        # Clear existing items but keep the "Select Quotation" placeholder
        self.quotation_combo.clear()
        self.quotation_combo.addItem("-- Select Quotation (Optional) --", None)
        for qid, quote_no in quotations:
            self.quotation_combo.addItem(quote_no, qid)

    def load_customers(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id, name FROM customers ORDER BY name")
        self.customers = cur.fetchall()
        self.customer_combo.clear()
        for cid, name in self.customers:
            self.customer_combo.addItem(name, cid)

    def show_customer_details(self):
        idx = self.customer_combo.currentIndex()
        if idx < 0: return
        cid = self.customer_combo.currentData()
        cust = self.db.get_customer(cid)
        if cust:
            details = f"""
            Name: {cust['name']}
            Contact: {cust['contact_person']}
            Phone: {cust['phone']}
            Email: {cust['email']}
            Address: {cust['address']}
            """
            self.customer_details.setText(details)
        else:
            self.customer_details.clear()

    def generate_invoice_number(self):
        # This will be overridden if a quotation is selected or an existing invoice is loaded
        self.invoice_number.setText(self.invoice_service._generate_invoice_no())
        self.version_label.setText("Version: 1 (New)")

    def load_quotation_data(self):
        self.items_table.setRowCount(0)  # Clear existing items
        qid = self.quotation_combo.currentData()

        if qid is None:
            # No quotation selected, clear customer and generate new invoice number
            self.customer_combo.setCurrentIndex(-1)
            self.customer_details.clear()
            self.notes.clear()
            self.generate_invoice_number()
            self.calculate_total()
            return

        # Load quotation details
        quote_details = self.db.get_quotation_details(qid)
        if quote_details:
            # Set customer
            customer_id = quote_details['customer_id']
            for i in range(self.customer_combo.count()):
                if self.customer_combo.itemData(i) == customer_id:
                    self.customer_combo.setCurrentIndex(i)
                    break
            self.notes.setText(quote_details['notes'])
            # Set invoice number based on quote number (or generate new if preferred)
            # For simplicity, let's generate a new invoice number, but keep quote reference
            self.generate_invoice_number()

        # Load quotation items
        quote_items = self.db.get_quotation_items(qid)
        for row_idx, item_data in enumerate(quote_items):
            self.add_item_row() # Add a new row with item combo
            combo = self.items_table.cellWidget(row_idx, 0)
            if combo:
                # item_description, item_code, qty, unit, unit_price, sac_hsn
                desc, code, qty, unit, price, sac_hsn = item_data
                # Find item in combo box by description
                found_index = -1
                for i in range(combo.count()):
                    if combo.itemText(i) == desc:
                        found_index = i
                        break
                if found_index != -1:
                    combo.setCurrentIndex(found_index)
                else:
                    # If item not found in master list, add it as a plain text item
                    combo.addItem(desc, (None, code, desc, unit, price, sac_hsn))
                    combo.setCurrentIndex(combo.count() - 1)

                self.items_table.setItem(row_idx, 1, QTableWidgetItem(str(qty)))
                self.items_table.setItem(row_idx, 2, QTableWidgetItem(unit))
                self.items_table.setItem(row_idx, 3, QTableWidgetItem(str(price)))
                self.items_table.setItem(row_idx, 4, QTableWidgetItem(sac_hsn))

        self.calculate_total()

    def add_item_row(self):
        row_count = self.items_table.rowCount()
        self.items_table.insertRow(row_count)

        # Create a QComboBox for item selection in the first column
        item_combo = QComboBox()
        item_combo.addItem("-- Select Item --", None) # Placeholder
        items = self.db.get_items()  # (id, code, description, unit, unit_price, sac_hsn)
        for it in items:
            item_combo.addItem(it[2], it) # Display description, store full item data

        # Connect the combo box's signal to fill other item details
        item_combo.currentIndexChanged.connect(lambda index, r=row_count, c=item_combo: self.fill_item_details(r, c))
        self.items_table.setCellWidget(row_count, 0, item_combo)

        # Initialize other cells as editable QTableWidgetItems
        self.items_table.setItem(row_count, 1, QTableWidgetItem("1")) # Qty
        self.items_table.setItem(row_count, 2, QTableWidgetItem("")) # Unit
        self.items_table.setItem(row_count, 3, QTableWidgetItem("0.00")) # Unit Price
        self.items_table.setItem(row_count, 4, QTableWidgetItem("")) # SAC/HSN

    def fill_item_details(self, row, combo):
        item_data = combo.currentData()
        if item_data:
            # item_id, code, desc, unit, price, sac_hsn
            _, code, desc, unit, price, sac_hsn = item_data
            self.items_table.setItem(row, 2, QTableWidgetItem(unit))
            self.items_table.setItem(row, 3, QTableWidgetItem(str(price)))
            self.items_table.setItem(row, 4, QTableWidgetItem(sac_hsn))
        else:
            # Clear fields if "Select Item" is chosen
            self.items_table.setItem(row, 2, QTableWidgetItem(""))
            self.items_table.setItem(row, 3, QTableWidgetItem("0.00"))
            self.items_table.setItem(row, 4, QTableWidgetItem(""))
        self.calculate_total()

    def delete_item_row(self):
        selected_row = self.items_table.currentRow()
        if selected_row >= 0:
            self.items_table.removeRow(selected_row)
            self.calculate_total()

    def calculate_total(self):
        subtotal = Decimal("0.00")
        for row in range(self.items_table.rowCount()):
            qty_item = self.items_table.item(row, 1)
            price_item = self.items_table.item(row, 3)

            if qty_item and price_item:
                try:
                    qty = Decimal(qty_item.text())
                    price = Decimal(price_item.text())
                    subtotal += qty * price
                except Exception:
                    pass # Ignore invalid numbers for now, will be caught on save

        tax_percent = Decimal(str(self.invoice_service.tax_percent))
        tax_amount = (subtotal * (tax_percent / Decimal('100'))).quantize(Decimal("0.01"))
        total = (subtotal + tax_amount).quantize(Decimal("0.01"))

        self.total_label.setText(f"Subtotal: {subtotal:.2f} | Tax ({tax_percent}%): {tax_amount:.2f} | Total: {total:.2f}")

    def save_invoice(self, status='Draft'):
        customer_id = self.customer_combo.currentData()
        if customer_id is None:
            QMessageBox.warning(self, "Error", "Please select a customer.")
            return

        invoice_no = self.invoice_number.text()
        invoice_date = self.invoice_date.date().toString("yyyy-MM-dd")
        notes = self.notes.toPlainText()
        quotation_id = self.quotation_combo.currentData()

        items = []
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 0)
            qty_item = self.items_table.item(row, 1)
            unit_item = self.items_table.item(row, 2)
            price_item = self.items_table.item(row, 3)
            sac_item = self.items_table.item(row, 4)

            if not combo or qty_item is None or price_item is None or not qty_item.text() or not price_item.text():
                QMessageBox.warning(self, "Error", f"Missing or invalid item details at row {row+1}.")
                return

            try:
                qty = float(qty_item.text())
                price = float(price_item.text())
            except ValueError:
                QMessageBox.warning(self, "Error", f"Invalid number in Qty or Unit Price at row {row+1}.")
                return

            item_data = combo.currentData()
            if item_data:
                _, item_code, desc, _, _, _ = item_data
            else:
                desc = combo.currentText()
                item_code = ""

            items.append({
                'description': desc,
                'item_code': item_code,
                'qty': qty,
                'unit': unit_item.text() if unit_item else "",
                'unit_price': price,
                'sac_hsn': sac_item.text() if sac_item else ""
            })

        if not items:
            QMessageBox.warning(self, "Error", "No line items to save.")
            return

        try:
            result = self.invoice_service.create_invoice(
                customer_id=customer_id,
                line_items=items,
                notes=notes,
                quotation_id=quotation_id,
                invoice_no=invoice_no,
                invoice_date=invoice_date,
                existing_invoice_id=self.current_invoice_id,
                status=status
            )
            self.current_invoice_id = result['invoice_id'] # Update current invoice ID
            self.original_invoice_id = result.get('original_invoice_id', self.current_invoice_id)

            msg_box = QMessageBox()
            msg_box.setWindowTitle("Success")
            msg_box.setText(f"Invoice {result['invoice_no']} saved as {status}!")
            if status == 'Issued':
                msg_box.setInformativeText(f"PDF generated at: {result['pdf_path']}")
            msg_box.exec()

            self.refresh_invoice_list()
            if status == 'Issued':
                self.clear_form() # Clear form after issuing
            else:
                # If saved as draft, update invoice number to reflect new version if applicable
                invoice_details = self.db.get_invoice_details(self.current_invoice_id)
                if invoice_details:
                    self.invoice_number.setText(invoice_details['invoice_no'])
                    self.version_label.setText(f"Version: {invoice_details['version']}")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh_invoice_list(self):
        invoices = self.db.get_all_invoices()
        self.existing_invoices_table.setRowCount(len(invoices))
        for r, inv in enumerate(invoices):
            # id, invoice_no, invoice_date, total, status
            self.existing_invoices_table.setItem(r, 0, QTableWidgetItem(str(inv[0]))) # ID
            self.existing_invoices_table.setItem(r, 1, QTableWidgetItem(inv[1])) # Invoice No
            self.existing_invoices_table.setItem(r, 2, QTableWidgetItem(inv[2])) # Date
            self.existing_invoices_table.setItem(r, 3, QTableWidgetItem(f"{inv[3]:.2f}")) # Total
            self.existing_invoices_table.setItem(r, 4, QTableWidgetItem(inv[4])) # Status

    def load_invoice_for_editing(self, row, column):
        invoice_id = int(self.existing_invoices_table.item(row, 0).text())
        invoice_details = self.db.get_invoice_details(invoice_id)
        if not invoice_details:
            QMessageBox.warning(self, "Error", "Invoice not found.")
            return

        self.clear_form(keep_invoice_number=True) # Clear form but keep current invoice number logic

        self.current_invoice_id = invoice_details['id']
        self.original_invoice_id = invoice_details['original_invoice_id'] if invoice_details['original_invoice_id'] else invoice_details['id']

        self.invoice_number.setText(invoice_details['invoice_no'])
        self.invoice_date.setDate(QDate.fromString(invoice_details['invoice_date'], "yyyy-MM-dd"))
        self.notes.setText(invoice_details['notes'])
        self.version_label.setText(f"Version: {invoice_details['version']}")

        # Select customer
        customer_id = invoice_details['customer_id']
        for i in range(self.customer_combo.count()):
            if self.customer_combo.itemData(i) == customer_id:
                self.customer_combo.setCurrentIndex(i)
                break

        # Select quotation if available
        quotation_id = invoice_details['quotation_id']
        if quotation_id:
            for i in range(self.quotation_combo.count()):
                if self.quotation_combo.itemData(i) == quotation_id:
                    self.quotation_combo.setCurrentIndex(i)
                    break
        else:
            self.quotation_combo.setCurrentIndex(0) # Select "-- Select Quotation --"

        # Load items
        invoice_items = self.db.get_invoice_items(invoice_id)
        self.items_table.setRowCount(0)
        for row_idx, item_data in enumerate(invoice_items):
            # item_description, item_code, qty, unit, unit_price, line_total, sac_hsn
            desc, code, qty, unit, price, _, sac_hsn = item_data
            self.add_item_row()
            combo = self.items_table.cellWidget(row_idx, 0)
            if combo:
                # Try to find the item in the master list
                found_index = -1
                for i in range(combo.count()):
                    if combo.itemText(i) == desc:
                        found_index = i
                        break
                if found_index != -1:
                    combo.setCurrentIndex(found_index)
                else:
                    # If not found, add it as a custom item
                    combo.addItem(desc, (None, code, desc, unit, price, sac_hsn))
                    combo.setCurrentIndex(combo.count() - 1)

            self.items_table.setItem(row_idx, 1, QTableWidgetItem(str(qty)))
            self.items_table.setItem(row_idx, 2, QTableWidgetItem(unit))
            self.items_table.setItem(row_idx, 3, QTableWidgetItem(str(price)))
            self.items_table.setItem(row_idx, 4, QTableWidgetItem(sac_hsn))

        self.calculate_total()

    def clear_form(self, keep_invoice_number=False):
        self.current_invoice_id = None
        self.original_invoice_id = None
        self.quotation_combo.setCurrentIndex(0) # Select "-- Select Quotation --"
        self.customer_combo.setCurrentIndex(-1)
        self.customer_details.clear()
        if not keep_invoice_number:
            self.generate_invoice_number()
        self.invoice_date.setDate(QDate.currentDate())
        self.notes.clear()
        self.items_table.setRowCount(0)
        self.calculate_total()
        self.version_label.setText("Version: 1 (New)")

# ---------- Settings Tab ----------
class SettingsTab(QWidget):
    def __init__(self, pdf_maker: QuotePDF, service: QuotationService):
        super().__init__()
        self.pdf_maker = pdf_maker
        self.service = service
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Company info
        self.name = QLineEdit(self.pdf_maker.company_info.get('name', ''))
        self.address = QTextEdit(self.pdf_maker.company_info.get('address', ''))
        self.phone = QLineEdit(self.pdf_maker.company_info.get('phone', ''))
        self.email = QLineEdit(self.pdf_maker.company_info.get('email', ''))
        self.gstin = QLineEdit(self.pdf_maker.company_info.get('gstin', ''))

        self.layout.addWidget(QLabel("Company Name:"))
        self.layout.addWidget(self.name)
        self.layout.addWidget(QLabel("Address:"))
        self.layout.addWidget(self.address)
        self.layout.addWidget(QLabel("Phone:"))
        self.layout.addWidget(self.phone)
        self.layout.addWidget(QLabel("Email:"))
        self.layout.addWidget(self.email)
        self.layout.addWidget(QLabel("GSTIN:"))
        self.layout.addWidget(self.gstin)

        # Tax %
        self.tax = QDoubleSpinBox()
        self.tax.setValue(self.service.tax_percent)
        self.tax.setSuffix(" %")
        self.layout.addWidget(QLabel("Default Tax %:"))
        self.layout.addWidget(self.tax)

        # Terms
        self.terms = QTextEdit("\n".join(self.pdf_maker.terms))
        self.layout.addWidget(QLabel("Terms & Conditions:"))
        self.layout.addWidget(self.terms)

        # Save button
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        self.layout.addWidget(self.save_btn)

    def save_settings(self):
        self.pdf_maker.company_info['name'] = self.name.text()
        self.pdf_maker.company_info['address'] = self.address.toPlainText()
        self.pdf_maker.company_info['phone'] = self.phone.text()
        self.pdf_maker.company_info['email'] = self.email.text()
        self.pdf_maker.company_info['gstin'] = self.gstin.text()
        self.pdf_maker.terms = self.terms.toPlainText().splitlines()
        self.service.tax_percent = Decimal(str(self.tax.value()))
        QMessageBox.information(self, "Saved", "Settings updated!")


# ---------- Main Window ----------
class MainWindow(QMainWindow):
    def __init__(self, db, pdf_maker, quotation_service, invoice_service):
        super().__init__()
        self.setWindowTitle("Quotation Manager")
        self.resize(1000, 700)

        tabs = QTabWidget()
        tabs.addTab(CustomersTab(db), "Customers")
        tabs.addTab(ItemsTab(db), "Items")
        tabs.addTab(QuotationsTab(db, quotation_service), "Quotations")
        tabs.addTab(InvoicesTab(db, invoice_service, quotation_service), "Invoices")
        tabs.addTab(SettingsTab(pdf_maker, quotation_service), "Settings")

        self.setCentralWidget(tabs)


# ---------- Run ----------
if __name__ == "__main__":
    from quotation_tool import Database, QuotePDF, QuotationService

    db = Database()
    company = {
        'name': "Apex Automobile Testing",
        'address': "62 Vrindavan Colony, Gawali Palasiya, MHOW, Indore, MP 453441",
        'phone': "+91-9754220798",
        'email': "deepeshpatidar@hotmail.com",
        'gstin': "23AOHPD5200L1ZD"
    }
    pdf_maker = QuotePDF(company_info=company, terms=default_terms()) # This is now generic for both
    quotation_service = QuotationService(db=db, pdf_maker=pdf_maker, currency="INR", tax_percent=18.0)
    invoice_service = InvoiceService(db=db, pdf_maker=pdf_maker, currency="INR", tax_percent=18.0)

    app = QApplication(sys.argv) # Pass both services to MainWindow
    win = MainWindow(db, pdf_maker, quotation_service, invoice_service)
    win.show()
    sys.exit(app.exec())
