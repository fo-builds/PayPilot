---
title: PayPilot
emoji: 🛒
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# PayPilot

AI shopping agent that browses a demo store, picks the product, and completes a real PayPal **sandbox** checkout end to end with zero clicks. Built for the PayPal AI Hackathon (Devpost submission 1296315).

- `/` — demo store + live agent console
- `POST /api/agent/run` — `{"query": "mechanical keyboard", "budget": 25}`
- `GET /health`

Set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` as Space secrets (sandbox only).
