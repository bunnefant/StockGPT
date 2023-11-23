from config import GPT_BASE_URL, GPT_HEADERS
import requests

class GPTAgent:
    def __init__(self):
        print('init')

    def query(self, prompt):
        body = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        r = requests.post(f'{GPT_BASE_URL}/v1/chat/completions', headers=GPT_HEADERS, json=body)
        return r.json()['choices'][0]['message']['content']

# agent = GPTAgent()
# agent.query('What does 2 + 2 equal?')