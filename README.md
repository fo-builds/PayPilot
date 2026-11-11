# PayPilot 🛩️

**An AI shopping agent that completes real PayPal checkouts on its own.**

PayPilot is a shopping agent for the PayPal AI Hackathon. You tell it what you need and your budget; it searches the catalog, picks what fits, and pays with PayPal's Orders API — end to end, no clicks, no forms, no human in the middle of the payment.

## How it works

```
you: "get me a mechanical keyboard under $50"
        │
        ▼
  ┌─────────────┐    search_products   ┌─────────────┐
  │ PayPilot    │ ───────────────────▶ │  catalog    │
  │  agent      │ ◀─────────────────── │  (8 items)  │
  └─────┬───────┘                      └─────────────┘
        │ pick cheapest within budget
        ▼
  ┌─────────────────────────────────────────────────────┐
  │ PayPal Orders v2 (sandbox)                          │
  │  POST /v2/checkout/orders  intent=CAPTURE           │
  │  payment_source: card  +  PayPal-Request-Id         │
  │  → status COMPLETED, capture COMPLETED in one call  │
  └─────────────────────────────────────────────────────┘
        │
        ▼
  receipt: order id + capture id + amount, shown live in the UI
```

The load-bearing trick: PayPal Checkout normally ends in an approval redirect
(the buyer must approve). That's the right model for a human checkout, but it
breaks an *agent* checkout. PayPilot uses PayPal's direct card payment source
(Advanced Card Processing) inside Orders v2, so the agent itself completes the
payment autonomously: order created and captured in a single API call, with
`PayPal-Request-Id` idempotency keys so a retry can never double-charge.

## Why it matters

Agentic commerce needs a payment rail that doesn't assume a human at the end
of the funnel. PayPilot demonstrates the full loop — intent → search → pick →
pay → receipt — on real PayPal rails (sandbox), with an auditable trail
(order id, capture id, request id) for every step.

## Run it

```bash
export PAYPAL_CLIENT_ID=...   # sandbox app
export PAYPAL_CLIENT_SECRET=...
python3 server.py         # http://localhost:8080
python3 e2e_agent.py          # full agent loop end to end
```

No dependencies beyond Python 3 stdlib.

## API

| Endpoint | What it does |
|---|---|
| `GET /api/catalog` | the demo store's catalog |
| `POST /api/agent/run` | `{query, budget?}` → agent search/pick/checkout with step-by-step trace |
| `GET /health` | health check |

## Built with

- PayPal Orders v2 REST API (sandbox), direct card payment source
- Python 3 stdlib (no frameworks)
- vanilla JS frontend

## Test results (sandbox)

| run | order | capture | status |
|---|---|---|---|
| e2e #1 | 38L97150Y04628210 | 1PB69050FU1129243 | COMPLETED $18.75 |
| e2e #2 | 2V3973273D0236947 | 4N025144YK078134F | COMPLETED $18.75 |
| HTTP e2e | 694501765J988533B | 10J30424SD164531C | COMPLETED $18.75 |
