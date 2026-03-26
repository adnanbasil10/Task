"""
Data validator: checks referential integrity and detects broken business flows.
"""
from db import execute_readonly


def validate_referential_integrity() -> dict:
    """Check all FK relationships for orphan records."""
    issues = {}
    
    checks = [
        ("orders → customers", 
         "SELECT o.id FROM orders o LEFT JOIN customers c ON o.customer_id = c.id WHERE c.id IS NULL"),
        ("order_items → orders",
         "SELECT oi.id FROM order_items oi LEFT JOIN orders o ON oi.order_id = o.id WHERE o.id IS NULL"),
        ("order_items → products",
         "SELECT oi.id FROM order_items oi LEFT JOIN products p ON oi.product_id = p.id WHERE p.id IS NULL"),
        ("deliveries → orders",
         "SELECT d.id FROM deliveries d LEFT JOIN orders o ON d.order_id = o.id WHERE o.id IS NULL"),
        ("deliveries → addresses",
         "SELECT d.id FROM deliveries d LEFT JOIN addresses a ON d.address_id = a.id WHERE a.id IS NULL"),
        ("invoices → orders",
         "SELECT i.id FROM invoices i LEFT JOIN orders o ON i.order_id = o.id WHERE o.id IS NULL"),
        ("invoice_items → invoices",
         "SELECT ii.id FROM invoice_items ii LEFT JOIN invoices i ON ii.invoice_id = i.id WHERE i.id IS NULL"),
        ("payments → invoices",
         "SELECT p.id FROM payments p LEFT JOIN invoices i ON p.invoice_id = i.id WHERE i.id IS NULL"),
    ]
    
    for label, sql in checks:
        orphans = execute_readonly(sql)
        if orphans:
            issues[label] = [r["id"] for r in orphans]
    
    return issues


def detect_broken_flows() -> list[dict]:
    """
    Detect orders with incomplete supply chain flows.
    Returns list of {order_id, reasons: [reason_code, ...]}
    """
    broken = []
    
    # Get all orders
    orders = execute_readonly("SELECT id FROM orders")
    
    for order in orders:
        oid = order["id"]
        reasons = []
        
        # Check delivery
        deliveries = execute_readonly(
            "SELECT id FROM deliveries WHERE order_id = ?", (oid,)
        )
        has_delivery = len(deliveries) > 0
        
        # Check invoice
        invoices_result = execute_readonly(
            "SELECT id FROM invoices WHERE order_id = ?", (oid,)
        )
        has_invoice = len(invoices_result) > 0
        
        # Check payment (via invoices)
        if has_invoice:
            invoice_ids = [inv["id"] for inv in invoices_result]
            placeholders = ",".join(["?"] * len(invoice_ids))
            payments = execute_readonly(
                f"SELECT id FROM payments WHERE invoice_id IN ({placeholders})",
                tuple(invoice_ids)
            )
            has_payment = len(payments) > 0
        else:
            has_payment = False
        
        # Determine broken flow reasons
        if has_delivery and not has_invoice:
            reasons.append("DELIVERED_NOT_BILLED")
        if has_invoice and not has_delivery:
            reasons.append("BILLED_NOT_DELIVERED")
        if not has_delivery:
            reasons.append("NO_DELIVERY")
        if not has_invoice:
            reasons.append("NO_INVOICE")
        if has_invoice and not has_payment:
            reasons.append("PAYMENT_MISSING")
        
        if reasons:
            broken.append({
                "order_id": oid,
                "has_delivery": has_delivery,
                "has_invoice": has_invoice,
                "has_payment": has_payment,
                "reasons": reasons
            })
    
    return broken


def get_validation_summary() -> dict:
    """Get complete validation summary."""
    from db import get_all_table_counts
    
    table_counts = get_all_table_counts()
    ref_issues = validate_referential_integrity()
    broken_flows = detect_broken_flows()
    
    # Count total nodes (entities that become graph nodes)
    total_nodes = sum(table_counts.get(t, 0) for t in 
                      ["customers", "products", "orders", "deliveries", "invoices", "payments"])
    
    summary = {
        "table_counts": table_counts,
        "total_nodes": total_nodes,
        "referential_issues": ref_issues,
        "broken_flows_count": len(broken_flows),
        "broken_flows": broken_flows,
        "reason_summary": {}
    }
    
    # Summarize reasons
    for flow in broken_flows:
        for reason in flow["reasons"]:
            summary["reason_summary"][reason] = summary["reason_summary"].get(reason, 0) + 1
    
    return summary


def print_validation_report(summary: dict):
    """Print a formatted validation report."""
    print("\n" + "=" * 60)
    print("📊 DATA VALIDATION REPORT")
    print("=" * 60)
    
    print("\n📋 Table Counts:")
    for table, count in summary["table_counts"].items():
        print(f"   {table:20s}: {count:>6d}")
    
    print(f"\n🔗 Total Graph Nodes: {summary['total_nodes']}")
    
    if summary["referential_issues"]:
        print("\n⚠️  Referential Integrity Issues:")
        for rel, ids in summary["referential_issues"].items():
            print(f"   {rel}: {len(ids)} orphan(s) → {ids[:5]}{'...' if len(ids)>5 else ''}")
    else:
        print("\n✅ No referential integrity issues found.")
    
    print(f"\n🔴 Broken Flows: {summary['broken_flows_count']} orders")
    if summary["reason_summary"]:
        print("   Reason breakdown:")
        for reason, count in summary["reason_summary"].items():
            print(f"     {reason:30s}: {count}")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    summary = get_validation_summary()
    print_validation_report(summary)
