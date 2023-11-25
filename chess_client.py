import requests
from config import LICHESS_BASE_URL, LICHESS_HEADERS
from secret import LICHESS_USERNAME
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
        self.critic_preamble = 'Please conduct a systematic evaluation of the proposed move. \
            Your role is to identify the greatest threat posed by the enemy, and decide if the proposed move leads to our best outcome.\
            Keep in mind, the best move might not be immediately winning. \
            You should begin by first asking why the opponent made that move.\
            Then you should begin your analysis by ensuring our king is not in any immediate danger of being checkmated. \
            Next you should identify all potential moves the opponent can make that would capture one of our pieces. \
            Each of these moves should be closely analyzed to ensure we do not accidentally sacrifice pieces of value. \
            Prioritize the safety of our most valuable pieces first. \
            When judging a trade. Keep in mind the value of different pieces: \
            Queen: 9, Rook: 5, Bishop: 3, Knight: 3, Pawn: 1. \
            \
            I have provided you with the game state, the current position of all pieces, \
            the proposed move, and a list of legal moves the opponent can take. Please reason about this, \
            and state if the move is unreasonable. If the move is unreasonable please address the biggest threat the opponent has that needs to be addressed.\
            Ensure you evaluate what is gained by the proposed move as well, if we capture their queen and they capture our rook it is still beneficial.\
            \
            Please end your response in the following format "STATUS: SUCCESS" or "STATUS: FAIL"'
        self.prefix = 'You are an aggressive chess bot that will evaluate a given game state and list of legal moves and propose \
            the best next move.'
        self.body = 'Please reason about why you chose this specific move and consider the position your \
            opponent is in and if they can take advantage of your move. First attempt to identify any weaknesses in the opponents position, \
            such as an undefended piece, or king safety issues. Your first priority is to look for checks, and examine if any lead to a checkmate, or material gain.\
            Next, you should examine all captures. Ensure you check all captures and capitalize if the opponent leaves a piece unprotected or not properly defended.\
            Next, you should consider any attacks you can make on their pieces. Next conclude by identifying which move you think is the strongest.\
            \
            We will be conducting this analysis in multiple rounds, after the first round you will also have to consider any passed in critique \
            about the previously suggested moves. The critique will identify threats you may have overlooked, ensure your next move properly addresses the critique.\
            \
            You can only select a move in the list of legal moves provided. Please end your response in the following format "UCI: <UCI-STRING>" with only 1 proposed move.'
        self.opening_prompt = ' You are still in a chess opening. Keep that in mind when you decide on your move to play. \
            Here are some key opening principles to keep in mind while deciding your move. \
            1) Develop your pieces. Get all your pieces out and into the game early, most specifically bishops and knights. \
            2) Control the center. The center is the most valuable area to control on the chess board in the early game. \
            3) Keep the queen safe. Moving the queen out too far early can make it a target. \
            4) Castle the king. Develop pieces so the king can castle, and be safe.\
            Keep in mind all of these concepts are very general, and there are exceptions to each of them. \
            For example, moving the queen out early is worth it if we are gaining material.\
            Use these concepts when there is no obvious advantageous move.'
        self.mid_game_prompt = ' You are now in a chess mid game. Keep that in mind when deciding the optimal move. Find good positions \
            on the board for your pieces without losing them. Prevent your opponent from getting material advantages and prevent them \
            from finding good squares for their own pieces.'
        self.end_game_prompt = ' You are now in a chess end game. Keep that in mind when you make your move. Make sure to \
            find places on the board where you have the advantage and push on that side of the board while defending your pieces \
            and limiting the opponent\'s ability to push their own advantage. This is also the point in the game where the king becomes \
            a more valuable piece. Consider activating the king and finding ways where it can help in making progress.'

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
                    json_resp = json.loads(line)
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
        formatted_opp_pos = self.format_positions(
            opp_pos, 'black' if self.color == 'white' else 'white')

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
                legal[move_key].append(
                    f'{chess.square_name(move.to_square)}{chess.piece_symbol(move.promotion)}')
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

    def is_legal(self, legal_moves, proposed_move):
        initial_location = proposed_move[:2]
        end_location = proposed_move[2:]
        
        legal_moves_by_line = legal_moves.split('\n')
        for line in legal_moves_by_line:
            try:
                start_index = line.index('(')
            except ValueError as e:
                print(f"Legal moves:\n{legal_moves}\
                      \nLine: {line}")
                raise e
            if initial_location == line[start_index + 1: start_index + 3]:
                if end_location in line[start_index + 6:]:
                    return True
                else:
                    return False
        return False
        

    def write_to_chat(self, message):
        body = {
            'room': 'player',
            'text': message
        }
        requests.post(f'{LICHESS_BASE_URL}/api/bot/game/{self.game_id}/chat',
                      headers=LICHESS_HEADERS, json=body)

    def get_game_status(self):
        moves = self.board.fullmove_number
        if moves < 8:
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

    # FILL IN WITH LOGIC TO SELECT WHICH MOVE TO DO
    # RETURN UCI STRING
    def compute_next_move(self, opp_move, captured=None):
        game_state = self.get_game_state()
        legal_moves = self.get_moves(self.color)
        # self.get_board_image()

        game_status = self.get_game_status()

        critique = ''
        proposed_move = ''
        last_proposed_legal_move = None
        for _ in range(3):
            print(game_status)
            if game_status == 'OPENING':
                stage_prompt = self.opening_prompt
            elif game_status == 'MID':
                stage_prompt = self.mid_game_prompt
            else:
                stage_prompt = self.end_game_prompt

            prompt = f'{self.prefix}{stage_prompt}{self.body}\nGAME STATE:\n{game_state}\nLEGAL MOVES:\n{legal_moves}\nVISUAL GAME STATE:\n{self.board}\nOPPONENT MOVE:\n{opp_move}\n'
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
            opp_legal_moves = self.get_moves(
                'black' if self.color == 'white' else 'white')
            self.board.pop()

            critic_prompt = f'{self.critic_preamble}\nGAME STATE:\n{game_state}\nLEGAL MOVES:\n{legal_moves}\nVISUAL GAME STATE:\n{self.board}\nOPPONENT MOVE:\n{opp_move}\nOUR PROPOSED MOVE:\n{proposed_move}\nOPPONENT LEGAL MOVES AFTER PROPOSED MOVE:\n{opp_legal_moves}'
            print(critic_prompt)
            if not self.is_legal(legal_moves, proposed_move):
                critique = f'The proposed move is illegal! STATUS: FAIL'
            else:
                critique = self.critic_agent.query(critic_prompt)
                last_proposed_legal_move = proposed_move
            print('CRITIQUE')
            print(critique)
            if critique.split("STATUS: ")[-1].strip('."') == 'SUCCESS':
                break
        print(last_proposed_legal_move)
        if last_proposed_legal_move is None:
            print("ALL PROPOSED MOVES WERE ILLEGAL. GPT IS VERY STUPID!")
            print("ALL PROPOSED MOVES WERE ILLEGAL. GPT IS VERY STUPID!")
            print("ALL PROPOSED MOVES WERE ILLEGAL. GPT IS VERY STUPID!")
            last_proposed_legal_move = legal_moves.split(', ')[-1]
        return proposed_move

        # all_legal_moves = list(self.board.legal_moves)
        # return random.choice(all_legal_moves).uci()

    def make_move(self, uci_string):
        requests.post(
            f'{LICHESS_BASE_URL}/api/bot/game/{self.game_id}/move/{uci_string}', headers=LICHESS_HEADERS)

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
                    json_resp = json.loads(line)
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
                            cap = self.board.piece_at(
                                opp_move.to_square).piece_type
                        self.board.push(opp_move)

                        # Compute what move to make based on current game state and available moves
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
client.start_challenge(LICHESS_USERNAME)
client.play_game()
