"""Legacy PyQt widgets retained during the incremental UI module extraction."""

import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QGroupBox, QGridLayout, QAbstractItemView,
    QFileDialog, QSpinBox, QDoubleSpinBox, QDialog, QDialogButtonBox,
    QListWidget, QListWidgetItem, QComboBox, QDateEdit, QRadioButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from quotation_tool import Database, QuotePDF, QuotationService, InvoiceService, default_terms, default_proforma_terms, default_invoice_terms, save_company_info, load_company_info
from decimal import Decimal

# ---------- Utility Functions ----------
def create_status_item(status):
    """Create a QTableWidgetItem with status-specific styling"""
    item = QTableWidgetItem(status)
    status_colors = {
        'Draft': QColor(200, 200, 200),      # Gray
        'Pending': QColor(255, 200, 0),      # Orange/Yellow
        'Accepted': QColor(144, 238, 144),   # Light Green
        'Rejected': QColor(255, 127, 127),   # Light Red
        'Unpaid': QColor(255, 200, 100),     # Light Orange
        'Partially Paid': QColor(255, 220, 130),  # Lighter Orange
        'Paid': QColor(144, 238, 144),       # Light Green
        'Issued': QColor(173, 216, 230),     # Light Blue
    }
    color = status_colors.get(status, QColor(255, 255, 255))
    item.setBackground(QBrush(color))
    item.setForeground(QBrush(QColor(0, 0, 0)))
    return item

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
        self.gstin = QLineEdit()
        self.address = QTextEdit()
        self.shipping_address = QTextEdit()
        self.layout.addWidget(QLabel("Customer Name:"))
        self.layout.addWidget(self.name)
        self.layout.addWidget(QLabel("Contact Person:"))
        self.layout.addWidget(self.contact)
        self.layout.addWidget(QLabel("Phone:"))
        self.layout.addWidget(self.phone)
        self.layout.addWidget(QLabel("Email:"))
        self.layout.addWidget(self.email)
        self.layout.addWidget(QLabel("GSTIN:"))
        self.layout.addWidget(self.gstin)
        self.layout.addWidget(QLabel("Address:"))
        self.layout.addWidget(self.address)
        self.layout.addWidget(QLabel("Shipping Address:"))
        self.layout.addWidget(self.shipping_address)
        # Add button
        self.add_btn = QPushButton("Add Customer")
        self.add_btn.clicked.connect(self.add_customer)
        self.layout.addWidget(self.add_btn)

        self.clear_btn = QPushButton("Clear/New Customer")
        self.clear_btn.clicked.connect(self.clear_form)
        self.layout.addWidget(self.clear_btn)

        self.save_btn = QPushButton("Edit Details")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_customer_changes)
        self.layout.addWidget(self.save_btn)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name, phone, email, or GSTIN...")
        self.search.textChanged.connect(self.refresh_table)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search)
        self.layout.addLayout(search_layout)
        
        # Table
        self.customer_table = QTableWidget(0, 8)
        self.customer_table.setHorizontalHeaderLabels(["ID","Name","Contact","Phone","Email","GSTIN","Billing Address", "Shipping Address"])
        self.customer_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.customer_table.itemSelectionChanged.connect(self.on_customer_selected)
        self.layout.addWidget(QLabel("Customer List:"))
        self.layout.addWidget(self.customer_table)
        # Delete button
        self.del_btn = QPushButton("Delete Selected Customer")
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self.delete_customer)
        self.layout.addWidget(self.del_btn)
        self.editing_customer_id = None
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
            self.address.toPlainText(),
            self.shipping_address.toPlainText(),
            self.gstin.text()
        )
        QMessageBox.information(self, "Success", "Customer added!")
        self.clear_form()
        self.refresh_table()

    def clear_form(self):
        self.name.clear()
        self.contact.clear()
        self.phone.clear()
        self.email.clear()
        self.gstin.clear()
        self.address.clear()
        self.shipping_address.clear()
        self.editing_customer_id = None
        self.add_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.customer_table.clearSelection()
        self.customer_table.setCurrentCell(-1, -1)

    def on_customer_selected(self):
        row = self.customer_table.currentRow()
        if row < 0:
            self.del_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.add_btn.setEnabled(True)
            return

        self.del_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.add_btn.setEnabled(False)

        self.editing_customer_id = int(self.customer_table.item(row, 0).text())
        customer = self.db.get_customer(self.editing_customer_id)
        if customer:
            self.name.setText(customer.get('name', ''))
            self.contact.setText(customer.get('contact_person', ''))
            self.phone.setText(customer.get('phone', ''))
            self.email.setText(customer.get('email', ''))
            self.gstin.setText(customer.get('gstin', ''))
            self.address.setPlainText(customer.get('address', ''))
            self.shipping_address.setPlainText(customer.get('shipping_address', ''))

    def save_customer_changes(self):
        if not self.editing_customer_id:
            QMessageBox.warning(self, "Error", "No customer selected for editing")
            return
        if not self.name.text():
            QMessageBox.warning(self, "Error", "Customer name required")
            return
        self.db.update_customer(
            self.editing_customer_id,
            self.name.text(),
            self.contact.text(),
            self.phone.text(),
            self.email.text(),
            self.address.toPlainText(),
            self.shipping_address.toPlainText(),
            self.gstin.text()
        )
        QMessageBox.information(self, "Success", "Customer details updated!")
        self.clear_form()
        self.refresh_table()

    def refresh_table(self):
        search_text = getattr(self, 'search', None)
        if search_text and search_text.text().strip():
            rows = self.db.search_customers(search_text.text().strip())
        else:
            rows = self.db.get_all_customers()
        self.customer_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.customer_table.setItem(r, c, QTableWidgetItem(str(val or "")))
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
            try:
                self.db.delete_customer(customer_id)
            except ValueError as error:
                QMessageBox.warning(self, "Cannot Delete Customer", str(error))
            else:
                QMessageBox.information(self, "Deleted", "Customer deleted successfully")
                self.refresh_table()
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
        self.table.setHorizontalHeaderLabels(["ID", "Code", "Description", "Unit", "Unit Price", "SAC/HSN"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.load_selected_item)  # double-click loads fields
        self.layout.addWidget(self.table)

        self.refresh_table()

    def refresh_table(self):
        """Reload items from DB, applying search if given"""
        filter_text = self.search.text().strip().lower()
        
        # Robustness: disable sorting while updating to prevent index errors
        self.table.setSortingEnabled(False)
        
        try:
            if filter_text:
                rows = self.db.search_items(filter_text)
            else:
                rows = self.db.get_items()

            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    display_val = str(val or "")
                    item = QTableWidgetItem(display_val)

                    # Highlight search matches
                    if filter_text and filter_text in display_val.lower():
                        item.setBackground(QBrush(QColor(0, 102, 204)))  # Professional Blue
                        item.setForeground(QBrush(QColor(255, 255, 255)))  # white text

                    self.table.setItem(r, c, item)
        finally:
            self.table.setSortingEnabled(True)

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
        self.db.update_item(item_id, desc, unit, price, self.sac.text())
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
            self.db.delete_item(item_id)
            QMessageBox.information(self, "Deleted", "Item removed")
            self.refresh_table()

    def load_selected_item(self, row, column):
        """Auto-fill fields when user double-clicks a row"""
        # Mapping to DB columns: 0:ID, 1:Code, 2:Description, 3:Unit, 4:Unit Price, 5:SAC/HSN
        self.desc.setText(self.table.item(row, 2).text())
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

    def on_item_changed(self, item):
        """Handle itemChanged signal for the quotations table (safe stub placed early).

        If full implementation is available later in the class, it will be used; this
        ensures the signal connect in __init__ won't fail if order changes.
        """
        try:
            if getattr(self, 'updating_table', False):
                return
        except Exception:
            return
        col = item.column()
        row = item.row()
        # act on qty (3) or unit price (5) when possible
        if col in (3, 5) and hasattr(self, '_recalculate_line_total'):
            try:
                self.updating_table = True
                self._recalculate_line_total(row)
            finally:
                self.updating_table = False

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
        # Column mapping:
        # 0 - Description (QComboBox), 1 - Item Code, 2 - SAC/HSN, 3 - Qty, 4 - Unit, 5 - Unit Price, 6 - Total
        
        # Search bar for quotations
        search_layout = QHBoxLayout()
        self.search_quotes = QLineEdit()
        self.search_quotes.setPlaceholderText("Search quotations by quote# or date...")
        self.search_quotes.textChanged.connect(self.load_quotation_list)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_quotes)
        self.layout.addLayout(search_layout)

        # Saved quotation list for selection and editing
        self.layout.addWidget(QLabel("Existing Quotations:"))
        self.quote_list = QListWidget()
        self.quote_list.itemSelectionChanged.connect(self.on_quote_selected)
        self.layout.addWidget(self.quote_list)
        
        self.items_table = QTableWidget(0, 7)
        self.items_table.setHorizontalHeaderLabels(["Description", "Item Code", "SAC/HSN", "Qty", "Unit", "Unit Price", "Total"])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Recalculate totals when editable cells change
        self.items_table.itemChanged.connect(self.on_item_changed)
        self.updating_table = False  # guard to avoid recursive itemChanged handling
        self.layout.addWidget(QLabel("Line Items:"))
        self.layout.addWidget(self.items_table)
        # Grand total label below the table
        self.grand_total_label = QLabel("Grand Total: 0.00")
        self.grand_total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.layout.addWidget(self.grand_total_label)

        # Discount section
        discount_group = QGroupBox("Discount")
        discount_layout = QHBoxLayout()
        
        # Create the widgets FIRST
        self.discount_percent_input = QDoubleSpinBox()
        self.discount_percent_input.setMinimum(0.0)
        self.discount_percent_input.setMaximum(100.0)
        self.discount_percent_input.setSuffix(" %")
        self.discount_percent_input.setEnabled(False) # Disabled by default

        self.discount_radio = QRadioButton("Apply Discount (%)")
        # THEN connect signals
        self.discount_radio.toggled.connect(self.discount_percent_input.setEnabled)
        self.discount_radio.toggled.connect(self.calculate_grand_total)
        self.discount_percent_input.valueChanged.connect(self.calculate_grand_total)

        self.discount_amount_label = QLabel("Discount Amount: ₹0.00")
        self.discount_amount_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        discount_layout.addWidget(self.discount_radio)
        discount_layout.addWidget(self.discount_percent_input)
        discount_layout.addStretch()
        discount_layout.addWidget(self.discount_amount_label)
        discount_group.setLayout(discount_layout)
        self.layout.addWidget(discount_group)
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
        
        # PDF Security Section
        security_group = QGroupBox("PDF Security")
        security_layout = QHBoxLayout()
        self.pdf_no_protect_radio = QRadioButton("No Protection")
        self.pdf_no_protect_radio.setChecked(True)
        self.pdf_protect_radio = QRadioButton("Password Protect")
        self.pdf_password = QLineEdit()
        self.pdf_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.pdf_password.setPlaceholderText("Enter PDF password")
        self.pdf_password.setEnabled(False)
        self.pdf_protect_radio.toggled.connect(self.pdf_password.setEnabled)
        
        security_layout.addWidget(self.pdf_no_protect_radio)
        security_layout.addWidget(self.pdf_protect_radio)
        security_layout.addWidget(self.pdf_password)
        security_group.setLayout(security_layout)
        self.layout.addWidget(security_group)

        # Generation buttons
        actions_layout = QHBoxLayout()
        self.gen_new_btn = QPushButton("Generate New Quotation")
        self.gen_new_btn.clicked.connect(lambda: self.generate_quote(update=False))
        self.update_btn = QPushButton("Update Selected (Same No)")
        self.update_btn.setEnabled(False)
        self.update_btn.clicked.connect(lambda: self.generate_quote(update=True))

        self.del_quote_btn = QPushButton("Delete Selected Quotation")
        self.del_quote_btn.setEnabled(False)
        self.del_quote_btn.clicked.connect(self.delete_quotation)

        actions_layout.addWidget(self.gen_new_btn)
        actions_layout.addWidget(self.update_btn)
        actions_layout.addWidget(self.del_quote_btn)
        self.layout.addLayout(actions_layout)

        self.current_quote_id = None
        self.load_quotation_list()

    def showEvent(self, event):
        """Refresh data whenever tab is shown."""
        super().showEvent(event)
        self.load_customers()

    def load_quotation_list(self):
        keyword = self.search_quotes.text().strip() if hasattr(self, 'search_quotes') else ''
        if keyword:
            rows = self.db.search_quotations(keyword)
        else:
            rows = self.db.get_all_quotations()

        self.quote_list.clear()
        for qid, quote_no, date, customer, total, status in rows:
            item = QListWidgetItem(f"{quote_no} - {customer} - {date} - ₹{total:.2f}")
            item.setData(Qt.ItemDataRole.UserRole, qid)
            self.quote_list.addItem(item)

    def on_quote_selected(self):
        selected = self.quote_list.selectedItems()
        if not selected:
            self.current_quote_id = None
            self.update_btn.setEnabled(False)
            self.del_quote_btn.setEnabled(False)
            return
        qid = selected[0].data(Qt.ItemDataRole.UserRole)
        if qid:
            self.current_quote_id = qid
            self.update_btn.setEnabled(True)
            self.del_quote_btn.setEnabled(True)
            self.load_quotation_by_id(qid)

    def load_quotation_by_id(self, quotation_id):
        self.items_table.setRowCount(0)
        self.items_table.itemChanged.disconnect()  # Block itemChanged signal during load
        try:
            quote_details = self.db.get_quotation_details(quotation_id)
            if quote_details:
                customer_id = quote_details['customer_id']
                for i in range(self.customer_combo.count()):
                    if self.customer_combo.itemData(i) == customer_id:
                        self.customer_combo.setCurrentIndex(i)
                        break
                self.show_customer_details()
                self.notes.setPlainText(quote_details.get('notes', ''))

                # Load discount settings
                discount_percent = quote_details.get('discount_percent', 0.0)
                if discount_percent > 0:
                    self.discount_radio.setChecked(True)
                    self.discount_percent_input.setValue(discount_percent)
                else:
                    self.discount_radio.setChecked(False)
                    self.discount_percent_input.setValue(0.0)

            quote_items = self.db.get_quotation_items(quotation_id)
            for row_idx, item_data in enumerate(quote_items):
                desc, code, qty, unit, unit_price, sac_hsn = item_data
                self.items_table.insertRow(row_idx)

                combo = QComboBox()
                combo.addItem("-- Select Item --", None)
                items = self.db.get_items()
                for it in items:
                    combo.addItem(f"{it[1]} - {it[2]}", it)

                found_index = -1
                for i in range(combo.count()):
                    data = combo.itemData(i)
                    if data and data[2] == desc and data[1] == code:
                        found_index = i
                        break
                if found_index != -1:
                    combo.setCurrentIndex(found_index)
                    # Prefer latest HSN/SAC from master catalog if matched
                    master_data = combo.itemData(found_index)
                    if master_data:
                        sac_hsn = master_data[5] # Index 5 is sac_hsn
                else:
                    combo.addItem(desc, (None, code, desc, unit, unit_price, sac_hsn))
                    combo.setCurrentIndex(combo.count() - 1)

                combo.currentIndexChanged.connect(lambda index, r=row_idx, c=combo: self.fill_item_details(r, c))
                self.items_table.setCellWidget(row_idx, 0, combo)

                code_item = QTableWidgetItem(code or "")
                code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                sac_item = QTableWidgetItem(sac_hsn or "")
                qty_item = QTableWidgetItem(str(qty))
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                unit_item = QTableWidgetItem(unit or "")
                price_item = QTableWidgetItem(f"{unit_price:.2f}")
                price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                total_item = QTableWidgetItem(f"{Decimal(str(qty)) * Decimal(str(unit_price)):.2f}")
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.items_table.setItem(row_idx, 1, code_item)
                self.items_table.setItem(row_idx, 2, sac_item)
                self.items_table.setItem(row_idx, 3, qty_item)
                self.items_table.setItem(row_idx, 4, unit_item)
                self.items_table.setItem(row_idx, 5, price_item)
                self.items_table.setItem(row_idx, 6, total_item)
        finally:
            self.items_table.itemChanged.connect(self.on_item_changed)  # Reconnect signal
            self.calculate_grand_total()

    def load_customers(self):
        """Populate the customer combo for the Quotations tab."""
        self.customers = self.db.get_customer_choices()
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
        combo.addItem("-- Select Item --", None)
        items = self.db.get_items()  # (id, code, description, unit, unit_price, sac_hsn)
        for it in items:
            combo.addItem(f"{it[1]} - {it[2]}", it)  # show code + description, store full item data

        combo.currentIndexChanged.connect(lambda index, r=row, c=combo: self.fill_item_details(r, c))
        self.items_table.setCellWidget(row, 0, combo)

        code_item = QTableWidgetItem("")
        code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        sac_item = QTableWidgetItem("")
        qty_item = QTableWidgetItem("1")
        unit_item = QTableWidgetItem("")
        price_item = QTableWidgetItem("0.00")
        total_item = QTableWidgetItem("0.00")

        qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.items_table.setItem(row, 1, code_item)        # Item Code
        self.items_table.setItem(row, 2, sac_item)         # SAC/HSN
        self.items_table.setItem(row, 3, qty_item)         # Qty (default 1)
        self.items_table.setItem(row, 4, unit_item)        # Unit
        self.items_table.setItem(row, 5, price_item)       # Unit Price
        self.items_table.setItem(row, 6, total_item)       # Total (read-only calculation)

    def fill_item_details(self, row, combo):
        item_data = combo.currentData()
        self.updating_table = True
        try:
            if item_data:
                _, code, desc, unit, price, sac_hsn = item_data

                code_it = QTableWidgetItem(code or "")
                code_it.setFlags(code_it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                sac_it = QTableWidgetItem(sac_hsn or "")
                qty_item = self.items_table.item(row, 3)
                if qty_item is None or not qty_item.text().strip():
                    qty_item = QTableWidgetItem("1")
                    qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.items_table.setItem(row, 3, qty_item)

                unit_it = QTableWidgetItem(unit or "")
                price_it = QTableWidgetItem(f"{price:.2f}" if isinstance(price, (int, float, Decimal)) else str(price))
                price_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                total_it = self.items_table.item(row, 6)
                if total_it is None:
                    total_it = QTableWidgetItem("0.00")
                    total_it.setFlags(total_it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    total_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.items_table.setItem(row, 6, total_it)

                self.items_table.setItem(row, 1, code_it)
                self.items_table.setItem(row, 2, sac_it)
                self.items_table.setItem(row, 4, unit_it)
                self.items_table.setItem(row, 5, price_it)
                self._recalculate_line_total(row)
            else:
                self.items_table.setItem(row, 1, QTableWidgetItem(""))
                self.items_table.setItem(row, 2, QTableWidgetItem(""))
                self.items_table.setItem(row, 3, QTableWidgetItem(""))
                self.items_table.setItem(row, 4, QTableWidgetItem(""))
                price_it = QTableWidgetItem("0.00")
                price_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.items_table.setItem(row, 5, price_it)
                total_it = self.items_table.item(row, 6)
                if total_it:
                    total_it.setText("0.00")
                self.calculate_grand_total()
        finally:
            self.updating_table = False

    def _recalculate_line_total(self, row):
        qty_item = self.items_table.item(row, 3)
        price_item = self.items_table.item(row, 5)
        total_item = self.items_table.item(row, 6)
        try:
            qty = Decimal(qty_item.text()) if qty_item and qty_item.text() else Decimal('0')
            price = Decimal(price_item.text()) if price_item and price_item.text() else Decimal('0')
            line_total = (qty * price).quantize(Decimal('0.01'))
        except Exception:
            line_total = Decimal('0.00')
        if total_item is None:
            total_item = QTableWidgetItem(f"{line_total:.2f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.items_table.setItem(row, 6, total_item)
        else:
            total_item.setText(f"{line_total:.2f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.calculate_grand_total()

    def calculate_grand_total(self):
        subtotal_items = Decimal('0.00')
        for r in range(self.items_table.rowCount()):
            item = self.items_table.item(r, 6)
            if item and item.text():
                try:
                    subtotal_items += Decimal(item.text())
                except Exception:
                    pass

        # Apply discount
        discount_percent = Decimal('0.00')
        discount_amount = Decimal('0.00')
        if self.discount_radio.isChecked():
            discount_percent = Decimal(str(self.discount_percent_input.value()))
            discount_amount = (subtotal_items * (discount_percent / Decimal('100'))).quantize(Decimal('0.01'))
        
        subtotal_after_discount = (subtotal_items - discount_amount).quantize(Decimal('0.01'))

        # Get tax percent from service
        tax_percent = self.service.tax_percent
        tax_amount = (subtotal_after_discount * (tax_percent / Decimal('100'))).quantize(Decimal('0.01'))
        
        total = (subtotal_after_discount + tax_amount).quantize(Decimal('0.01'))

        self.discount_amount_label.setText(f"Discount Amount: ₹{discount_amount:.2f}")
        self.grand_total_label.setText(
            f"Subtotal: ₹{subtotal_items:.2f} | Discount: ₹{discount_amount:.2f} | "
            f"Tax ({tax_percent}%): ₹{tax_amount:.2f} | Grand Total: ₹{total:.2f}"
        )

    def del_row(self):
        row = self.items_table.currentRow()
        if row >= 0:
            self.items_table.removeRow(row)
            self.calculate_grand_total()

    def generate_quote(self, update=False):
        customer_id = self.customer_combo.currentData()
        if customer_id is None:
            QMessageBox.warning(self, "Error", "Please select a customer.")
            return
        customer_id = self.customer_combo.currentData()
        items = []
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 0)
            sac_item = self.items_table.item(row, 2)
            qty_item = self.items_table.item(row, 3)
            unit_item = self.items_table.item(row, 4)
            price_item = self.items_table.item(row, 5)
            total_item = self.items_table.item(row, 6)

            if not combo or qty_item is None or price_item is None or not qty_item.text().strip() or not price_item.text().strip():
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
                _, item_code, desc, _, _, _ = item_data
            else:
                desc = combo.currentText()
                item_code = ""

            # Ensure description is not empty
            if not desc:
                desc = "Unnamed Item"

            items.append({
                'description': desc,
                'item_code': item_code,
                'unit': unit_item.text() if unit_item else "",
                'unit_price': price,
                'sac_hsn': sac_item.text() if sac_item else "",
                'line_total': float(total_item.text()) if total_item and total_item.text() else qty * price
            })

        if not items:
            QMessageBox.warning(self, "Error", "No line items to generate quotation.")
            return

        discount_percent = 0.0
        if self.discount_radio.isChecked():
            discount_percent = self.discount_percent_input.value()

        pdf_password = None
        if self.pdf_protect_radio.isChecked():
            pdf_password = self.pdf_password.text().strip()
            if not pdf_password:
                QMessageBox.warning(self, "Security Error", "Please enter a password to protect the PDF.")
                return

        try:
            result = self.service.create_quotation(
                customer_id=customer_id,
                line_items=items,
                notes=self.notes.toPlainText(),
                discount_percent=discount_percent,
                existing_quote_id=self.current_quote_id if update else None,
                pdf_password=pdf_password
            )
            
            # Track the created/updated quote
            self.current_quote_id = result['quotation_id']
            self.update_btn.setEnabled(True)
            
            action_msg = "updated" if update else "created"
            QMessageBox.information(
                self, "Success",
                f"Quotation {result['quote_no']} {action_msg}!\nPDF: {result['pdf_path']}"
            )
            self.load_quotation_list()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_quotation(self):
        if not self.current_quote_id:
            return

        selected_items = self.quote_list.selectedItems()
        quote_info = selected_items[0].text() if selected_items else "this quotation"

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {quote_info}?\n\nThis will permanently remove the record and all generated files (.pdf, .tex, .log, .aux).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 1. Fetch file path before deleting record
                pdf_path = self.db.get_quotation_pdf_path(self.current_quote_id)

                # 2. Delete from DB
                self.db.delete_quotation(self.current_quote_id)

                # 3. Cleanup Filesystem
                if pdf_path:
                    base_path = os.path.splitext(pdf_path)[0]
                    # Clean up common LaTeX extensions + PDF
                    for ext in ['.pdf', '.tex', '.log', '.aux']:
                        full_path = base_path + ext
                        if os.path.exists(full_path):
                            os.remove(full_path)

                QMessageBox.information(self, "Success", "Quotation and associated files deleted successfully.")

                # 4. Refresh UI
                self.current_quote_id = None
                self.load_quotation_list()
                self.items_table.setRowCount(0)
                self.notes.clear()
                self.grand_total_label.setText("Grand Total: 0.00")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete quotation: {str(e)}")


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

        # Search and filter bar
        search_filter_layout = QHBoxLayout()
        self.search_invoices_field = QLineEdit()
        self.search_invoices_field.setPlaceholderText("Search by invoice#, customer...")
        search_filter_layout.addWidget(QLabel("Search:"))
        search_filter_layout.addWidget(self.search_invoices_field)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Draft", "Issued", "Paid"])
        search_filter_layout.addWidget(QLabel("Status:"))
        search_filter_layout.addWidget(self.status_filter)
        search_filter_layout.addStretch()
        self.layout.addLayout(search_filter_layout)
        
        # Items Table
        self.items_table = QTableWidget(0, 6)
        self.items_table.setHorizontalHeaderLabels(
            ["Description", "Qty", "Unit", "Unit Price", "SAC/HSN", "Total"]
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
        self.delete_invoice_btn = QPushButton("Delete Invoice")
        self.delete_invoice_btn.setEnabled(False)
        self.delete_invoice_btn.clicked.connect(self.delete_invoice)

        action_btn_layout.addWidget(self.new_invoice_btn)
        action_btn_layout.addWidget(self.save_draft_btn)
        action_btn_layout.addWidget(self.generate_invoice_btn)
        action_btn_layout.addWidget(self.delete_invoice_btn)
        self.layout.addLayout(action_btn_layout)

        # Existing Invoices Table
        self.existing_invoices_table = QTableWidget(0, 5) # Added Status column
        self.existing_invoices_table.setHorizontalHeaderLabels(["ID", "Invoice No", "Date", "Total", "Status"])
        self.existing_invoices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.existing_invoices_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.existing_invoices_table.cellDoubleClicked.connect(self.load_invoice_for_editing)
        self.layout.addWidget(QLabel("Existing Invoices (Double-click to Edit):"))
        self.existing_invoices_table.itemSelectionChanged.connect(self.on_invoice_selection_changed)
        self.layout.addWidget(self.existing_invoices_table)

        self.refresh_invoice_list()
        self.generate_invoice_number() # Generate initial invoice number
        self.calculate_total() # Initial total calculation
        
        # Connect search and filter signals
        self.search_invoices_field.textChanged.connect(self.refresh_invoice_list)
        self.status_filter.currentIndexChanged.connect(self.refresh_invoice_list)

    def showEvent(self, event):
        """Refresh data whenever tab is shown."""
        super().showEvent(event)
        self.load_quotations()
        self.load_customers()

    def on_invoice_selection_changed(self):
        selected = self.existing_invoices_table.selectedItems()
        self.delete_invoice_btn.setEnabled(len(selected) > 0)

    def load_quotations(self):
        quotations = self.db.get_quotation_choices()
        # Clear existing items but keep the "Select Quotation" placeholder
        self.quotation_combo.clear()
        self.quotation_combo.addItem("-- Select Quotation (Optional) --", None)
        for qid, quote_no in quotations:
            self.quotation_combo.addItem(quote_no, qid)

    def load_customers(self):
        self.customers = self.db.get_customer_choices()
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
                    data = combo.itemData(i)
                    if data and data[2] == desc and (not code or data[1] == code):
                        found_index = i
                        break
                if found_index != -1:
                    combo.setCurrentIndex(found_index)
                    # Prefer latest HSN/SAC from master catalog if matched
                    master_data = combo.itemData(found_index)
                    if master_data:
                        sac_hsn = master_data[5]
                else:
                    # If item not found in master list, add it as a plain text item
                    combo.addItem(desc, (None, code, desc, unit, price, sac_hsn))
                    combo.setCurrentIndex(combo.count() - 1)

                # Column mapping for Invoices: 1 Qty, 2 Unit, 3 Unit Price, 4 SAC/HSN
                qty_it = QTableWidgetItem(str(qty))
                qty_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                unit_it = QTableWidgetItem(unit)
                price_it = QTableWidgetItem(str(price))
                price_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                sac_it = QTableWidgetItem(sac_hsn)

                self.items_table.setItem(row_idx, 1, qty_it)
                self.items_table.setItem(row_idx, 2, unit_it)
                self.items_table.setItem(row_idx, 3, price_it)
                self.items_table.setItem(row_idx, 4, sac_it)

                # Calculate and set total
                total = qty * price
                total_it = QTableWidgetItem(f"{total:.2f}")
                total_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                total_it.setFlags(total_it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.items_table.setItem(row_idx, 5, total_it)

        self.calculate_total()

    def on_item_changed(self, item):
        # Recalculate line total when qty or unit price changes
        if self.updating_table:
            return
        col = item.column()
        row = item.row()
        # Only act on qty (1) or unit price (3) edits
        if col in (1, 3):
            try:
                self.updating_table = True
                if hasattr(self, '_recalculate_line_total'):
                    self._recalculate_line_total(row)
            finally:
                self.updating_table = False

    def _recalculate_line_total(self, row):
        qty_item = self.items_table.item(row, 1)
        price_item = self.items_table.item(row, 3)
        total_item = self.items_table.item(row, 5)
        try:
            qty = Decimal(qty_item.text()) if qty_item and qty_item.text() else Decimal('0')
            price = Decimal(price_item.text()) if price_item and price_item.text() else Decimal('0')
            line_total = (qty * price).quantize(Decimal('0.01'))
        except Exception:
            line_total = Decimal('0.00')
        if total_item is None:
            new_tot = QTableWidgetItem(f"{line_total:.2f}")
            new_tot.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            new_tot.setFlags(new_tot.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.items_table.setItem(row, 5, new_tot)
        else:
            total_item.setText(f"{line_total:.2f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.calculate_total()

    def calculate_grand_total(self):
        grand = Decimal('0.00')
        for r in range(self.items_table.rowCount()):
            t = self.items_table.item(r, 5)
            if t and t.text():
                try:
                    grand += Decimal(t.text())
                except Exception:
                    pass
        self.grand_total_label.setText(f"Grand Total: {grand:.2f}")

    def add_item_row(self):
        row_count = self.items_table.rowCount()
        self.items_table.insertRow(row_count)

        item_combo = QComboBox()
        item_combo.addItem("-- Select Item --", None)
        items = self.db.get_items()  # (id, code, description, unit, unit_price, sac_hsn)
        for it in items:
            item_combo.addItem(f"{it[1]} - {it[2]}", it)

        item_combo.currentIndexChanged.connect(lambda index, r=row_count, c=item_combo: self.fill_item_details(r, c))
        self.items_table.setCellWidget(row_count, 0, item_combo)

        qty_item = QTableWidgetItem("1")
        unit_item = QTableWidgetItem("")
        price_item = QTableWidgetItem("0.00")
        sac_item = QTableWidgetItem("")
        total_item = QTableWidgetItem("0.00")

        qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.items_table.setItem(row_count, 1, qty_item)
        self.items_table.setItem(row_count, 2, unit_item)
        self.items_table.setItem(row_count, 3, price_item)
        self.items_table.setItem(row_count, 4, sac_item)
        self.items_table.setItem(row_count, 5, total_item)

    def fill_item_details(self, row, combo):
        item_data = combo.currentData()
        if item_data:
            _, code, desc, unit, price, sac_hsn = item_data

            qty_item = self.items_table.item(row, 1)
            if qty_item is None or not qty_item.text().strip():
                qty_item = QTableWidgetItem("1")
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.items_table.setItem(row, 1, qty_item)

            unit_item = QTableWidgetItem(unit or "")
            price_item = QTableWidgetItem(f"{price:.2f}" if isinstance(price, (int, float, Decimal)) else str(price))
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            sac_item = QTableWidgetItem(sac_hsn or "")

            total_item = self.items_table.item(row, 5)
            if total_item is None:
                total_item = QTableWidgetItem("0.00")
                total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.items_table.setItem(row, 5, total_item)

            self.items_table.setItem(row, 2, unit_item)
            self.items_table.setItem(row, 3, price_item)
            self.items_table.setItem(row, 4, sac_item)
            self._recalculate_line_total(row)
        else:
            self.items_table.setItem(row, 2, QTableWidgetItem(""))
            price_item = QTableWidgetItem("0.00")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.items_table.setItem(row, 3, price_item)
            self.items_table.setItem(row, 4, QTableWidgetItem(""))
            total_item = self.items_table.item(row, 5)
            if total_item:
                total_item.setText("0.00")
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
            
        pdf_password = None
        if hasattr(self, 'pdf_protect_radio') and self.pdf_protect_radio.isChecked():
            pdf_password = self.pdf_password.text().strip()
            if not pdf_password:
                QMessageBox.warning(self, "Security Error", "Please enter a password to protect the PDF.")
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
                status=status,
                pdf_password=pdf_password
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
        # Get search and filter values
        search_text = self.search_invoices_field.text().strip() if hasattr(self, 'search_invoices_field') else ""
        status_filter = self.status_filter.currentText() if hasattr(self, 'status_filter') else "All"
        
        # Fetch data based on search/filter
        if search_text:
            invoices = self.db.search_invoices(search_text)
        elif status_filter != "All":
            invoices = self.db.get_invoices_by_status(status_filter)
        else:
            invoices = self.db.get_all_invoices()
        
        self.existing_invoices_table.setRowCount(len(invoices))
        for r, inv in enumerate(invoices):
            # id, invoice_no, invoice_date, total, status
            self.existing_invoices_table.setItem(r, 0, QTableWidgetItem(str(inv[0]))) # ID
            display_invoice_no = self.invoice_service.display_invoice_no(inv[1])
            self.existing_invoices_table.setItem(r, 1, QTableWidgetItem(display_invoice_no)) # Invoice No
            self.existing_invoices_table.setItem(r, 2, QTableWidgetItem(inv[2])) # Date
            self.existing_invoices_table.setItem(r, 3, QTableWidgetItem(f"{inv[3]:.2f}")) # Total
            self.existing_invoices_table.setItem(r, 4, QTableWidgetItem(inv[4])) # Status
        self.on_invoice_selection_changed()

    def delete_invoice(self):
        row = self.existing_invoices_table.currentRow()
        if row < 0: return
        
        invoice_id = int(self.existing_invoices_table.item(row, 0).text())
        invoice_no = self.existing_invoices_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete invoice {invoice_no}?\n\nThis will permanently remove the record and free up the invoice number/version for reuse.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                details = self.db.get_invoice_details(invoice_id)
                pdf_path = details.get('pdf_path') if details else None
                self.db.delete_invoice(invoice_id)
                if pdf_path and os.path.exists(pdf_path):
                    try:
                        os.remove(pdf_path)
                        base = os.path.splitext(pdf_path)[0]
                        for ext in ('.tex', '.log', '.aux'):
                            if os.path.exists(base + ext): os.remove(base + ext)
                    except Exception: pass
                QMessageBox.information(self, "Success", f"Invoice {invoice_no} deleted.")
                self.refresh_invoice_list()
                self.clear_form()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete invoice: {str(e)}")

    def load_invoice_for_editing(self, row, column):
        invoice_id = int(self.existing_invoices_table.item(row, 0).text())
        invoice_details = self.db.get_invoice_details(invoice_id)
        if not invoice_details:
            QMessageBox.warning(self, "Error", "Invoice not found.")
            return

        self.clear_form(keep_invoice_number=True) # Clear form but keep current invoice number logic

        self.current_invoice_id = invoice_details['id']
        self.original_invoice_id = invoice_details['original_invoice_id'] if invoice_details['original_invoice_id'] else invoice_details['id']

        self.invoice_number.setText(
            self.invoice_service.display_invoice_no(invoice_details['invoice_no'])
        )
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
                    data = combo.itemData(i)
                    if data and data[2] == desc:
                        found_index = i
                        break
                if found_index != -1:
                    combo.setCurrentIndex(found_index)
                    # Prefer latest HSN/SAC from master catalog if matched
                    master_data = combo.itemData(found_index)
                    if master_data:
                        sac_hsn = master_data[5]
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

        # Initialize fields
        self.name = QLineEdit(self.pdf_maker.company_info.get('name', ''))
        self.address = QTextEdit(self.pdf_maker.company_info.get('address', ''))
        self.address.setMaximumHeight(60)
        self.phone = QLineEdit(self.pdf_maker.company_info.get('phone', ''))
        self.email = QLineEdit(self.pdf_maker.company_info.get('email', ''))
        self.gstin = QLineEdit(self.pdf_maker.company_info.get('gstin', ''))

        self.bank_name = QLineEdit(self.pdf_maker.company_info.get('bank_name', ''))
        self.bank_account_name = QLineEdit(self.pdf_maker.company_info.get('bank_account_name', ''))
        self.bank_account_no = QLineEdit(self.pdf_maker.company_info.get('bank_account_no', ''))
        self.bank_branch = QLineEdit(self.pdf_maker.company_info.get('bank_branch', ''))
        self.bank_account_type = QLineEdit(self.pdf_maker.company_info.get('bank_account_type', ''))
        self.bank_ifsc_code = QLineEdit(self.pdf_maker.company_info.get('bank_ifsc_code', ''))
        self.bank_address = QTextEdit(self.pdf_maker.company_info.get('bank_address', ''))
        self.bank_address.setMaximumHeight(60)

        self.tax = QDoubleSpinBox()
        self.tax.setValue(float(self.service.tax_percent))
        self.tax.setSuffix(" %")

        self.terms = QTextEdit("\n".join(self.pdf_maker.terms))
        self.invoice_terms = QTextEdit("\n".join(self.pdf_maker.invoice_terms))

        self.logo_path = QLineEdit(self.pdf_maker.company_info.get('logo_path', ''))
        self.logo_path.setPlaceholderText("Path to logo image file (.png, .jpg, .jpeg)")
        self.browse_logo_btn = QPushButton("Browse...")
        self.browse_logo_btn.clicked.connect(self.browse_logo)

        self.seal_sign_path = QLineEdit(self.pdf_maker.company_info.get('seal_sign_path', ''))
        self.seal_sign_path.setPlaceholderText("Path to seal/signature image file (.png, .jpg, .jpeg)")
        self.browse_seal_btn = QPushButton("Browse...")
        self.browse_seal_btn.clicked.connect(self.browse_seal)

        # --- Layout organization ---

        # 1. Company Information Group
        comp_group = QGroupBox("Company Information")
        comp_grid = QGridLayout()
        comp_grid.addWidget(QLabel("Company Name:"), 0, 0)
        comp_grid.addWidget(self.name, 0, 1, 1, 3)
        comp_grid.addWidget(QLabel("Address:"), 1, 0)
        comp_grid.addWidget(self.address, 1, 1, 1, 3)
        comp_grid.addWidget(QLabel("Phone:"), 2, 0)
        comp_grid.addWidget(self.phone, 2, 1)
        comp_grid.addWidget(QLabel("Email:"), 2, 2)
        comp_grid.addWidget(self.email, 2, 3)
        comp_grid.addWidget(QLabel("GSTIN:"), 3, 0)
        comp_grid.addWidget(self.gstin, 3, 1)
        comp_group.setLayout(comp_grid)
        self.layout.addWidget(comp_group)

        # 2. Bank Details Group
        bank_group = QGroupBox("Bank Details")
        bank_grid = QGridLayout()
        bank_grid.addWidget(QLabel("Bank Name:"), 0, 0)
        bank_grid.addWidget(self.bank_name, 0, 1)
        bank_grid.addWidget(QLabel("Account Name:"), 0, 2)
        bank_grid.addWidget(self.bank_account_name, 0, 3)
        bank_grid.addWidget(QLabel("Account Number:"), 1, 0)
        bank_grid.addWidget(self.bank_account_no, 1, 1)
        bank_grid.addWidget(QLabel("Branch:"), 1, 2)
        bank_grid.addWidget(self.bank_branch, 1, 3)
        bank_grid.addWidget(QLabel("Type (Current/Saving):"), 2, 0)
        bank_grid.addWidget(self.bank_account_type, 2, 1)
        bank_grid.addWidget(QLabel("IFSC Code:"), 2, 2)
        bank_grid.addWidget(self.bank_ifsc_code, 2, 3)
        bank_grid.addWidget(QLabel("Bank Address:"), 3, 0)
        bank_grid.addWidget(self.bank_address, 3, 1, 1, 3)
        bank_group.setLayout(bank_grid)
        self.layout.addWidget(bank_group)

        # 3. Tax and Logo (Mixed Row)
        misc_layout = QHBoxLayout()
        
        tax_layout = QHBoxLayout()
        tax_layout.addWidget(QLabel("Default Tax %:"))
        tax_layout.addWidget(self.tax)
        misc_layout.addLayout(tax_layout)
        
        logo_layout = QHBoxLayout()
        logo_layout.addWidget(QLabel("Logo Path:"))
        logo_layout.addWidget(self.logo_path)
        logo_layout.addWidget(self.browse_logo_btn)
        misc_layout.addLayout(logo_layout)

        seal_layout = QHBoxLayout()
        seal_layout.addWidget(QLabel("Seal/Sign Path:"))
        seal_layout.addWidget(self.seal_sign_path)
        seal_layout.addWidget(self.browse_seal_btn)
        misc_layout.addLayout(seal_layout)
        
        self.layout.addLayout(misc_layout)

        # 4. Terms and Conditions (Side by Side)
        terms_layout = QHBoxLayout()
        
        quote_terms_box = QVBoxLayout()
        quote_terms_box.addWidget(QLabel("Quotation Terms & Conditions:"))
        quote_terms_box.addWidget(self.terms)
        
        invoice_terms_box = QVBoxLayout()
        invoice_terms_box.addWidget(QLabel("Invoice Terms & Conditions:"))
        invoice_terms_box.addWidget(self.invoice_terms)
        
        terms_layout.addLayout(quote_terms_box)
        terms_layout.addLayout(invoice_terms_box)
        self.layout.addLayout(terms_layout)

        # 5. Save Button (Small, right-aligned)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setFixedWidth(150)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)
        self.layout.addLayout(btn_layout)

    def save_settings(self):
        self.pdf_maker.company_info['name'] = self.name.text()
        self.pdf_maker.company_info['address'] = self.address.toPlainText()
        self.pdf_maker.company_info['phone'] = self.phone.text()
        self.pdf_maker.company_info['email'] = self.email.text()
        self.pdf_maker.company_info['gstin'] = self.gstin.text()
        self.pdf_maker.company_info['bank_name'] = self.bank_name.text()
        self.pdf_maker.company_info['bank_account_name'] = self.bank_account_name.text()
        self.pdf_maker.company_info['bank_account_no'] = self.bank_account_no.text()
        self.pdf_maker.company_info['bank_branch'] = self.bank_branch.text()
        self.pdf_maker.company_info['bank_account_type'] = self.bank_account_type.text()
        self.pdf_maker.company_info['bank_ifsc_code'] = self.bank_ifsc_code.text()
        self.pdf_maker.company_info['bank_address'] = self.bank_address.toPlainText()
        self.pdf_maker.company_info['logo_path'] = self.logo_path.text()
        self.pdf_maker.company_info['seal_sign_path'] = self.seal_sign_path.text()
        self.pdf_maker.terms = self.terms.toPlainText().splitlines()
        self.pdf_maker.company_info['terms'] = self.pdf_maker.terms
        self.pdf_maker.invoice_terms = self.invoice_terms.toPlainText().splitlines()
        self.pdf_maker.company_info['invoice_terms'] = self.pdf_maker.invoice_terms
        self.service.tax_percent = Decimal(str(self.tax.value()))
        self.pdf_maker.seal_sign_path = self.seal_sign_path.text()
        # Persist to file
        save_company_info(self.pdf_maker.company_info)
        QMessageBox.information(self, "Saved", "Settings updated!")

    def browse_logo(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Image files (*.png *.jpg *.jpeg *.bmp)")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                logo_file_path = selected_files[0]
                # Copy the logo to a local directory
                import shutil
                logo_dir = os.path.join(os.path.dirname(__file__), "logos")
                os.makedirs(logo_dir, exist_ok=True)
                logo_filename = os.path.basename(logo_file_path)
                local_logo_path = os.path.join(logo_dir, logo_filename)
                try:
                    shutil.copy2(logo_file_path, local_logo_path)
                    self.logo_path.setText(local_logo_path)
                    QMessageBox.information(self, "Logo Selected", f"Logo copied to: {local_logo_path}")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to copy logo: {str(e)}")

    def browse_seal(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Image files (*.png *.jpg *.jpeg)")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                import shutil
                src_path = selected_files[0]
                logo_dir = os.path.join(os.path.dirname(__file__), "logos")
                os.makedirs(logo_dir, exist_ok=True)
                dst_path = os.path.join(logo_dir, os.path.basename(src_path))
                try:
                    shutil.copy2(src_path, dst_path)
                    self.seal_sign_path.setText(dst_path)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to copy image: {str(e)}")

# ---------- Proforma Invoice Tab ----------
class ProformaInvoiceTab(QWidget):
    def __init__(self, db: Database, quotation_service: QuotationService):
        super().__init__()
        self.db = db
        self.quotation_service = quotation_service
        self.current_proforma_id = None
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search proforma invoices...")
        self.search_input.textChanged.connect(self.search_proformas)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        self.layout.addLayout(search_layout)

        # Status filter
        filter_layout = QHBoxLayout()
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Draft", "Issued", "Paid", "Cancelled"])
        self.status_filter.currentTextChanged.connect(self.filter_by_status)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        self.layout.addLayout(filter_layout)

        # Proforma list table
        self.proforma_table = QTableWidget()
        self.proforma_table.setColumnCount(6)
        self.proforma_table.setHorizontalHeaderLabels(["ID", "Proforma No", "Date", "Customer", "Total", "Status"])
        self.proforma_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.proforma_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.proforma_table.itemSelectionChanged.connect(self.on_proforma_selected)
        self.layout.addWidget(self.proforma_table)

        # Buttons
        button_layout = QHBoxLayout()
        self.create_from_quote_btn = QPushButton("Create from Quotation")
        self.create_from_quote_btn.clicked.connect(self.create_from_quotation)
        self.edit_btn = QPushButton("Edit Proforma")
        self.edit_btn.clicked.connect(self.edit_proforma)
        self.edit_btn.setEnabled(False)
        self.generate_pdf_btn = QPushButton("Generate PDF")
        self.generate_pdf_btn.clicked.connect(self.generate_pdf)
        self.generate_pdf_btn.setEnabled(False)
        self.update_status_btn = QPushButton("Update Status")
        self.update_status_btn.clicked.connect(self.update_status)
        self.update_status_btn.setEnabled(False)
        button_layout.addWidget(self.create_from_quote_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.generate_pdf_btn)
        button_layout.addWidget(self.update_status_btn)
        button_layout.addStretch()
        self.layout.addLayout(button_layout)

        # Load initial data
        self.load_proformas()

    def load_proformas(self):
        self.proforma_table.setRowCount(0)
        proformas = self.db.get_all_proforma_invoices()

        for row, proforma in enumerate(proformas):
            self.proforma_table.insertRow(row)
            proforma_id, proforma_no, date, customer, total, status = proforma

            self.proforma_table.setItem(row, 0, QTableWidgetItem(str(proforma_id)))
            self.proforma_table.setItem(row, 1, QTableWidgetItem(proforma_no))
            self.proforma_table.setItem(row, 2, QTableWidgetItem(date))
            self.proforma_table.setItem(row, 3, QTableWidgetItem(customer or ""))
            self.proforma_table.setItem(row, 4, QTableWidgetItem(f"{total:.2f}"))
            self.proforma_table.setItem(row, 5, create_status_item(status or "Draft"))

    def search_proformas(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            self.load_proformas()
            return

        self.proforma_table.setRowCount(0)
        proformas = self.db.search_proforma_invoices(keyword)

        for row, proforma in enumerate(proformas):
            self.proforma_table.insertRow(row)
            proforma_id, proforma_no, date, customer, total, status = proforma

            self.proforma_table.setItem(row, 0, QTableWidgetItem(str(proforma_id)))
            self.proforma_table.setItem(row, 1, QTableWidgetItem(proforma_no))
            self.proforma_table.setItem(row, 2, QTableWidgetItem(date))
            self.proforma_table.setItem(row, 3, QTableWidgetItem(customer or ""))
            self.proforma_table.setItem(row, 4, QTableWidgetItem(f"{total:.2f}"))
            self.proforma_table.setItem(row, 5, create_status_item(status or "Draft"))

    def filter_by_status(self):
        status = self.status_filter.currentText()
        if status == "All":
            self.load_proformas()
            return

        self.proforma_table.setRowCount(0)
        all_proformas = self.db.get_all_proforma_invoices()

        for row, proforma in enumerate(all_proformas):
            proforma_id, proforma_no, date, customer, total, proforma_status = proforma
            if proforma_status == status or (status == "Draft" and not proforma_status):
                self.proforma_table.insertRow(self.proforma_table.rowCount())
                current_row = self.proforma_table.rowCount() - 1
                self.proforma_table.setItem(current_row, 0, QTableWidgetItem(str(proforma_id)))
                self.proforma_table.setItem(current_row, 1, QTableWidgetItem(proforma_no))
                self.proforma_table.setItem(current_row, 2, QTableWidgetItem(date))
                self.proforma_table.setItem(current_row, 3, QTableWidgetItem(customer or ""))
                self.proforma_table.setItem(current_row, 4, QTableWidgetItem(f"{total:.2f}"))
                self.proforma_table.setItem(current_row, 5, create_status_item(proforma_status or "Draft"))

    def on_proforma_selected(self):
        selected_rows = set()
        for item in self.proforma_table.selectedItems():
            selected_rows.add(item.row())

        has_selection = len(selected_rows) > 0
        self.edit_btn.setEnabled(has_selection)
        self.generate_pdf_btn.setEnabled(has_selection)
        self.update_status_btn.setEnabled(has_selection)

        if len(selected_rows) == 1:
            row = list(selected_rows)[0]
            self.current_proforma_id = int(self.proforma_table.item(row, 0).text())

    def create_from_quotation(self):
        # Show quotation selection dialog
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Quotation")
        dialog.resize(600, 400)

        layout = QVBoxLayout()

        # Quotation list
        self.quote_list = QListWidget()
        quotations = self.db.get_all_quotations()
        for quote in quotations:
            quote_id, quote_no, date, customer, total, status = quote
            self.quote_list.addItem(f"{quote_no} - {customer} - {date} - ₹{total:.2f}")

        layout.addWidget(QLabel("Select a quotation to create proforma from:"))
        layout.addWidget(self.quote_list)

        # Buttons
        button_layout = QHBoxLayout()
        select_btn = QPushButton("Create Proforma")
        select_btn.clicked.connect(lambda: self.do_create_from_quotation(dialog))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(select_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        dialog.exec()

    def do_create_from_quotation(self, dialog):
        selected_items = self.quote_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a quotation.")
            return

        # Get quotation ID from selected item
        selected_text = selected_items[0].text()
        quote_no = selected_text.split(" - ")[0]

        # Find quotation by quote_no
        quotations = self.db.get_all_quotations()
        quotation_id = None
        for quote in quotations:
            if quote[1] == quote_no:  # quote_no is at index 1
                quotation_id = quote[0]
                break

        if not quotation_id:
            QMessageBox.warning(self, "Error", "Could not find quotation.")
            return

        # Generate proforma number
        from datetime import datetime
        today = datetime.now()
        date_str = today.strftime("%Y%m%d")
        last_seq = self.db.get_last_proforma_sequence_for_date(date_str)
        if last_seq:
            # Extract sequence number from last proforma_no (format: YYYYMMDD-XXX)
            seq_part = last_seq.split('-')[-1]
            seq_num = int(seq_part) + 1
        else:
            seq_num = 1
        proforma_no = f"{date_str}-{seq_num:03d}"

        try:
            proforma_id = self.db.create_proforma_from_quotation(quotation_id, proforma_no, today.strftime("%Y-%m-%d"))
            QMessageBox.information(self, "Success", f"Proforma invoice {proforma_no} created successfully!")
            dialog.accept()
            self.load_proformas()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create proforma: {str(e)}")

    def edit_proforma(self):
        if not self.current_proforma_id:
            return

        # Open edit dialog
        dialog = ProformaEditDialog(self.db, self.current_proforma_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_proformas()

    def generate_pdf(self):
        if not self.current_proforma_id:
            return

        try:
            # Get proforma details
            proforma = self.db.get_proforma_details(self.current_proforma_id)
            if not proforma:
                QMessageBox.warning(self, "Error", "Proforma not found.")
                return

            # Get customer details
            customer = self.db.get_customer(proforma['customer_id'])
            if not customer:
                QMessageBox.warning(self, "Error", "Customer not found.")
                return

            # Get items
            items = self.db.get_proforma_items(self.current_proforma_id)

            # Generate PDF
            from quotation_tool import ProformaPDF
            pdf_terms = proforma.get('terms')
            if pdf_terms:
                pdf_terms = pdf_terms.split('\n')
            else:
                pdf_terms = default_proforma_terms()

            pdf_maker = ProformaPDF(self.quotation_service.pdf_maker.company_info, pdf_terms, self.quotation_service.pdf_maker.logo_path)

            file_path = pdf_maker.generate_pdf(
                proforma_no=proforma['proforma_no'],
                proforma_date=proforma['proforma_date'],
                customer=customer,
                items=items,
                subtotal=proforma['subtotal'],
                tax_percent=proforma['tax_percent'],
                tax_amount=proforma['tax_amount'],
                total=proforma['total'],
                currency=proforma['currency'],
                notes=proforma.get('notes', '')
            )

            # Update PDF path in database
            self.db.update_proforma_pdf_path(self.current_proforma_id, file_path)

            QMessageBox.information(self, "Success", f"PDF generated: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF: {str(e)}")

    def update_status(self):
        if not self.current_proforma_id:
            return

        # Status update dialog
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QLineEdit, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Update Proforma Status")

        layout = QVBoxLayout()

        # Status dropdown
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Draft", "Issued", "Paid", "Cancelled"])
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.status_combo)

        # Advance payment fields (only for Paid status)
        self.advance_amount = QLineEdit()
        self.advance_date = QLineEdit()
        self.advance_date.setPlaceholderText("YYYY-MM-DD")
        layout.addWidget(QLabel("Advance Amount (₹):"))
        layout.addWidget(self.advance_amount)
        layout.addWidget(QLabel("Advance Date:"))
        layout.addWidget(self.advance_date)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(lambda: self.do_update_status(dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setLayout(layout)
        dialog.exec()

    def do_update_status(self, dialog):
        status = self.status_combo.currentText()
        advance_amount = None
        advance_date = None

        if status == "Paid":
            try:
                advance_amount = float(self.advance_amount.text().strip())
                advance_date = self.advance_date.text().strip()
                if not advance_date:
                    QMessageBox.warning(self, "Error", "Advance date is required for Paid status.")
                    return
            except ValueError:
                QMessageBox.warning(self, "Error", "Invalid advance amount.")
                return

        try:
            self.db.update_proforma_status(self.current_proforma_id, status, advance_amount, advance_date)
            QMessageBox.information(self, "Success", "Status updated successfully!")
            dialog.accept()
            self.load_proformas()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update status: {str(e)}")


# ---------- Proforma Edit Dialog ----------
class ProformaEditDialog(QDialog):
    def __init__(self, db: Database, proforma_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.proforma_id = proforma_id
        self.setWindowTitle("Edit Proforma Invoice")
        self.resize(800, 600)

        # Get proforma data
        self.proforma = self.db.get_proforma_details(proforma_id)
        self.items = list(self.db.get_proforma_items(proforma_id))

        layout = QVBoxLayout()

        # Proforma info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"Proforma No: {self.proforma['proforma_no']}"))
        info_layout.addWidget(QLabel(f"Date: {self.proforma['proforma_date']}"))
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels(["Description", "Code", "Qty", "Unit", "Unit Price", "SAC/HSN", "Total"])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(QLabel("Items:"))
        layout.addWidget(self.items_table)

        # Load items
        self.load_items()

        # Item buttons
        item_buttons = QHBoxLayout()
        self.add_item_btn = QPushButton("Add Item")
        self.add_item_btn.clicked.connect(self.add_item)
        self.edit_item_btn = QPushButton("Edit Item")
        self.edit_item_btn.clicked.connect(self.edit_item)
        self.delete_item_btn = QPushButton("Delete Item")
        self.delete_item_btn.clicked.connect(self.delete_item)
        item_buttons.addWidget(self.add_item_btn)
        item_buttons.addWidget(self.edit_item_btn)
        item_buttons.addWidget(self.delete_item_btn)
        item_buttons.addStretch()
        layout.addLayout(item_buttons)

        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(self.proforma.get('notes', ''))
        layout.addWidget(QLabel("Notes:"))
        layout.addWidget(self.notes_edit)

        # Proforma terms (editable)
        self.terms_edit = QTextEdit()
        self.terms_edit.setPlainText(self.proforma.get('terms', '\n'.join(default_proforma_terms())))
        layout.addWidget(QLabel("Proforma Terms & Conditions:"))
        layout.addWidget(self.terms_edit)

        # Totals
        totals_layout = QHBoxLayout()
        self.subtotal_label = QLabel(f"Subtotal: ₹{self.proforma['subtotal']:.2f}")
        self.tax_label = QLabel(f"Tax ({self.proforma['tax_percent']}%): ₹{self.proforma['tax_amount']:.2f}")
        self.total_label = QLabel(f"Total: ₹{self.proforma['total']:.2f}")
        totals_layout.addWidget(self.subtotal_label)
        totals_layout.addWidget(self.tax_label)
        totals_layout.addWidget(self.total_label)
        totals_layout.addStretch()
        layout.addLayout(totals_layout)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_changes)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_items(self):
        self.items_table.setRowCount(0)
        for row, item in enumerate(self.items):
            self.items_table.insertRow(row)
            desc, code, qty, unit, price, line_total, hsn = item
            total = line_total  # Use the stored line_total

            self.items_table.setItem(row, 0, QTableWidgetItem(desc))
            self.items_table.setItem(row, 1, QTableWidgetItem(code or ""))
            self.items_table.setItem(row, 2, QTableWidgetItem(str(qty)))
            self.items_table.setItem(row, 3, QTableWidgetItem(unit))
            self.items_table.setItem(row, 4, QTableWidgetItem(f"{price:.2f}"))
            self.items_table.setItem(row, 5, QTableWidgetItem(str(hsn) if hsn else ""))
            self.items_table.setItem(row, 6, QTableWidgetItem(f"{total:.2f}"))

    def add_item(self):
        dialog = ItemEditDialog("Add Item", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            desc, code, qty, unit, price, hsn = dialog.get_item_data()
            self.items.append((desc, code, qty, unit, price, qty * price, hsn))
            self.load_items()
            self.update_totals()

    def edit_item(self):
        selected_rows = set()
        for item in self.items_table.selectedItems():
            selected_rows.add(item.row())

        if len(selected_rows) != 1:
            QMessageBox.warning(self, "Selection Error", "Please select exactly one item to edit.")
            return

        row = list(selected_rows)[0]
        current_item = self.items[row]

        dialog = ItemEditDialog("Edit Item", self)
        dialog.set_item_data(current_item[0], current_item[1], current_item[2], current_item[3], current_item[4], current_item[6])  # desc, code, qty, unit, price, hsn

        if dialog.exec() == QDialog.DialogCode.Accepted:
            desc, code, qty, unit, price, hsn = dialog.get_item_data()
            self.items[row] = (desc, code, qty, unit, price, qty * price, hsn)
            self.load_items()
            self.update_totals()

    def delete_item(self):
        selected_rows = sorted(set(item.row() for item in self.items_table.selectedItems()), reverse=True)

        if not selected_rows:
            QMessageBox.warning(self, "Selection Error", "Please select items to delete.")
            return

        for row in selected_rows:
            del self.items[row]

        self.load_items()
        self.update_totals()

    def update_totals(self):
        subtotal = sum(item[5] for item in self.items)  # line_total is at index 5
        tax_percent = self.proforma['tax_percent']
        tax_amount = (subtotal * tax_percent) / 100
        total = subtotal + tax_amount

        self.subtotal_label.setText(f"Subtotal: ₹{subtotal:.2f}")
        self.tax_label.setText(f"Tax ({tax_percent}%): ₹{tax_amount:.2f}")
        self.total_label.setText(f"Total: ₹{total:.2f}")

    def save_changes(self):
        try:
            notes = self.notes_edit.toPlainText()
            proforma_terms = self.terms_edit.toPlainText()

            self.update_totals()
            subtotal = sum(item[5] for item in self.items)
            tax_amount = (subtotal * self.proforma['tax_percent']) / 100
            total = subtotal + tax_amount

            self.db.save_proforma_changes(
                self.proforma_id,
                self.items,
                notes,
                proforma_terms,
                subtotal,
                tax_amount,
                total,
            )

            QMessageBox.information(self, "Success", "Proforma updated successfully!")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {str(e)}")


# ---------- Item Edit Dialog ----------
class ItemEditDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 300)

        layout = QVBoxLayout()

        # Form fields
        self.desc_edit = QTextEdit()
        self.code_edit = QLineEdit()
        self.qty_spin = QSpinBox()
        self.qty_spin.setMinimum(1)
        self.unit_edit = QLineEdit()
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setMinimum(0)
        self.price_spin.setMaximum(999999)
        self.hsn_edit = QLineEdit()

        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.desc_edit)
        layout.addWidget(QLabel("Item Code:"))
        layout.addWidget(self.code_edit)
        layout.addWidget(QLabel("Quantity:"))
        layout.addWidget(self.qty_spin)
        layout.addWidget(QLabel("Unit:"))
        layout.addWidget(self.unit_edit)
        layout.addWidget(QLabel("Unit Price:"))
        layout.addWidget(self.price_spin)
        layout.addWidget(QLabel("SAC/HSN:"))
        layout.addWidget(self.hsn_edit)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def set_item_data(self, desc, code, qty, unit, price, hsn):
        self.desc_edit.setPlainText(desc)
        self.code_edit.setText(code or "")
        self.qty_spin.setValue(int(qty))
        self.unit_edit.setText(unit)
        self.price_spin.setValue(float(price))
        self.hsn_edit.setText(hsn or "")

    def get_item_data(self):
        return (
            self.desc_edit.toPlainText(),
            self.code_edit.text(),
            self.qty_spin.value(),
            self.unit_edit.text(),
            self.price_spin.value(),
            self.hsn_edit.text()
        )
