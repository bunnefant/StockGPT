import requests
from config import BASE_URL, HEADERS
import json
import chess
import random

board = chess.Board()
bot_color = None

class ChessClient:
    def __init__(self):
        self.color = None
        self.board = chess.Board()

    def start_challenge(self, username):
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
                    print(json_resp)
                    if 'challenge' in json_resp:
                        game_id = json_resp['challenge']['id']
                        self.color = json_resp['challenge']['color']
                    if 'done' in json_resp and json_resp['done'] != 'accepted':
                        raise Exception('Game was not properly accepted')
        print('Game was accepted.')
        print('Successfully created game.')
        return game_id

    def get_formatted_legal_moves(self):
        moves = []
        for move in list(board.legal_moves):
            uci = move.uci()

    ### FILL IN WITH LOGIC TO SELECT WHICH MOVE TO DO
    ### RETURN UCI STRING
    def get_next_move(self):
        all_legal_moves = list(board.legal_moves)
        return random.choice(all_legal_moves).uci()

    def make_move(self, game_id, uci_string):
        requests.post(f'{BASE_URL}/api/bot/game/{game_id}/move/{uci_string}', headers=HEADERS)    

    def play_game(self, game_id):
        s = requests.Session()
        with s.get(f'{BASE_URL}/api/bot/game/stream/{game_id}', headers=HEADERS, stream=True) as resp:
            for line in resp.iter_lines():
                if line:
                    json_resp  = json.loads(line)
                    print(json_resp)
                    if json_resp['type'] == 'gameState':
                        if json_resp['status'] != 'started':
                            resp.close()
                            print('Opponent resigned.')
                            break

                        if len(json_resp['moves'].split()) % 2 == 1 and self.color == 'white':
                            continue

                        if len(json_resp['moves'].split()) % 2 == 0 and self.color == 'black':
                            continue

                        print('game state')
                        new_position = json_resp['moves'].split()[-1]
                        board.push(chess.Move.from_uci(new_position))

                        bot_move = self.get_next_move()
                        self.make_move(game_id, bot_move)
                        board.push(chess.Move.from_uci(bot_move))
                        print(board)

                    elif json_resp['type'] == 'gameFull':
                        print('game full')
                        if self.color == 'white':
                            bot_move = self.get_next_move()
                            self.make_move(game_id, bot_move)
                            board.push(chess.Move.from_uci(bot_move))

        print('Exiting Game')


client = ChessClient()
game_id = client.start_challenge('bunnefant')
print(f'Game id: {game_id}')
client.play_game(game_id)
