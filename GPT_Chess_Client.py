import requests
from secret import BASE_URL, HEADERS
import json

def start_challenge(username):
    s = requests.Session()

    challenge_body = {
        'keepAliveStream': True
    }
    game_id = None
    with s.post(f'{BASE_URL}/api/challenge/{username}', headers=HEADERS, json=challenge_body, stream=True) as resp:
        print('Sent out challenge.')
        for line in resp.iter_lines():
            if line:
                json_resp  = json.loads(line)
                if 'challenge' in json_resp:
                    game_id = json_resp['challenge']['id']
                if 'done' in json_resp and json_resp['done'] != 'accepted':
                    raise Exception('Game was not properly accepted')
    print(f'Successfully created game.')
    return game_id

game_id = start_challenge('bunnefant')
print(f'Game id: {game_id}')
