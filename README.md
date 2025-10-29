# chatbotdemo

Small demo: a static frontend and a minimal Python stdlib backend for local testing and simple deployments.

## Quick start (local)

1. Create a `.env` file in the project root with your OpenAI API key (do NOT commit this file to Git):

```text
OPENAI_API_KEY=sk-... (your key)
OPENAI_MODEL=gpt-4o
ADMIN_TOKEN=secret-token
RERANK_N=5
```

2. Install Python 3 (3.8+ recommended). This project uses only the Python standard library; a `requirements.txt` is provided for future packages.

3. Start the backend:

```bash
python3 server_py.py
```

The backend listens on port 3000 by default.

4. Open the static frontend files (e.g. `index.html`, `chat.html`) in your browser or serve the folder with a static server.

## Notes

- This backend intentionally uses only the stdlib (no external dependencies) so it’s easy to run locally or on small VPS instances.
- Keep secrets out of Git. Use `.env.example` for placeholders and set real secrets either in the host environment or via GitHub Actions/hosting provider secrets.
- To deploy, either use the included GitHub Actions workflow (`.github/workflows/deploy.yml`) or a hosting provider that supports Python apps (Render, Railway, etc.).

## Troubleshooting

- If the backend accepts connections on `127.0.0.1:3000` but not via the droplet public IP, check any cloud firewall or provider network settings (DigitalOcean Firewalls must be attached to the droplet and allow TCP:3000).
- If you accidentally committed a secret, rotate the key immediately and remove it from history using a tool like `git filter-repo` or BFG.

## License

MIT-style example (no warranty).