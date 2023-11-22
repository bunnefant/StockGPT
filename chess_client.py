import requests
from config import BASE_URL, HEADERS
import json
import chess

board = chess.Board()

def start_challenge(username):
    s = requests.Session()

    challenge_body = {
        'keepAliveStream': True,
        'color': 'black'
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
    print('Game was accepted.')
    print('Successfully created game.')
    return game_id

def play_game(game_id):
    s = requests.Session()
    with s.get(f'{BASE_URL}/api/bot/game/stream/{game_id}', headers=HEADERS, stream=True) as resp:
        for line in resp.iter_lines():
            if line:
                json_resp  = json.loads(line)
                print(json_resp)
                if json_resp['type'] == 'opponentGone' and json_resp['gone']:
                    print('Opponent Gone.')
                    print('Exiting game.')
                    resp.close()
                elif json_resp['type'] == 'gameState':
                    print('game state')
                    new_position = chess.Move.from_uci(json_resp['moves'].split()[-1])
                    board.push(new_position)
                    print(list(board.legal_moves))
                    print(board)
                elif json_resp['type'] == 'gameFull':
                    print('game full')
    print('done')



game_id = start_challenge('bunnefant')
print(f'Game id: {game_id}')
play_game(game_id)
