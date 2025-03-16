from pyquoridor.board import Board
from pyquoridor.utils import print_board
from pyquoridor.exceptions import GameOver
import numpy as np

def legal_moves_tensor(board, color=None):
    if color is None:
        color = board.current_player()
    moves, (horizonzal_grids, vertical_grids) = board.legal_moves(color)
    valid_moves_np = np.zeros((board.max_row, board.max_col), dtype=int)-1
    for move, L in moves[color].items():
        valid_moves_np[move.row, move.col] = L
    moves_tensor = np.zeros((3, board.max_row, board.max_col), dtype=int)
    moves_tensor[0] = valid_moves_np
    moves_tensor[1] = horizonzal_grids[color].grid
    moves_tensor[2] = vertical_grids[color].grid

    opponent_lengths = np.zeros((3, board.max_row, board.max_col), dtype=int)
    opponent_color = 'white' if color == 'black' else 'black'
    current_opponent_length = np.min(list(moves[opponent_color].values())) + 1
    opponent_lengths[1] = horizonzal_grids[opponent_color].grid
    opponent_lengths[2] = vertical_grids[opponent_color].grid
    return moves_tensor, opponent_lengths, current_opponent_length

def state_representation(board):
    state = board.state()
    board_tensor = np.zeros((4, board.max_row, board.max_col), dtype=bool)
    pawn_positions_np = np.zeros((board.max_row, board.max_col), dtype=int)
    pawn_positions_np[state['white_position'].row, state['white_position'].col] = 1
    pawn_positions_np[state['black_position'].row, state['black_position'].col] = 2
    board_tensor[0] = pawn_positions_np
    board_tensor[1] = state['horizontal_fence_grid'].grid
    board_tensor[2] = state['vertical_fence_grid'].grid
    board_tensor[3] = state['fence_center_grid'].grid
    fences_left = np.zeros(2, dtype=int)
    fences_left[0] = state['fences_left']['white']
    fences_left[1] = state['fences_left']['black']
    return board_tensor, fences_left

def calculate_scores(board, player='white'):
    player_scores, opponent_scores, current_opponent_length = legal_moves_tensor(board, player)
    mask = player_scores == -1
    scores = player_scores.astype(float)
    opponent_scores = opponent_scores.astype(float)
    scores[mask] = np.nan
    opponent_scores[mask] = np.nan
    best_path_length = np.nanmin(scores[0]) + 1
    self_delta = scores[1:] - best_path_length
    opponent_delta = opponent_scores[1:] - current_opponent_length
    scores[1:] = self_delta - opponent_delta
    scores[mask] = np.nan
    return scores

def perform_action(board, player, last_action,
                   copy_prob=0,
                   move_prob=0.5,
                   min_turn_until_fence=4,
                   min_best_fence_value=-3,
                   verbose=True):
    scores = calculate_scores(board, player)

    # Check if opponent can win
    opponent = 'white' if player == 'black' else 'black'
    opponent_close = board.player_finish_within_moves(opponent, 2)

    # Check if player can place more fences and best fence value
    fence_possible = not np.isnan(scores[1:]).all()
    best_fence_value = 0
    if fence_possible:
        best_fence_value = np.nanmin(scores[1:])

    # Check if player can finish
    player_can_finish = np.nanmin(scores[0]) == 0
    opponent_victory_can_be_prevented = opponent_close and best_fence_value < 0

    move = np.random.rand() < move_prob
    if np.random.rand() < copy_prob:
        move = last_action == 'move_pawn'
    if player_can_finish or not fence_possible or board.turn < min_turn_until_fence:
        if verbose:
            print(f'{player} can finish or cannot put fences, moving')
        move = True
    elif opponent_victory_can_be_prevented or best_fence_value < min_best_fence_value:
        if verbose:
            print(f'{player}: placing fence triggered, nice fence available ({best_fence_value}) or opponent victory should be avoided')
        move = False
    elif best_fence_value >= 0:
        if verbose:
            print(f'{player}: best fence value is positive, moving')
        move = True
    # move = not opponent_victory_can_be_prevented and not fence_possible or best_fence_value >= 0 or board.fences_left[player] == 0 or np.random.rand() < move_prob
    action_details = {}
    if move:
        min_val = np.nanmin(scores[0])
        m = scores[0] == min_val
        move_idxs = np.argwhere(m)
        i = np.random.choice(len(move_idxs))    
        row, col = move_idxs[i]
        
        # Move pawn
        action_details['action'] = 'move_pawn'
        # action_details['source_row']
        # action_details['source_col']
        action_details['target_row'] = int(row)
        action_details['target_col'] = int(col)
        try:
            board.move_pawn(player, row, col)
        except GameOver as e:
            # Bot wins the game
            print(f"Bot wins the game. Game over: {e}", print_board(board))
        if verbose:
            print(f'{player} moves to ({row}, {col}). Fences left: {board.fences_left[player]}')
    else:
        m = scores[1:] == best_fence_value
        fence_idxs = np.argwhere(m)
        i = np.random.choice(len(fence_idxs))
        t, row, col = fence_idxs[i]

        # Place fence
        orientation = 'h' if t == 0 else 'v'
        action_details['action'] = 'place_fence'
        action_details['row'] = int(row)
        action_details['col'] = int(col)
        action_details['wall_type'] = orientation
        board.place_fence(row, col, orientation)
        if verbose:
            print(f'{player} places {orientation} fence ({row}, {col}). Fences left: {board.fences_left[player]}')
    
    action_details['player_color'] = player

    return board, action_details