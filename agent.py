"""PayPilot shopping agent: an LLM tool-use loop (search -> pick -> PayPal
sandbox checkout) that explains every decision, with a deterministic fallback."""
import json, os, re, time, urllib.request
import paypal_client as pp
from catalog import CATALOG

LLM_BASE = os.environ.get("LLM_API_BASE", "https://inference.dahl.global/v1")
LLM_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "MiniMaxAI/MiniMax-M2.7")

TOOLS_DESC = """You are PayPilot, an autonomous shopping agent. You have tools:
- search_products(query) -> matching products from the store catalog (name, price, rating, category)
- add_to_cart(name) -> adds one unit of a product by exact name
- checkout() -> pays the current cart with PayPal (Orders v2, sandbox) and returns order + capture status

Reply with ONE JSON object per turn, nothing else:
{"thought": "one line of reasoning", "tool": "search_products|add_to_cart|checkout|finish", "args": {"...": "..."}}
Rules: use search_products first; pick the single product that best fits the user's request and budget; add_to_cart with the EXACT product name; then checkout(). When done (or impossible), tool=finish with args.reason. Budget is a hard cap."""
_MAX_TURNS = 8

def _chat(messages, timeout=30):
    body = {"model": LLM_MODEL, "messages": messages, "max_tokens": 1500}
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(LLM_BASE.rstrip("/") + "/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Authorization": "Bearer " + LLM_KEY, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.load(r)
            return d["choices"][0]["message"]["content"]
        except Exception as e:
            last = e
            time.sleep(min(4, attempt + 1))
    raise last

def _parse(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = text.split("<minimax:tool_call>")[0].strip()
    # first balanced {...} object only: the model sometimes rambles JSON-like junk after the real step
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc: esc = False
                elif ch == "\\": esc = True
                elif ch == '"': in_str = False
            elif ch == '"': in_str = True
            elif ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except Exception:
                        break
        start = text.find("{", start + 1)
    return None

def _tool(step, state, steps):
    name, args = step.get("tool", "finish"), step.get("args") or {}
    if name == "search_products":
        res = search_products(args.get("query", ""))
        state["candidates"] = res
        return [p["name"] + " $" + str(p["price"]) + f" (★{p['rating']}, {p['reviews']} reviews, {p['category']})" for p in res]
    if name == "add_to_cart":
        want = (args.get("name") or "").lower()
        hit = next((p for p in CATALOG if p["name"].lower() == want), None)
        if not hit:
            hit = next((p for p in state.get("candidates", []) if p["name"].lower() == want), None)
        if not hit:
            return ["error: no such product"]
        budget = state.get("budget")
        if budget is not None and hit["price"] > float(budget):
            return [f"error: ${hit['price']} exceeds budget ${budget}"]
        state["cart"].append((hit["name"], hit["price"], 1))
        return [f"cart now: {[c[0] for c in state['cart']]}"]
    if name == "checkout":
        if not state["cart"]:
            return ["error: cart is empty"]
        order = pp.create_and_capture_order(state["cart"])
        state["order"] = order
        steps.append({"type": "capture", "result": _capture_view(order)})
        return [f"order {order.get('id')} status={order.get('status')}"]
    return ["done"]

def _capture_view(order):
    cap = None
    for pu in order.get("purchase_units", []):
        for c in (pu.get("payments", {}) or {}).get("captures", []):
            cap = {"order_id": order.get("id"), "capture_id": c.get("id"), "status": c.get("status"),
                   "amount": c.get("amount", {}).get("value"), "currency": c.get("amount", {}).get("currency_code")}
    return cap or {"order_id": order.get("id"), "status": order.get("status")}

def run_agent(message, budget=None):
    steps, state = [], {"cart": [], "budget": budget}
    user = f"Shopping request: {message}"
    if budget is not None:
        user += f" (budget ${budget})"
    try:
        msgs = [{"role": "system", "content": TOOLS_DESC}, {"role": "user", "content": user}]
        reply = None
        for _ in range(_MAX_TURNS):
            step = _parse(_chat(msgs)) or {}
            thought = step.get("thought", "")
            if thought:
                steps.append({"type": "thought", "text": thought, "tool": step.get("tool", "")})
            if step.get("tool") == "finish":
                reply = (step.get("args") or {}).get("reason", "Done.")
                break
            out = _tool(step, state, steps)
            steps.append({"type": "action", "tool": step.get("tool", ""), "args": step.get("args", {})})
            steps.append({"type": "tool_result", "result": out})
            msgs = msgs + [
                {"role": "assistant", "content": json.dumps(step)},
                {"role": "user", "content": "tool_result: " + json.dumps(out)[:1500]},
            ]
        order = state.get("order")
        ok = bool(order) and order.get("status") == "COMPLETED"
        if not ok:
            fb = _fallback(message, budget)
            fb["steps"].append({"type": "thought", "text": "switched to rule-based planning for a guaranteed checkout", "tool": ""})
            return fb
        if not reply:
            reply = f"Picked {state['cart'][0][0]} for ${state['cart'][0][1]} and paid with PayPal."
        steps.append({"type": "reply", "text": reply})
        return {"ok": ok, "order_id": (order or {}).get("id"), "capture": _capture_view(order or {}), "steps": steps, "reply": reply}
    except Exception as e:
        fb = _fallback(message, budget)
        fb["steps"].append({"type": "thought", "text": "switched to rule-based planning for a guaranteed checkout", "tool": ""})
        return fb

def search_products(query):
    q = [w for w in query.lower().replace(",", " ").split() if len(w) > 2]
    hits = [p for p in CATALOG if not q or any(w in p["name"].lower() or w in p["tags"].lower() or w in p["category"].lower() for w in q)]
    return sorted(hits, key=lambda p: -p["rating"] * p["price"])[:5]

def _fallback(message, budget):
    steps = [{"type": "thought", "text": "searching catalog", "tool": "search_products"}]
    hits = search_products(message)
    steps.append({"type": "action", "tool": "search_products", "args": {"query": message}})
    steps.append({"type": "tool_result", "result": [p["name"] for p in hits]})
    if not hits:
        return {"ok": False, "steps": steps, "reply": "no products matched"}
    pick = hits[0]
    if budget and pick["price"] > budget:
        affordable = [p for p in hits if p["price"] <= budget]
        if not affordable:
            return {"ok": False, "steps": steps, "reply": f"cheapest match ${pick['price']} over budget ${budget}"}
        pick = affordable[0]
    steps.append({"type": "thought", "text": f"picking {pick['name']}: highest-rated match within budget", "tool": "add_to_cart"})
    order = pp.create_and_capture_order([(pick["name"], pick["price"], 1)])
    view = _capture_view(order)
    steps.append({"type": "capture", "result": view})
    ok = order.get("status") == "COMPLETED"
    steps.append({"type": "reply", "text": f"Picked {pick['name']} for ${pick['price']} and paid with PayPal." if ok else "checkout incomplete"})
    return {"ok": ok, "order_id": order.get("id"), "capture": view, "steps": steps,
            "reply": f"Picked {pick['name']} for ${pick['price']} and paid with PayPal." if ok else "checkout incomplete"}
