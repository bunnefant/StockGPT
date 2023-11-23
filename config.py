from secret import LICHESS_API_KEY, GPT_API_KEY

LICHESS_BASE_URL = 'https://lichess.org'
LICHESS_HEADERS = {"Authorization" : f"Bearer {LICHESS_API_KEY}"}

GPT_BASE_URL = 'https://api.openai.com'
GPT_HEADERS = {
    "Authorization" : f"Bearer {GPT_API_KEY}", 
    "Content-Type" : "application/json", 
    "OpenAI-Organization" : "org-Kg5hXSKh7Z7oOZu8JTxBFVfh"
}
