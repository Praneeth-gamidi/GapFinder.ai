"""GENERATION layer. The only file that talks to a language model."""
import json, os, re, time
import requests

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "openai/gpt-oss-120b"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "gemini-3.5-flash-lite"),
}

def chat(cfg, system, user):
    url, default_model = PROVIDERS[cfg["provider"]]
    for attempt in range(3):
        r = requests.post(url, timeout=90,
            headers={"Authorization": f"Bearer {cfg['key']}"},
            json={"model": cfg.get("model") or default_model, "temperature": 0.2,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user}]})
        if r.status_code == 429 and attempt < 2:   # free-tier rate limit: wait, retry
            try:
                wait = float(r.headers.get("retry-after", 20))
            except ValueError:
                wait = 20
            time.sleep(min(wait, 60))
            continue
        if not r.ok:
            raise RuntimeError(f"AI service error {r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"]

def chat_json(cfg, system, user):
    text = chat(cfg, system + " Reply with valid JSON only.", user)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise RuntimeError("The model did not return JSON. Try again.")
    return json.loads(m.group(0))

def config_from_env():
    for p in PROVIDERS:
        key = os.getenv(f"{p.upper()}_API_KEY")
        if key:
            return {"provider": p, "key": key, "model": os.getenv("LLM_MODEL")}
    return None
