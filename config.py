from secret import LICHESS_API_KEY, GPT_API_KEY, GPT_ORG_ID

LICHESS_BASE_URL = 'https://lichess.org'
LICHESS_HEADERS = {"Authorization" : f"Bearer {LICHESS_API_KEY}"}

GPT_BASE_URL = 'https://api.openai.com'
GPT_HEADERS = {
    "Authorization" : f"Bearer {GPT_API_KEY}", 
    "Content-Type" : "application/json", 
    "OpenAI-Organization" : GPT_ORG_ID
}
