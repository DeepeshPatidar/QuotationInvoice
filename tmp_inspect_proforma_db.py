import sqlite3
import os
os.chdir(r'd:\ApexAutomobileTesting\Offer\PythonApp')
conn = sqlite3.connect('quotation.db')
cur = conn.cursor()
quote_no = 'Q-20260406-0007'
cur.execute('SELECT id, quote_no, subtotal, tax_percent, tax_amount, total FROM quotations WHERE quote_no=?', (quote_no,))
quote = cur.fetchone()
print('QUOTE:', quote)
if quote:
    qid = quote[0]
    cur.execute('SELECT item_description, item_code, qty, unit, unit_price, line_total, sac_hsn FROM quotation_items WHERE quotation_id=?', (qid,))
    print('QUOTE ITEMS:')
    for row in cur.fetchall():
        print(row)
cur.execute('SELECT id, proforma_no, quotation_id, subtotal, tax_percent, tax_amount, total FROM proforma_invoices')
print('PROFORMA:')
for row in cur.fetchall():
    print(row)
cur.execute('SELECT proforma_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn FROM proforma_items')
print('PROFORMA ITEMS:')
for row in cur.fetchall():
    print(row)
conn.close()
