import chess
import win32clipboard

def get_piece_positions(board):
    piece_positions = {}
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            piece_color = "white" if piece.color == chess.WHITE else "black"
            piece_name = piece.symbol().lower()
            if piece_name not in piece_positions:
                piece_positions[piece_name] = {}
            if piece_color not in piece_positions[piece_name]:
                piece_positions[piece_name][piece_color] = []
            piece_positions[piece_name][piece_color].append(chess.square_name(square))
    return piece_positions

win32clipboard.OpenClipboard()
FEN_str = win32clipboard.GetClipboardData()
win32clipboard.CloseClipboard()

board = chess.Board(FEN_str)

abbv_2_piece = {'r': 'Rook(s)', 'n': 'Knight(s)', 'b': 'Bishop(s)', 'q': 'Queen(s)', 'k': 'King', 'p': 'Pawn(s)'}
colors = ['White', 'Black']


def get_game_state(board):
    game_state = ""
    piece_positions = get_piece_positions(board)
    game_state += "GAME STATE\n"
    for color in colors:
        for piece in piece_positions:
            output = f"{color} {abbv_2_piece[piece]}: "
            if color.lower() in piece_positions[piece]:
                output += ', '.join(piece_positions[piece][color.lower()])
            game_state += output + "\n"
        game_state += "\n"


    if board.turn == chess.WHITE:
        game_state += "White's Turn!\n"
    else:
        game_state += "Black's Turn!\n"

    legal_moves = [board.san(move) for move in board.legal_moves]
    game_state += "LEGAL MOVES\n" + ', '.join(legal_moves)

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(game_state)
    win32clipboard.CloseClipboard()
    print(game_state)

get_game_state(board)
move = input("Insert proposed move")
board.push_san(move)
get_game_state(board)
