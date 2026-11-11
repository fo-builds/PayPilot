// PayPilot server: demo store + agent console.
const path = require('path');
const express = require('express');
const { runAgent } = require('./lib/agent');
const { CATALOG } = require('./lib/catalog');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/catalog', (req, res) => res.json(CATALOG));

app.post('/api/agent/run', async (req, res) => {
  const { message, history } = req.body || {};
  if (!message) return res.status(400).json({ error: 'message required' });
  try {
    const steps = [];
    const out = await runAgent({
      userMessage: message,
      history: Array.isArray(history) ? history.slice(-8) : [],
      onStep: (s) => steps.push(s)
    });
    res.json(out);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: String(err.message || err), steps: [] });
  }
});

app.get('/health', (req, res) => res.json({ ok: true }));

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`PayPilot running on :${port}`));
