# Checks
C1: capture a real sandbox order JSON (create + capture) with order id — resolved only by file evidence in runs/.
C2: one agent transcript that goes goal -> cart -> order -> capture with no human step.
C3: deployed URL responds 200 and a sandbox checkout completes on it (screenshot).
C4: repo URL returns public page with LICENSE in About section.
C5: video file duration < 180s, YouTube link live.

## 2026-11-12 02:20 IST — N2 LLM agent loop FIXED, e2e verified
Root causes of the LLM-loop failures (MiniMax-M2.7 via dahl):
1. max_tokens 700: the model burns the budget on its `<think>` block, `finish_reason=length`, no JSON emitted. Raised to 1500 in `_chat` (agent.py:22).
2. stop=["</think>"]: output truncated exactly at the closing think tag, dropping the JSON that followed. stop removed entirely (the `_parse` tail-stripper handles think tags).

Post-fix evidence (agent.py unmodified otherwise, rule fallback untouched):
- "get me something to keep my cables tidy on my desk, cheap" budget $15 → LLM-driven full loop: search_products → add_to_cart(Cable Organizer 6-pack) → checkout → COMPLETED. order 25Y09989GB822232N, $9.99, LLM-authored finish reply.
- "keep my desk cables tidy, cheap" budget $15 → ok=True, order 63178779JA666470C, capture 7XT56158836961228, status COMPLETED, USD 9.99. Reply authored by LLM: "Order ... completed. Purchased Cable Organizer 6-pack for $9.99..."
- Miss behavior stays graceful: "order me a notebook under 10 dollars" → search empty → falls back, returns "no products matched" instead of inventing.
- No fallback marker in successful runs; the earlier "paypal client not configured" error did not recur with .env sourced (PAYPAL_CLIENT_ID/PAYPAL_CLIENT_SECRET present; paypal_client reads both).

N2 status: done. Next node: N5 repo push (this run), then N3 frontend polish, N6 video, N7 devpost.
