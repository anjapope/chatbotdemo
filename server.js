// server.js — minimal mock chat backend
const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// Simple health/ping via OPTIONS (frontend uses OPTIONS to 'ping')
app.options('/chat', (req, res) => {
  res.sendStatus(200);
});

// POST /chat — expects the same contract the frontend sends
app.post('/chat', (req, res) => {
  const { messages } = req.body || {};

  // Find the last user message
  let lastUser = null;
  if (Array.isArray(messages)) {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i] && messages[i].role === 'user') {
        lastUser = messages[i].content;
        break;
      }
    }
  }

  const userText = lastUser || '(no user message)';

  // Very naive mock reply — replace with real LLM proxying in production
  const reply = `Mock reply — you said: ${userText}`;

  // Respond with JSON (non-streaming)
  res.json({ reply });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Mock backend running on http://localhost:${PORT}/`));
