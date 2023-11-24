import chess

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

FEN_str = input("Put in a FEN string:\n")
board = chess.Board(FEN_str)
piece_positions = get_piece_positions(board)

abbv_2_piece = {'r': 'Rook(s)', 'n': 'Knight(s)', 'b': 'Bishop(s)', 'q': 'Queen(s)', 'k': 'King', 'p': 'Pawn(s)'}
colors = ['White', 'Black']

gamee_state = ""

print("GAME STATE")
for color in colors:
    for piece in piece_positions:
        output = f"{color} {abbv_2_piece[piece]}: "
        if color.lower() in piece_positions[piece]:
            output += ', '.join(piece_positions[piece][color.lower()])
        print(output)
    print("")


legal_moves = [board.san(move) for move in board.legal_moves]
if board.turn == chess.WHITE:
    print("White's Turn!")
else:
    print("Black's Turn!")
print("LEGAL MOVES")
print(', '.join(legal_moves))