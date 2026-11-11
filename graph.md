# PayPilot — build graph (PayPal AI Hackathon, deadline Fri 13 Nov 2026 01:30 IST)

## Goal
Working AI shopping agent: browses a demo store, picks products, completes PayPal sandbox checkout (Orders v2), explains every decision. Public OSS repo, hosted demo, <3min YouTube video, Devpost submission 1296315 (draft).

## Nodes
N1 paypal-sandbox-app: Fo-owned developer.paypal.com account + sandbox app (client id/secret). -> N2
N2 backend-agent: agent loop (tool-use LLM via Dahl minimax-m2.7 free endpoint; fallback Clocked 20k credits) with tools: search products, add to cart, create PayPal order, approve+capture. -> N3
N3 frontend: demo store + live agent console showing reasoning + payment status. -> N4
N4 deploy: Render free web service (sponsor prize) + verify end-to-end sandbox checkout. -> N5
N5 docs+repo: github public repo (Fo-builds), README with run instructions, MIT license at top. -> N6
N6 video: scripted browser run captured to screenshots -> ffmpeg mp4 <3min -> YouTube upload via Fo Google account -> link into Devpost. -> N7
N7 devpost-fill: About the project, Built with tags, links, video URL, additional info, submit.

## Checks
C1 sandbox order created + captured in sandbox (evidence: order id JSON).
C2 agent completes full flow unaided from a single goal prompt (evidence: transcript).
C3 hosted demo reachable + checkout works there (evidence: URL + screenshot).
C4 repo public, license visible (evidence: repo URL).
C5 video <3min, public/unlisted YouTube (evidence: link).

## Deadlines
Fri 13 Nov 01:30 IST submit. Backstop: aim complete by Thu 12 Nov 18:00 IST.
