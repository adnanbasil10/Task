"""
Flow routes: /api/flow/:order_id, /api/broken-flows
"""
from fastapi import APIRouter, HTTPException
from db import execute_readonly
from validator import detect_broken_flows

router = APIRouter(prefix="/api", tags=["flows"])


@router.get("/flow/{order_id}")
async def get_order_flow(order_id: str):
    """
    Return the complete trace for an order:
    Order → Items → Delivery → Invoice → InvoiceItems → Payment
    Flags any broken steps explicitly.
    """
    # Get order
    orders = execute_readonly("SELECT * FROM orders WHERE id = ?", (order_id,))
    if not orders:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    
    order = dict(orders[0])
    
    # Get order items
    items = execute_readonly(
        "SELECT oi.*, p.name as product_name FROM order_items oi "
        "LEFT JOIN products p ON oi.product_id = p.id "
        "WHERE oi.order_id = ?", (order_id,)
    )
    
    # Get deliveries
    deliveries = execute_readonly(
        "SELECT d.*, a.city, a.state FROM deliveries d "
        "LEFT JOIN addresses a ON d.address_id = a.id "
        "WHERE d.order_id = ?", (order_id,)
    )
    
    # Get invoices
    invoices = execute_readonly(
        "SELECT * FROM invoices WHERE order_id = ?", (order_id,)
    )
    
    # Get invoice items and payments for each invoice
    invoice_details = []
    for inv in invoices:
        inv_dict = dict(inv)
        inv_items = execute_readonly(
            "SELECT * FROM invoice_items WHERE invoice_id = ?", (inv["id"],)
        )
        inv_payments = execute_readonly(
            "SELECT * FROM payments WHERE invoice_id = ?", (inv["id"],)
        )
        inv_dict["items"] = [dict(ii) for ii in inv_items]
        inv_dict["payments"] = [dict(p) for p in inv_payments]
        invoice_details.append(inv_dict)
    
    # Customer info
    customer = execute_readonly(
        "SELECT * FROM customers WHERE id = ?", (order["customer_id"],)
    )
    
    # Determine broken steps
    broken_steps = []
    if not deliveries:
        broken_steps.append({"step": "DELIVERY", "reason": "NO_DELIVERY", "message": "No delivery record found for this order"})
    if not invoices:
        broken_steps.append({"step": "INVOICE", "reason": "NO_INVOICE", "message": "No invoice found for this order"})
    if deliveries and not invoices:
        broken_steps.append({"step": "BILLING", "reason": "DELIVERED_NOT_BILLED", "message": "Order delivered but not invoiced"})
    if invoices and not deliveries:
        broken_steps.append({"step": "SHIPPING", "reason": "BILLED_NOT_DELIVERED", "message": "Order invoiced but not delivered"})
    
    for inv in invoice_details:
        if not inv["payments"]:
            broken_steps.append({
                "step": "PAYMENT", 
                "reason": "PAYMENT_MISSING",
                "message": f"No payment found for invoice {inv['id']}"
            })
    
    # Build all node IDs in this flow
    flow_nodes = [order_id]
    flow_nodes.extend([i["id"] for i in items])
    flow_nodes.extend([d["id"] for d in deliveries])
    flow_nodes.extend([inv["id"] for inv in invoices])
    for inv in invoice_details:
        flow_nodes.extend([p["id"] for p in inv["payments"]])
    if customer:
        flow_nodes.append(customer[0]["id"])
    
    return {
        "order_id": order_id,
        "order": order,
        "customer": dict(customer[0]) if customer else None,
        "items": [dict(i) for i in items],
        "deliveries": [dict(d) for d in deliveries],
        "invoices": invoice_details,
        "broken_steps": broken_steps,
        "is_complete": len(broken_steps) == 0,
        "flow_node_ids": flow_nodes
    }


@router.get("/broken-flows")
async def get_broken_flows():
    """Return all orders with incomplete chains and reason codes."""
    broken = detect_broken_flows()
    return {
        "total_broken": len(broken),
        "flows": broken
    }
