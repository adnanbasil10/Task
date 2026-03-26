"""
Generate realistic SAP-style supply chain CSV data.
Creates 9 CSV files with intentional broken flows for testing.
"""
import csv
import os
import random
from datetime import datetime, timedelta

random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# --- Helpers ---
def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def write_csv(filename, headers, rows):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"  ✓ {filename}: {len(rows)} records")

# --- Customers ---
FIRST_NAMES = ["James","Maria","Robert","Linda","David","Sarah","Michael","Emma","William","Olivia",
               "John","Sophia","Richard","Isabella","Thomas","Mia","Charles","Charlotte","Daniel","Amelia"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
              "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin"]
SEGMENTS = ["Enterprise", "Mid-Market", "SMB", "Government", "Education"]
DOMAINS = ["acme.com","globex.com","initech.com","umbrella.com","starkindustries.com",
           "wayneent.com","oscorp.com","lexcorp.com","cyberdyne.com","soylent.com"]

customers = []
for i in range(1, 51):
    cid = f"CUST-{i:03d}"
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    name = f"{fn} {ln}"
    email = f"{fn.lower()}.{ln.lower()}@{random.choice(DOMAINS)}"
    phone = f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"
    segment = random.choice(SEGMENTS)
    customers.append((cid, name, email, phone, segment))

write_csv("customers.csv", ["id","name","email","phone","segment"], customers)

# --- Products ---
CATEGORIES = ["Raw Materials", "Components", "Finished Goods", "Packaging", "Services"]
PRODUCT_NAMES = [
    "Steel Coil","Aluminum Sheet","Copper Wire","Plastic Resin","Glass Panel",
    "Circuit Board","Hydraulic Pump","Electric Motor","Sensor Module","Battery Pack",
    "Industrial Valve","Rubber Gasket","LED Display","Power Supply","Control Unit",
    "Bearing Assembly","Heat Exchanger","Filter Cartridge","Welding Rod","Safety Helmet",
    "Conveyor Belt","Gear Box","Transformer","Cable Harness","Pressure Gauge",
    "O-Ring Set","Thermal Paste","Optical Fiber","Cooling Fan","Junction Box"
]

products = []
for i in range(1, 31):
    pid = f"PROD-{i:03d}"
    name = PRODUCT_NAMES[i-1]
    category = random.choice(CATEGORIES)
    unit_price = round(random.uniform(5.0, 500.0), 2)
    sku = f"SKU-{random.randint(10000,99999)}"
    products.append((pid, name, category, unit_price, sku))

write_csv("products.csv", ["id","name","category","unit_price","sku"], products)

# --- Addresses ---
STREETS = ["123 Main St","456 Oak Ave","789 Pine Rd","321 Elm Blvd","654 Maple Dr",
           "987 Cedar Ln","147 Birch Way","258 Spruce Ct","369 Walnut Pl","741 Cherry St"]
CITIES = ["New York","Los Angeles","Chicago","Houston","Phoenix","Philadelphia",
          "San Antonio","San Diego","Dallas","San Jose"]
STATES = ["NY","CA","IL","TX","AZ","PA","TX","CA","TX","CA"]
ZIPS = ["10001","90001","60601","77001","85001","19101","78201","92101","75201","95101"]

addresses = []
for i in range(1, 61):
    aid = f"ADDR-{i:03d}"
    idx = random.randint(0, len(STREETS)-1)
    street = f"{random.randint(1,9999)} {STREETS[idx].split(' ',1)[1]}"
    city = CITIES[idx]
    state = STATES[idx]
    postal = ZIPS[idx]
    country = "US"
    addresses.append((aid, street, city, state, postal, country))

write_csv("addresses.csv", ["id","street","city","state","postal_code","country"], addresses)

