"""PayPal Orders v2 client (sandbox). Token cached; card payment source for
autonomous checkout: order create + capture completes in one call."""
import base64, json, os, time, urllib.request, uuid

API = "https://api-m.sandbox.paypal.com"
CID = os.environ["PAYPAL_CLIENT_ID"]
SECRET = os.environ["PAYPAL_CLIENT_SECRET"]
_tok, _tok_exp = None, 0.0

def token():
    global _tok, _tok_exp
    if _tok and time.time() < _tok_exp - 60:
        return _tok
    cred = base64.b64encode(f"{CID}:{SECRET}".encode()).decode()
    req = urllib.request.Request(
        API + "/v1/oauth2/token", method="POST",
        data=b"grant_type=client_credentials",
        headers={"Authorization": "Basic " + cred,
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    _tok, _tok_exp = d["access_token"], time.time() + d.get("expires_in", 32400)
    return _tok

def _call(method, path, body=None, request_id=None):
    headers = {"Authorization": "Bearer " + token(),
               "Content-Type": "application/json"}
    if request_id:
        headers["PayPal-Request-Id"] = request_id
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)

TEST_CARD = {"number": "4111111111111111", "expiry": "2030-12", "cvv2": "123",
             "name": "John DoeskipKYC",
             "billing_address": {"address_line_1": "1 Main St",
                                 "admin_area_2": "Liverpool",
                                 "postal_code": "L1 0AB", "country_code": "GB"}}

def create_and_capture_order(items, brand="PayPilot Demo Store"):
    """items: list of (name, unit_price, quantity). Returns the completed order."""
    total = round(sum(p * q for _, p, q in items), 2)
    rid = "pp-" + uuid.uuid4().hex
    body = {
        "intent": "CAPTURE",
        "payment_source": {"card": dict(TEST_CARD)},
        "purchase_units": [{
            "amount": {"currency_code": "USD", "value": f"{total:.2f}",
                       "breakdown": {"item_total": {"currency_code": "USD",
                                                    "value": f"{total:.2f}"}}},
            "description": "PayPilot agent order",
            "items": [{"name": n, "unit_amount": {"currency_code": "USD",
                       "value": f"{p:.2f}"}, "quantity": str(q)} for n, p, q in items],
        }],
        "application_context": {"brand_name": brand, "user_action": "PAY_NOW"},
    }
    order = _call("POST", "/v2/checkout/orders", body, request_id=rid)
    order["_request_id"] = rid
    return order

def get_order(oid):
    return _call("GET", "/v2/checkout/orders/" + oid)
