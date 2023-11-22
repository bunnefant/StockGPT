import requests
from config import BASE_URL, HEADERS
import json
import chess
import random


class ChessClient:
    def __init__(self):
        self.color = None
        self.board = chess.Board()
        self.pieces = {
            chess.PAWN: 'PAWN',
            chess.KNIGHT: 'KNIGHT',
            chess.BISHOP: 'BISHOP',
            chess.ROOK: 'ROOK',
            chess.QUEEN: 'QUEEN',
            chess.KING: 'KING'
        }

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
                    if 'challenge' in json_resp:
                        game_id = json_resp['challenge']['id']
                        self.color = json_resp['challenge']['color']
                    if 'done' in json_resp and json_resp['done'] != 'accepted':
                        raise Exception('Game was not properly accepted')
        print('Game was accepted.')
        return game_id
    
    def get_piece_positions(self, color):
        piece_dict = {}
        for piece in self.pieces:
            positions = self.board.pieces(piece, color)
            for pos in positions:
                if self.pieces[piece] not in piece_dict:
                    piece_dict[self.pieces[piece]] = []
                piece_dict[self.pieces[piece]].append(chess.square_name(pos))
        return piece_dict
    
    def format_positions(self, positions, color):
        out = ''
        for piece in positions:
            curr_piece = f'{color} {piece.lower()}: '
            for pos in positions[piece]:
                curr_piece += f'{pos}, '
            out += curr_piece[:-2] + '\n'
        return out
    
    def get_game_state(self):
        bot_pos = self.get_piece_positions(self.color == 'white')
        opp_pos = self.get_piece_positions(self.color != 'white')

        formatted_bot_pos = self.format_positions(bot_pos, self.color)
        formatted_opp_pos = self.format_positions(opp_pos, 'black' if self.color == 'white' else 'white')

        return f'{formatted_bot_pos}\n{formatted_opp_pos}'

    def get_legal_moves(self):
        # moves = list(self.board.legal_moves)
        legal = {}
        for move in list(self.board.legal_moves):
            piece = self.board.piece_at(move.from_square)
            move_key = (piece.piece_type, chess.square_name(move.from_square))
            if move_key not in legal:
                legal[move_key] = []
            if move.promotion:
                legal[move_key].append(f'{chess.square_name(move.to_square)}{chess.piece_symbol(move.promotion)}')
            else:
                legal[move_key].append(chess.square_name(move.to_square))
        return legal
    
    def format_moves(self, legal_move_dict):
        out = ''
        for move in legal_move_dict:
            piece, start = move
            curr_piece = f'{self.color} {self.pieces[piece].lower()} ({start}): '
            for target in legal_move_dict[move]:
                curr_piece += f'{target}, '
            out += curr_piece[:-2] + '\n'
        return out
    
    def get_moves(self):
        return self.format_moves(self.get_legal_moves())
            

    ### FILL IN WITH LOGIC TO SELECT WHICH MOVE TO DO
    ### RETURN UCI STRING
    def get_next_move(self):
        all_legal_moves = list(self.board.legal_moves)
        return random.choice(all_legal_moves).uci()

    def make_move(self, game_id, uci_string):
        requests.post(f'{BASE_URL}/api/bot/game/{game_id}/move/{uci_string}', headers=HEADERS)    

    def play_game(self, game_id):
        s = requests.Session()
        with s.get(f'{BASE_URL}/api/bot/game/stream/{game_id}', headers=HEADERS, stream=True) as resp:
            for line in resp.iter_lines():
                if line:
                    json_resp  = json.loads(line)
                    if json_resp['type'] == 'gameState':
                        if json_resp['status'] != 'started':
                            resp.close()
                            print('Opponent resigned.')
                            break

                        if len(json_resp['moves'].split()) % 2 == 1 and self.color == 'white':
                            continue

                        if len(json_resp['moves'].split()) % 2 == 0 and self.color == 'black':
                            continue
                        new_position = json_resp['moves'].split()[-1]
                        self.board.push(chess.Move.from_uci(new_position))

                        game_state = self.get_game_state()
                        legal_moves = self.get_moves()
                        print('GAME STATE:')
                        print(game_state)
                        print('LEGAL MOVES:')
                        print(legal_moves)
                        
                        bot_move = self.get_next_move()
                        self.make_move(game_id, bot_move)
                        self.board.push(chess.Move.from_uci(bot_move))
                        print(self.board)
                        print('Waiting for opponent move...')

                    elif json_resp['type'] == 'gameFull':
                        if self.color == 'white':
                            bot_move = self.get_next_move()
                            self.make_move(game_id, bot_move)
                            self.board.push(chess.Move.from_uci(bot_move))

        print('Exiting Game')


client = ChessClient()
game_id = client.start_challenge('bunnefant')
print(f'Game id: {game_id}')
client.play_game(game_id)