# --- Orders ---
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 12, 31)
ORDER_STATUSES = ["CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]

orders = []
for i in range(1, 101):
    oid = f"ORD-{i:03d}"
    customer_id = random.choice(customers)[0]
    order_date = random_date(START_DATE, END_DATE).strftime("%Y-%m-%d")
    status = random.choice(ORDER_STATUSES)
    total = 0  # will be computed from items
    orders.append([oid, customer_id, order_date, status, total])

# --- Order Items ---
order_items = []
item_counter = 1
for order in orders:
    num_items = random.randint(1, 5)
    order_total = 0
    for _ in range(num_items):
        iid = f"OI-{item_counter:04d}"
        product = random.choice(products)
        qty = random.randint(1, 20)
        unit_price = product[3]
        total = round(qty * unit_price, 2)
        order_total += total
        order_items.append((iid, order[0], product[0], qty, unit_price, total))
        item_counter += 1
    order[4] = round(order_total, 2)

write_csv("orders.csv", ["id","customer_id","order_date","status","total_amount"], orders)
write_csv("order_items.csv", ["id","order_id","product_id","quantity","unit_price","total"], order_items)

# --- Deliveries (intentionally skip some orders) ---
DELIVERY_STATUSES = ["IN_TRANSIT", "DELIVERED", "RETURNED", "PENDING"]
delivered_orders = orders[:90]  # skip last 10 orders -> no delivery

deliveries = []
del_counter = 1
for order in delivered_orders:
    num_deliveries = 1 if random.random() > 0.15 else 2  # some orders have split deliveries
    for _ in range(num_deliveries):
        did = f"DEL-{del_counter:03d}"
        address_id = random.choice(addresses)[0]
        order_date = datetime.strptime(order[2], "%Y-%m-%d")
        delivery_date = (order_date + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d")
        status = random.choice(DELIVERY_STATUSES)
        tracking = f"TRK{random.randint(100000000, 999999999)}"
        deliveries.append((did, order[0], address_id, delivery_date, status, tracking))
        del_counter += 1

write_csv("deliveries.csv", ["id","order_id","address_id","delivery_date","status","tracking_number"], deliveries)

# --- Invoices (intentionally skip some delivered orders) ---
INVOICE_STATUSES = ["DRAFT", "SENT", "PAID", "OVERDUE", "CANCELLED"]
invoiced_orders = delivered_orders[:75]  # skip 15 delivered orders -> DELIVERED_NOT_BILLED

invoices = []
inv_counter = 1
for order in invoiced_orders:
    iid = f"INV-{inv_counter:03d}"
    order_date = datetime.strptime(order[2], "%Y-%m-%d")
    invoice_date = (order_date + timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d")
    due_date = (order_date + timedelta(days=random.randint(30, 60))).strftime("%Y-%m-%d")
    status = random.choice(INVOICE_STATUSES)
    total_amount = order[4]
    invoices.append((iid, order[0], invoice_date, due_date, status, total_amount))
    inv_counter += 1

# Add a few invoices for non-delivered orders -> BILLED_NOT_DELIVERED
for order in orders[90:95]:
    iid = f"INV-{inv_counter:03d}"
    order_date = datetime.strptime(order[2], "%Y-%m-%d")
    invoice_date = (order_date + timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d")
    due_date = (order_date + timedelta(days=random.randint(30, 60))).strftime("%Y-%m-%d")
    status = random.choice(INVOICE_STATUSES)
    total_amount = order[4]
    invoices.append((iid, order[0], invoice_date, due_date, status, total_amount))
    inv_counter += 1

write_csv("invoices.csv", ["id","order_id","invoice_date","due_date","status","total_amount"], invoices)

# --- Invoice Items ---
invoice_items_list = []
ii_counter = 1
for inv in invoices:
    num_items = random.randint(1, 4)
    for j in range(num_items):
        iiid = f"II-{ii_counter:04d}"
        desc = f"Line item {j+1} for {inv[0]}"
        qty = random.randint(1, 10)
        unit_price = round(random.uniform(10.0, 200.0), 2)
        total = round(qty * unit_price, 2)
        invoice_items_list.append((iiid, inv[0], desc, qty, unit_price, total))
        ii_counter += 1

write_csv("invoice_items.csv", ["id","invoice_id","description","quantity","unit_price","total"], invoice_items_list)

# --- Payments (intentionally skip some invoices) ---
PAYMENT_METHODS = ["BANK_TRANSFER", "CREDIT_CARD", "CHECK", "WIRE", "ACH"]
PAYMENT_STATUSES = ["COMPLETED", "PENDING", "FAILED", "REFUNDED"]
paid_invoices = invoices[:65]  # skip last ~15 invoices -> PAYMENT_MISSING

payments = []
pay_counter = 1
for inv in paid_invoices:
    pid = f"PAY-{pay_counter:03d}"
    inv_date = datetime.strptime(inv[2], "%Y-%m-%d")
    payment_date = (inv_date + timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
    amount = inv[5]
    method = random.choice(PAYMENT_METHODS)
    status = random.choice(PAYMENT_STATUSES)
    payments.append((pid, inv[0], payment_date, amount, method, status))
    pay_counter += 1

write_csv("payments.csv", ["id","invoice_id","payment_date","amount","method","status"], payments)

print(f"\n✅ All CSV files generated in {DATA_DIR}/")
print(f"   Intentional broken flows:")
print(f"   - Orders without delivery: {len(orders) - len(delivered_orders)}")
print(f"   - Delivered but not billed: {len(delivered_orders) - len(invoiced_orders)}")
print(f"   - Billed but not delivered: {len(orders[90:95])}")
print(f"   - Invoices without payment: {len(invoices) - len(paid_invoices)}")
