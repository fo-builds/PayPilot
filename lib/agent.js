// PayPilot agent: LLM-driven shopping agent loop (OpenAI-compatible tool calling).
// Rails: any OpenAI-compatible endpoint (Dahl / MiniMax M2.7 by default).
const { CATALOG } = require('./catalog');
const paypal = require('./paypal');

const SYSTEM_PROMPT = `You are PayPilot, an autonomous shopping agent. You help a shopper find the right product in a small demo catalog and then complete the purchase end to end using PayPal's sandbox REST APIs. Rules:
1. Call search_products to browse the catalog when you need options.
2. Pick the product that best fits the shopper's request and budget; say why in one sentence.
3. Call create_order with your pick. If it succeeds, report the order id and status in plain English. Do not fabricate order ids - use only values returned by tools.
4. Every message you send the shopper is one short paragraph of plain English. Explain what you did and why, like a helpful store clerk who happens to be software.
5. Never invent prices. Prices come from search_products only.`;

const TOOLS = [
  {
    type: 'function',
    function: {
      name: 'search_products',
      description: 'Search the demo store catalog. Optional filters: category, max_price, min_rating, keyword.',
      parameters: {
        type: 'object',
        properties: {
          keyword: { type: 'string' },
          category: { type: 'string', enum: ['Audio', 'Desk', 'Accessories'] },
          max_price: { type: 'number' },
          min_rating: { type: 'number' }
        }
      }
    }
  },
  {
    type: 'function',
    function: {
      name: 'create_order',
      description: 'Create (and, in sandbox, complete) a PayPal order for the chosen product.',
      parameters: {
        type: 'object',
        properties: {
          product_id: { type: 'string', description: 'id from search_products' },
          quantity: { type: 'integer', default: 1 }
        },
        required: ['product_id']
      }
    }
  }
];

function searchProducts(args) {
  let rows = CATALOG.slice();
  if (args.keyword) {
    const k = String(args.keyword).toLowerCase();
    rows = rows.filter(p => (p.name + ' ' + p.description + ' ' + p.category).toLowerCase().includes(k));
  }
  if (args.category) rows = rows.filter(p => p.category === args.category);
  if (args.max_price != null) rows = rows.filter(p => p.price <= args.max_price);
  if (args.min_rating != null) rows = rows.filter(p => p.rating >= args.min_rating);
  return rows;
}

async function createOrderTool(args) {
  const product = CATALOG.find(p => p.id === args.product_id);
  if (!product) return { error: `no product with id ${args.product_id}` };
  const qty = args.quantity || 1;
  const res = await paypal.createOrder({
    items: [{ name: product.name, description: product.description, unit_amount: product.price, quantity: qty }]
  });
  if (!res.ok) return { error: 'paypal create_order failed', status: res.status, detail: res.json };
  const order = res.json;
  return {
    order_id: order.id,
    status: order.status,
    amount: order.purchase_units?.[0]?.amount?.value,
    currency: order.purchase_units?.[0]?.amount?.currency_code,
    product: product.name,
    next: 'capture (auto-approved in sandbox by the agent) runs next'
  };
}

async function captureOrderTool(orderId) {
  const res = await paypal.captureOrder(orderId);
  if (!res.ok) {
    return { error: 'capture failed', status: res.status, detail: res.json };
  }
  const cap = res.json;
  const pu = cap.purchase_units?.[0];
  return {
    order_id: cap.id,
    status: cap.status,
    capture_id: pu?.payments?.captures?.[0]?.id,
    amount: pu?.payments?.captures?.[0]?.amount?.value,
    currency: pu?.payments?.captures?.[0]?.amount?.currency_code,
    payer_email: cap.payer?.email_address
  };
}

async function runAgent({ userMessage, history = [], onStep }) {
  const base = process.env.LLM_API_BASE;
  const key = process.env.LLM_API_KEY;
  const model = process.env.LLM_MODEL || 'MiniMaxAI/MiniMax-M2.7';
  const messages = [
    { role: 'system', content: SYSTEM_PROMPT },
    ...history,
    { role: 'user', content: userMessage }
  ];
  const steps = [];
  const log = (step) => { steps.push(step); if (onStep) onStep(step); };

  for (let i = 0; i < 6; i++) {
    const res = await fetch(`${base}/chat/completions`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, messages, tools: TOOLS, tool_choice: 'auto', temperature: 0.3 })
    });
    if (!res.ok) throw new Error(`llm call failed: ${res.status} ${await res.text()}`);
    const data = await res.json();
    const msg = data.choices?.[0]?.message;
    if (!msg) throw new Error('empty llm response');
    messages.push(msg);

    if (msg.tool_calls && msg.tool_calls.length) {
      for (const call of msg.tool_calls) {
        const fn = call.function.name;
        let args = {};
        try { args = JSON.parse(call.function.arguments || '{}'); } catch { args = {}; }
        let result;
        if (fn === 'search_products') {
          log({ type: 'thought', text: msg.content || '', tool: fn, args });
          result = searchProducts(args);
          log({ type: 'tool_result', tool: fn, result });
        } else if (fn === 'create_order') {
          log({ type: 'action', text: msg.content || '', tool: fn, args });
          result = await createOrderTool(args);
          log({ type: 'tool_result', tool: fn, result });
        } else {
          result = { error: `unknown tool ${fn}` };
        }
        messages.push({ role: 'tool', tool_call_id: call.id, content: JSON.stringify(result) });
      }
      continue;
    }

    // final assistant message
    log({ type: 'reply', text: msg.content });
    // if the last tool result contains an order id, capture it automatically
    const lastOrder = [...steps].reverse().find(s => s.type === 'tool_result' && s.tool === 'create_order' && s.result && s.result.order_id);
    let capture = null;
    if (lastOrder) {
      capture = await captureOrderTool(lastOrder.result.order_id);
      log({ type: 'capture', result: capture });
    }
    return { reply: msg.content, steps, capture };
  }
  return { reply: 'I hit my step limit before finishing. Please retry.', steps, capture: null };
}

module.exports = { runAgent, searchProducts, createOrderTool, captureOrderTool };
