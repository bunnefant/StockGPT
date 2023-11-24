import requests
from config import LICHESS_BASE_URL, LICHESS_HEADERS
import json
import chess
import chess.svg
import random
from gpt_client import GPTAgent


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
        self.board_image_filepath = 'curr_board.svg'
        self.game_id = None
        self.agent = GPTAgent()
        self.critic_agent = GPTAgent()
        self.critic_preamble = 'Please conduct a systematic evaluation of the proposed move, \
            specifically checking for any immediate capturing threats to the piece being moved. \
            Confirm the safety of the piece post-move by examining all possible opponent\'s responses,\
            including any capturing possibilities by pawns. Emphasize the protection and \
            control of key squares around the moved piece and provide a tactical review of the new \
            position to ensure no chess motifs have been overlooked. Keep in mind the direction of pieces \
            like pawns, the white pawns move up the ranks from 1 to 8, and the black pawns move down the \
            ranks from 8 to 1. I have provided you with the game state, the current position of all pieces, \
            the proposed move, and a list of legal moves the opponent can take. Please reason about this, \
            and state if the move is unreasonable and puts \
            our moved piece or king into harms way. Please end your response in the following format "STATUS: SUCCESS" \
            or "STATUS: FAIL"'
        self.preamble = 'You are an aggressive chess bot that will evaluate a given game state and list of legal moves and propose \
            the best next move. Please reason about why you chose this specific move and consider the position your \
            opponent is in and if they can take advantage of your move. Also look for openings to try to force a checkmate \
            on your opponent or to take an undefended piece from your opponent with no repercussions. Also look to engage in trades that will benefit us materially. We will be conducting \
            this analysis in multiple rounds, so after the first round you will also have to consider any passed in critique \
            about previously suggested moves. We will also additionally pass in the move that was just played by the opponent to give a better idea of what may be important to focus on and how to counterplay when deciding your move. Please let this additional information guide your decision on choosing a \
            better move. It is imperitive that you select a move that is present in the list of legal moves provided. Please end your response in the following format "UCI: <UCI-STRING>" with only 1 proposed move.'

    def start_challenge(self, username):
        s = requests.Session()

        challenge_body = {
            'keepAliveStream': True,
            'color': 'black'
        }
        game_id = None
        with s.post(f'{LICHESS_BASE_URL}/api/challenge/{username}', headers=LICHESS_HEADERS, json=challenge_body, stream=True) as resp:
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
        self.game_id = game_id
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
    
    def format_moves(self, legal_move_dict, color):
        out = ''
        for move in legal_move_dict:
            piece, start = move
            curr_piece = f'{color} {self.pieces[piece].lower()} ({start}): '
            for target in legal_move_dict[move]:
                curr_piece += f'{target}, '
            out += curr_piece[:-2] + '\n'
        return out
    
    def get_moves(self, color):
        return self.format_moves(self.get_legal_moves(), color)
    
    def write_to_chat(self, message):
        body = {
            'room': 'player',
            'text': message
        }
        requests.post(f'{LICHESS_BASE_URL}/api/bot/game/{self.game_id}/chat', headers=LICHESS_HEADERS, json=body)

    def get_game_status(self):
        moves = self.board.fullmove_number
        if moves < 5:
            return 'OPENING'

        white_pieces = self.get_piece_positions(True)
        black_pieces = self.get_piece_positions(False)

        num_white = 0
        for piece in white_pieces:
            if piece != 'PAWN':
                num_white += len(white_pieces[piece])

        num_black = 0
        for piece in black_pieces:
            if piece != 'PAWN':
                num_black += len(black_pieces[piece])
        if num_black < 4 or num_white < 4:
            return 'END'
        else:
            return 'MID'
            
    ### FILL IN WITH LOGIC TO SELECT WHICH MOVE TO DO
    ### RETURN UCI STRING
    def compute_next_move(self, opp_move, captured=None):
        game_state = self.get_game_state()
        legal_moves = self.get_moves(self.color)
        # self.get_board_image()

        game_status = self.get_game_status()


        critique = ''
        proposed_move = ''
        for _ in range(3):     
            print(game_status)

            prompt = f'{self.preamble}\nGAME STATE:\n{game_state}\nLEGAL MOVES:\n{legal_moves}\nVISUAL GAME STATE:\n{self.board}\nOPPONENT MOVE:\n{opp_move}\n'
            if captured:
                prompt += f'OPPONENT MOVE RESULTED IN CAPTURE OF FOLLOWING PIECE:\n{chess.piece_name(captured)}'
                print(prompt)
            if critique != '' and proposed_move != '':
                prompt += f'PREVIOUS PROPOSED MOVE:\n{proposed_move}\nCRITIQUE ABOUT PREVIOUS PROPOSED MOVE:\n{critique}\n'
            print(prompt)
            resp = self.agent.query(prompt)
            proposed_move = resp.split("UCI: ")[-1].strip('."')
            print('GPT RESPONSE:')
            print(resp)
            print('--------------------------')

            self.board.push(chess.Move.from_uci(proposed_move))
            opp_legal_moves = self.get_moves('black' if self.color == 'white' else 'white')
            self.board.pop()

            critic_prompt = f'{self.critic_preamble}\nGAME STATE:\n{game_state}\nLEGAL MOVES:\n{legal_moves}\nVISUAL GAME STATE:\n{self.board}\nOPPONENT MOVE:\n{opp_move}\nOUR PROPOSED MOVE:\n{proposed_move}\nOPPONENT LEGAL MOVES AFTER PROPOSED MOVE:\n{opp_legal_moves}'
            print(critic_prompt)
            critique = self.critic_agent.query(critic_prompt)
            print('CRITIQUE')
            print(critique)
            if critique.split("STATUS: ")[-1].strip('."') == 'SUCCESS':
                break
        print(proposed_move)
        return proposed_move


        # all_legal_moves = list(self.board.legal_moves)
        # return random.choice(all_legal_moves).uci()

    def make_move(self, uci_string):
        requests.post(f'{LICHESS_BASE_URL}/api/bot/game/{self.game_id}/move/{uci_string}', headers=LICHESS_HEADERS)

    def get_board_image(self):
        svg = chess.svg.board(self.board)
        outputfile = open(self.board_image_filepath, "w")
        outputfile.write(svg)
        outputfile.close()

    def play_game(self):
        s = requests.Session()
        with s.get(f'{LICHESS_BASE_URL}/api/bot/game/stream/{self.game_id}', headers=LICHESS_HEADERS, stream=True) as resp:
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
                        # Keeping track of what move opponent made
                        new_position = json_resp['moves'].split()[-1]
                        opp_move = chess.Move.from_uci(new_position)
                        cap = None
                        if self.board.is_capture(opp_move):
                            cap = self.board.piece_at(opp_move.to_square).piece_type
                        self.board.push(opp_move)
                        
                        #Compute what move to make based on current game state and available moves
                        bot_move = self.compute_next_move(new_position, cap)
                        self.make_move(bot_move)
                        self.board.push(chess.Move.from_uci(bot_move))
                        # print(self.board)
                        print('Waiting for opponent move...')

                    elif json_resp['type'] == 'gameFull':
                        if self.color == 'white':
                            bot_move = self.get_next_move()
                            self.make_move(bot_move)
                            self.board.push(chess.Move.from_uci(bot_move))

        print('Exiting Game')


client = ChessClient()
client.start_challenge('bunnefant')
client.play_game()
