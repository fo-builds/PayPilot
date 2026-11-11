// PayPal Orders v2 client (sandbox by default). Zero deps beyond fetch (Node 18+).
const BASE = process.env.PAYPAL_API_BASE || 'https://api-m.sandbox.paypal.com';
const CID = process.env.PAYPAL_CLIENT_ID;
const SECRET = process.env.PAYPAL_CLIENT_SECRET;

let tokenCache = null; // { token, expiresAt }

async function getToken() {
  if (tokenCache && Date.now() < tokenCache.expiresAt - 60000) return tokenCache.token;
  const res = await fetch(`${BASE}/v1/oauth2/token`, {
    method: 'POST',
    headers: {
      Authorization: 'Basic ' + Buffer.from(`${CID}:${SECRET}`).toString('base64'),
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: 'grant_type=client_credentials'
  });
  if (!res.ok) throw new Error(`paypal oauth failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  tokenCache = { token: data.access_token, expiresAt: Date.now() + data.expires_in * 1000 };
  return tokenCache.token;
}

async function pp(method, path, body) {
  const token = await getToken();
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { json = { raw: text }; }
  return { status: res.status, ok: res.ok, json };
}

// Create an order. items: [{name, unit_amount, quantity, description?}]
async function createOrder({ items, currency = 'USD', brand = 'PayPilot Demo Store', reference = undefined }) {
  const total = items.reduce((s, i) => s + Number(i.unit_amount) * Number(i.quantity), 0).toFixed(2);
  const body = {
    intent: 'CAPTURE',
    purchase_units: [{
      reference_id: reference || 'paypilot-' + Date.now(),
      description: `${brand} - AI agent checkout`,
      amount: { currency_code: currency, value: total, breakdown: { item_total: { currency_code: currency, value: total } } },
      items: items.map(i => ({
        name: i.name,
        description: (i.description || '').slice(0, 127),
        unit_amount: { currency_code: currency, value: Number(i.unit_amount).toFixed(2) },
        quantity: String(i.quantity),
        category: 'PHYSICAL_GOODS'
      }))
    }],
    payment_source: {
      paypal: {
        experience_context: {
          brand_name: brand,
          user_action: 'PAY_NOW',
          shipping_preference: 'NO_SHIPPING'
        }
      }
    }
  };
  return pp('POST', '/v2/checkout/orders', body);
}

async function getOrder(id) { return pp('GET', `/v2/checkout/orders/${id}`); }

// Attempt capture. In sandbox, an order created without buyer approval returns
// ORDER_NOT_APPROVED; e2e.js shows the programmatic-approval path for demos.
async function captureOrder(id) { return pp('POST', `/v2/checkout/orders/${id}/capture`, {}); }

module.exports = { createOrder, getOrder, captureOrder, getToken, pp, BASE };
