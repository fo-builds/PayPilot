// End-to-end sandbox check: OAuth -> order create -> capture attempts.
// Usage: node scripts/e2e.js   (env: PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, [PAYPAL_BUYER_EMAIL], [PAYPAL_PAYER_ID])
const paypal = require('../lib/paypal');
const { CATALOG } = require('../lib/catalog');

(async () => {
  const product = CATALOG[0]; // Pulse Wireless Earbuds, $49.99
  console.log('== PayPal sandbox rails check ==');

  // 1. OAuth
  const token = await paypal.getToken();
  console.log('[1] OAuth OK, token prefix:', token.slice(0, 12) + '...');

  // 2. v2 order, plain
  const ord = await paypal.createOrder({ items: [{ name: product.name, description: product.description, unit_amount: product.price, quantity: 1 }] });
  console.log('[2] create_order v2:', ord.status, JSON.stringify({ id: ord.json.id, status: ord.json.status, total: ord.json.purchase_units?.[0]?.amount?.value }));

  // 3. capture attempt (no approval)
  const cap = await paypal.captureOrder(ord.json.id);
  console.log('[3] capture (no approval):', cap.status, JSON.stringify(cap.json).slice(0, 400));

  // 4. v2 order with buyer email in payment_source
  const buyer = process.env.PAYPAL_BUYER_EMAIL;
  if (buyer) {
    const body = {
      intent: 'CAPTURE',
      purchase_units: [{
        amount: { currency_code: 'USD', value: product.price.toFixed(2) },
        items: [{ name: product.name, unit_amount: { currency_code: 'USD', value: product.price.toFixed(2) }, quantity: '1', category: 'PHYSICAL_GOODS' }]
      }],
      payment_source: { paypal: { email_address: buyer, experience_context: { user_action: 'PAY_NOW', shipping_preference: 'NO_SHIPPING' } } }
    };
    const ord2 = await paypal.pp('POST', '/v2/checkout/orders', body);
    console.log('[4] create with buyer email:', ord2.status, JSON.stringify({ id: ord2.json.id, status: ord2.json.status }).slice(0, 300));
    if (ord2.ok) {
      const cap2 = await paypal.captureOrder(ord2.json.id);
      console.log('[5] capture (buyer email):', cap2.status, JSON.stringify(cap2.json).slice(0, 600));
    }
  } else {
    console.log('[4] skipped (no PAYPAL_BUYER_EMAIL set)');
  }

  // 5. legacy v1 payments create + execute path
  const payerId = process.env.PAYPAL_PAYER_ID;
  if (payerId) {
    const v1 = await paypal.pp('POST', '/v1/payments/payment', {
      intent: 'sale',
      payer: { payment_method: 'paypal' },
      transactions: [{ amount: { total: product.price.toFixed(2), currency: 'USD' }, description: 'PayPilot agent checkout' }],
      redirect_urls: { return_url: 'https://example.com/return', cancel_url: 'https://example.com/cancel' }
    });
    console.log('[6] v1 create:', v1.status, v1.json.id || JSON.stringify(v1.json).slice(0, 300));
    if (v1.ok) {
      const exec = await paypal.pp('POST', `/v1/payments/payment/${v1.json.id}/execute`, { payer_id: payerId });
      console.log('[7] v1 execute:', exec.status, JSON.stringify(exec.json).slice(0, 600));
    }
  } else {
    console.log('[6] skipped (no PAYPAL_PAYER_ID set)');
  }
})().catch(e => { console.error('E2E FAILED:', e.message); process.exit(1); });
