"""
Graph API routes: /api/graph, /api/node/:type/:id
"""
from fastapi import APIRouter, HTTPException
from db import execute_readonly

router = APIRouter(prefix="/api", tags=["graph"])

# Color mapping for node types
NODE_COLORS = {
    "ORDER": "#228be6",
    "DELIVERY": "#40c057",
    "INVOICE": "#fab005",
    "PAYMENT": "#7950f2",
    "CUSTOMER": "#e64980",
    "PRODUCT": "#15aabf",
}

NODE_TYPE_TABLE = {
    "ORDER": "orders",
    "DELIVERY": "deliveries",
    "INVOICE": "invoices",
    "PAYMENT": "payments",
    "CUSTOMER": "customers",
    "PRODUCT": "products",
}


def _build_node(row: dict, node_type: str) -> dict:
    """Build a graph node from a database row."""
    node_id = row["id"]
    
    # Build label based on type
    if node_type == "ORDER":
        label = f"Order {node_id}\n{row.get('status', '')}"
    elif node_type == "DELIVERY":
        label = f"Delivery {node_id}\n{row.get('status', '')}"
    elif node_type == "INVOICE":
        label = f"Invoice {node_id}\n${row.get('total_amount', 0)}"
    elif node_type == "PAYMENT":
        label = f"Payment {node_id}\n{row.get('method', '')}"
    elif node_type == "CUSTOMER":
        label = f"{row.get('name', node_id)}\n{row.get('segment', '')}"
    elif node_type == "PRODUCT":
        label = f"{row.get('name', node_id)}\n${row.get('unit_price', 0)}"
    else:
        label = node_id
    
    return {
        "id": node_id,
        "type": node_type,
        "label": label,
        "color": NODE_COLORS.get(node_type, "#6B7280"),
        "metadata": {k: v for k, v in row.items()}
    }


@router.get("/graph")
async def get_graph():
    """Return full graph with all nodes and edges."""
    nodes = []
    edges = []
    
    # Customers
    for row in execute_readonly("SELECT * FROM customers"):
        nodes.append(_build_node(row, "CUSTOMER"))
    
    # Products
    for row in execute_readonly("SELECT * FROM products"):
        nodes.append(_build_node(row, "PRODUCT"))
    
    # Orders + edges to customers
    for row in execute_readonly("SELECT * FROM orders"):
        nodes.append(_build_node(row, "ORDER"))
        edges.append({
            "source": row["customer_id"],
            "target": row["id"],
            "relationship_label": "PLACED_ORDER"
        })
    
    # Order items → edges from orders to products
    for row in execute_readonly("SELECT DISTINCT order_id, product_id FROM order_items"):
        edges.append({
            "source": row["order_id"],
            "target": row["product_id"],
            "relationship_label": "CONTAINS_PRODUCT"
        })
    
    # Deliveries + edges to orders
    for row in execute_readonly("SELECT * FROM deliveries"):
        nodes.append(_build_node(row, "DELIVERY"))
        edges.append({
            "source": row["order_id"],
            "target": row["id"],
            "relationship_label": "HAS_DELIVERY"
        })
    
    # Invoices + edges to orders
    for row in execute_readonly("SELECT * FROM invoices"):
        nodes.append(_build_node(row, "INVOICE"))
        edges.append({
            "source": row["order_id"],
            "target": row["id"],
            "relationship_label": "HAS_INVOICE"
        })
    
    # Payments + edges to invoices
    for row in execute_readonly("SELECT * FROM payments"):
        nodes.append(_build_node(row, "PAYMENT"))
        edges.append({
            "source": row["invoice_id"],
            "target": row["id"],
            "relationship_label": "HAS_PAYMENT"
        })
    
    return {"nodes": nodes, "edges": edges}


@router.get("/node/{node_type}/{node_id}")
async def get_node(node_type: str, node_id: str):
    """Return full metadata for a single node + connected node IDs."""
    node_type_upper = node_type.upper()
    table = NODE_TYPE_TABLE.get(node_type_upper)
    
    if not table:
        raise HTTPException(status_code=400, detail=f"Invalid node type: {node_type}")
    
    rows = execute_readonly(f"SELECT * FROM {table} WHERE id = ?", (node_id,))
    if not rows:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_type}/{node_id}")
    
    row = rows[0]
    node = _build_node(row, node_type_upper)
    
    # Find connected nodes
    connected = []
    
    if node_type_upper == "CUSTOMER":
        orders = execute_readonly("SELECT id FROM orders WHERE customer_id = ?", (node_id,))
        connected.extend([{"id": o["id"], "type": "ORDER"} for o in orders])
    
    elif node_type_upper == "ORDER":
        # Customer
        connected.append({"id": row["customer_id"], "type": "CUSTOMER"})
        # Items/Products
        items = execute_readonly("SELECT DISTINCT product_id FROM order_items WHERE order_id = ?", (node_id,))
        connected.extend([{"id": i["product_id"], "type": "PRODUCT"} for i in items])
        # Deliveries
        deliveries = execute_readonly("SELECT id FROM deliveries WHERE order_id = ?", (node_id,))
        connected.extend([{"id": d["id"], "type": "DELIVERY"} for d in deliveries])
        # Invoices
        invoices = execute_readonly("SELECT id FROM invoices WHERE order_id = ?", (node_id,))
        connected.extend([{"id": inv["id"], "type": "INVOICE"} for inv in invoices])
    
    elif node_type_upper == "DELIVERY":
        orders = execute_readonly("SELECT order_id FROM deliveries WHERE id = ?", (node_id,))
        connected.extend([{"id": o["order_id"], "type": "ORDER"} for o in orders])
    
    elif node_type_upper == "INVOICE":
        orders = execute_readonly("SELECT order_id FROM invoices WHERE id = ?", (node_id,))
        connected.extend([{"id": o["order_id"], "type": "ORDER"} for o in orders])
        payments = execute_readonly("SELECT id FROM payments WHERE invoice_id = ?", (node_id,))
        connected.extend([{"id": p["id"], "type": "PAYMENT"} for p in payments])
    
    elif node_type_upper == "PAYMENT":
        invoices = execute_readonly("SELECT invoice_id FROM payments WHERE id = ?", (node_id,))
        connected.extend([{"id": inv["invoice_id"], "type": "INVOICE"} for inv in invoices])
    
    elif node_type_upper == "PRODUCT":
        orders = execute_readonly("SELECT DISTINCT order_id FROM order_items WHERE product_id = ?", (node_id,))
        connected.extend([{"id": o["order_id"], "type": "ORDER"} for o in orders])
    
    node["connected_nodes"] = connected
    return node
