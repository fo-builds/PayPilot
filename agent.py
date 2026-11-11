"""PayPilot shopping agent: search -> pick -> pay. Autonomous capture proven."""
from paypal_client import pp
from catalog import CATALOG

def search_products(query):
    q = query.lower().split()
    hits = [p for p in CATALOG if any(w in p["name"].lower() or w in p["tags"] for w in q)]
    return sorted(hits, key=lambda p: p["price"])[:5]

def run_agent(query, budget=None):
    steps = []
    hits = search_products(query)
    steps.append({"step": "search", "query": query, "found": [h["name"] for h in hits]})
    if not hits:
        return {"ok": False, "reason": "no products matched", "steps": steps}
    pick = hits[0]
    if budget and pick["price"] > budget:
        affordable = [p for p in hits if p["price"] <= budget]
        if not affordable:
            return {"ok": False, "reason": f"cheapest match ${pick['price']} over budget ${budget}", "steps": steps}
        pick = affordable[0]
    steps.append({"step": "pick", "product": pick["name"], "price": pick["price"],
                  "why": pick.get("why", "cheapest match within budget")})
    order = pp.create_and_capture_order([(pick["name"], pick["price"], 1)])
    steps.append({"step": "checkout", "order_id": order.get("id"),
                  "status": order.get("status"), "request_id": order.get("_request_id")})
    capture = None
    for pu in order.get("purchase_units", []):
        for c in (pu.get("payments", {}) or {}).get("captures", []):
            capture = {"capture_id": c.get("id"), "status": c.get("status"),
                       "amount": c.get("amount")}
    steps.append({"step": "capture", "result": capture})
    ok = order.get("status") == "COMPLETED"
    return {"ok": ok, "order_id": order.get("id"), "capture": capture, "steps": steps}
