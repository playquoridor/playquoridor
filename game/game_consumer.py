import json
from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from .models import QuoridorGame
# from .logic.board import Board
# from .logic.exceptions import *
from pyquoridor.board import Board
from pyquoridor.utils import print_board
from pyquoridor.exceptions import *
from rest_framework.authtoken.models import Token

from datetime import datetime, timezone, timedelta
import django.utils.timezone as djtz
from collections import defaultdict
from game.game_utils import abort_game_if_not_started
from game.game_utils import create_game, user_has_active_game

# from django_tasks import task
import threading
import time


class GameConsumer(WebsocketConsumer):
    def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'

        # Extract token from query parameters
        self.player = None
        if 'query_string' in self.scope:
            token_key = None
            query_string = self.scope["query_string"].decode()
            split = query_string.split("&")
            if len(split) > 0:
                for param in split:
                    if '=' in param:
                        key, value = param.split("=")
                        if key == "token":
                            token_key = value
                            break
                
                # Validate token
                if token_key:
                    try:
                        token = Token.objects.get(key=token_key)
                        user = token.user

                        # TODO: Check if user is bot? i.e. allow only bots to connect via token
                        self.player = user.username  # Assign authenticated user
                    except Token.DoesNotExist:
                        self.disconnect()  # Reject connection
                        return

        # Get player information
        user = self.scope['user']
        isbot = self.player is not None
        self.session_key = None
        self.is_anonymous = False
        if isinstance(user, AnonymousUser) and not isbot:
            print('Anonymous user', user, self.player)
            # Get session key of anonymous users
            session_key = self.scope['session'].session_key
            self.session_key = session_key
            self.player = 'Anonymous'
            self.is_anonymous = True
        elif self.player is None:
            self.player = user.username

        # Check that user is authorised

        # Load game
        self.game = get_object_or_404(QuoridorGame,
                                      pk=self.game_id)  # QuoridorGame.objects.get(pk=self.game_id)  # self.game_id)

        # Join game group
        async_to_sync(self.channel_layer.group_add)(
            self.game_group_name, self.channel_name
        )
        print('Channel name', self.channel_name)

        # Accept the connection
        self.accept()

        # Dummy message: For some reason, the first message to the client is lost
        self.send(text_data=json.dumps({'action': 'dummy'}))

        # If left to None, consumer is just a spectator
        self.player_color = None

        # Get color of the player
        players = self.game.player_set.all()
        self.color2username = {}
        self.player_session_key = None
        for player in players:
            self.color2username[player.player_color] = player.username
            if player.username.lower() == 'anonymous' and self.is_anonymous and player.session_key == self.session_key:
                self.player_color = player.player_color
                self.player_session_key = player.session_key
            elif player.username.lower() != 'anonymous' and self.player == player.username:
                self.player_color = player.player_color
            else:
                self.opponent_username_nonspectator = player.username
                self.opponent_session_key = player.session_key
        self.username2color = {v: k for k, v in self.color2username.items()}
        
        # Instantiate board logic
        start = time.time()
        self.reset_board_logic_from_db()
        end = time.time()
        print('Elapsed time DB reset', end - start)

        # Check if there's a winner
        if self.game.ended():
            self.send_game_over_message()
        try:
            self.board_logic.check_winner()
        except GameOver as e:
            if not self.game.ended():
                winner_username = self.color2username[e.winner]
                self.finish_game(winner_username)
            else:
                self.send_game_over_message()

        # Acknowledge connection flag
        self.ack_conn = True  # TODO?

        # Check
        if not self.board_logic_matches_db():
            print('Board logic does not match DB')
            print('Board logic FEN', self.board_logic.partial_FEN())
            print('DB FEN', self.game.FEN().replace(' ', ''))
            self.reset_board_logic_from_db()
        
        if self.game.number_of_moves() < 2:
            self.timer = threading.Timer(60, self.abort_game_if_not_started)  # Abort after 10 sec
            self.timer.start()  # Start countdown


    def reset_board_logic_from_db(self):
        if self.is_spectator():  # Spectator
            self.board_logic = Board()
            players = self.game.player_set.all()
            fences = self.game.fence_set.all()
            for fence in fences:
                self.board_logic.place_fence(fence.row, fence.col, fence.fence_type_str, check_winner=False, check_update_fences=False, run_BFS=False)

            for player in players:
                self.board_logic._set_pawn_location(player.player_color, target_row=player.row, target_col=player.col)
        else:
             # Instantiate board logic
            self.board_logic = Board()

            # if not self.is_spectator():
            # Save intermediate FENs to check for 3 move repetitions
            self.FEN_history = defaultdict(int)
            self.FEN_history[self.board_logic.FEN()] += 1

            for move in self.game.move_set.all().order_by('move_number'):
                if move.pawn_move is not None:
                    try:
                        self.board_logic.move_pawn(self.board_logic.current_player(),
                                                move.pawn_move.row,
                                                move.pawn_move.col,
                                                check_player=False,
                                                check_winner=False)
                    except GameOver as e:
                        pass
                else:
                    self.board_logic.place_fence(move.fence.row,
                                                move.fence.col,
                                                move.fence.fence_type_str,
                                                check_winner=False,
                                                run_BFS=False)
                self.FEN_history[self.board_logic.FEN()] += 1

        
    def disconnect(self, close_code):
        print('Disconnecting from game consumer...', self.player_color)
        print(self.game_group_name)
        print(self.channel_name)
        print('Close code', close_code)
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.game_group_name, self.channel_name
        )

    def _check_active_player(self, player):
        active_player = self.game.get_active_player()
        if player != active_player:
            raise InvalidPlayer(f'Turn of player {active_player}')

    def get_winner_color(self, winner_username):
        if winner_username == '-' or winner_username is None:
            return '-'
        return self.username2color[winner_username]

    """
    Sending board states
    """

    def send_board_state(self):
        # Load the board state
        FEN = self.game.FEN()

        # Get player details
        if self.is_spectator(): # Spectator
            player_username = self.color2username['white']
            opponent_username = self.color2username['black']
        else:
            player_username = self.player
            opponent_username = self.opponent_username_nonspectator

        # Send FEN
        text_data_json = {
            'action': 'FEN',
            'FEN': FEN,
            'game_id': self.game.game_id,
            'player_color': self.player_color,
            'player_username': player_username,
            'opponent_username': opponent_username
        }

        # Send message to websocket
        self.send(text_data=json.dumps(text_data_json))

        """
        # Send message to group to acknowledge connection
        text_data_json = {'action': 'acknowledge_connection',
                          'player_color': self.player_color}
        async_to_sync(self.channel_layer.group_send)(
            self.game_group_name, {'type': 'game_message',
                                   'contents': text_data_json,
                                   'channel_name': self.channel_name}
        )
        """

    def send_PGN(self):
        # Load PGN
        PGN = self.game.PGN()

        # Get player details
        if self.is_spectator(): # Spectator
            player_username = self.color2username['white']
            opponent_username = self.color2username['black']
        else:
            player_username = self.player
            opponent_username = self.opponent_username_nonspectator

        # Send FEN
        # print('PGN', PGN)
        text_data_json = {
            'action': 'PGN',
            'PGN': PGN,
            'move_count': self.game.move_count(),
            'game_id': self.game.game_id,
            'player_color': self.player_color,
            'player_username': player_username,
            'opponent_username': opponent_username
        }

        # Send message to websocket
        self.send(text_data=json.dumps(text_data_json))

    """
    Utils
    """

    def is_spectator(self):
        return self.player_color is None

    def next_active_player(self, player_color):
        # TODO: 2+ players
        if player_color == 'white':
            active_player = 'black'
        else:
            active_player = 'white'
        return active_player

    """
    Game events
    """

    def place_fence(self, text_data_json, check_active_player, make_updates=True):
        if self.game.ended():
            return

        move_time = datetime.now(timezone.utc)

        # To update database, check_active_player needs to be True
        assert self.ack_conn
        try:
            player = text_data_json['player_color']
            if check_active_player:
                self._check_active_player(player)
            updates_game_state = make_updates and self.player_color == player

            # row, col = text_data_json['fence_coords_1']
            row = text_data_json['row']
            col = text_data_json['col']
            wall_type = text_data_json['wall_type']
            fence_type = wall_type == 'v'

            if self.game.get_fence_number(player) == 0 and updates_game_state:
                raise InvalidFence(f'Player {player} ran out of walls')

            # Place fence. This function raises an error if fence is invalid
            self.board_logic.place_fence(row, col, wall_type, run_BFS=updates_game_state, check_update_fences=updates_game_state)
            if not self.is_spectator():
                self.FEN_history[self.board_logic.FEN()] += 1

            # If consumer's associated player is placing the fence, update database and communicate with other player
            if updates_game_state:
                # Place fence and decrease number of walls
                # (changes active player in the same transaction)
                remaining_fences, active_player, remaining_time = self.game.place_fence(player, row, col, fence_type,
                                                                                        move_time=move_time)

                # remaining_fences = self.game.decrease_fences(player)
                # text_data_json['player'] = self.player
                text_data_json['player_color'] = self.player_color
                text_data_json['remaining_fences'] = remaining_fences

                # Send new active player
                text_data_json['last_username'] = self.color2username[player]
                text_data_json['last_color'] = player
                text_data_json['active_username'] = self.color2username[active_player]
                text_data_json['active_color'] = active_player
                text_data_json['winner_username'] = ''
                text_data_json['winner_color'] = ''

                # Set remaining time
                text_data_json['remaining_time'] = remaining_time

                # Set move count
                text_data_json['move_count'] = self.game.move_count()

                # Send message to game group
                async_to_sync(self.channel_layer.group_send)(
                    self.game_group_name, {'type': 'game_message',
                                           'contents': text_data_json,
                                           'channel_name': self.channel_name}
                )
            else:
                active_player = self.game.get_active_player()

            # If new active player corresponds to consumer, send moves
            if active_player == self.player_color:
                self.send_pawn_moves(player_color=self.player_color)

        except InvalidFence as e:
            print(e, print_board(self.board_logic))
        except InvalidPlayer as e:
            print(e, print_board(self.board_logic))

    def move_pawn(self, text_data_json, check_active_player, make_updates=True):
        if self.game.ended():
            return

        move_time = datetime.now(timezone.utc)

        # To update database, check_active_player needs to be True
        assert self.ack_conn
        try:
            player = text_data_json['player_color']
            if check_active_player:
                self._check_active_player(player)

            row = text_data_json['target_row']
            col = text_data_json['target_col']
            self.board_logic.move_pawn(player=player,
                                       target_row=row,
                                       target_col=col)
            if not self.is_spectator():
                self.FEN_history[self.board_logic.FEN()] += 1
                if self.FEN_history[self.board_logic.FEN()] >= 3:
                    raise GameOver('-', True, 'Three move repetition')

            # If consumer's associated player is moving the pawn, update database and communicate with other player
            updates_game_state = make_updates and self.player_color == player
            if updates_game_state:
                # Update database
                active_player, remaining_time = self.game.update_pawn_position(self.player_color, row, col,
                                                                               move_time=move_time)

                # Send new active player
                text_data_json['last_username'] = self.color2username[player]
                text_data_json['last_color'] = player
                text_data_json['active_username'] = self.color2username[active_player]
                text_data_json['active_color'] = active_player
                text_data_json['winner_username'] = ''
                text_data_json['winner_color'] = ''

                # Set remaining time
                text_data_json['remaining_time'] = remaining_time

                # Set move count
                text_data_json['move_count'] = self.game.move_count()

                # Send message to game group
                # TODO: Assert key type not in text_data_json
                print('Sending message to group...', text_data_json)
                async_to_sync(self.channel_layer.group_send)(
                    self.game_group_name, {'type': 'game_message',
                                           'contents': text_data_json,
                                           'channel_name': self.channel_name}
                )
            else:
                active_player = self.game.get_active_player()

            # If new active player corresponds to consumer, send moves
            if active_player == self.player_color:
                self.send_pawn_moves(player_color=self.player_color, check_winner=True)

        except GameOver as e:
            if str(e) == 'Three move repetition':
                winner_username = '-'
                draw = True
            else:
                # Set winner
                winner_username = self.color2username[e.winner]
                draw = False

            if e.last_move and make_updates and self.player_color == player:
                # Update database
                active_player, remaining_time = self.game.update_pawn_position(self.player_color, row, col,
                                                                            move_time=move_time)

                # Send new active player
                active_player = self.game.get_active_player()
                text_data_json['last_username'] = self.color2username[active_player]
                text_data_json['last_color'] = active_player
                text_data_json['active_username'] = self.color2username[active_player]
                text_data_json['winner_username'] = winner_username
                text_data_json['winner_color'] = self.get_winner_color(winner_username)
                text_data_json['just_finished'] = True

                # Set remaining time
                text_data_json['remaining_time'] = remaining_time

                # Set move count
                text_data_json['move_count'] = self.game.move_count()

                # Send move message
                async_to_sync(self.channel_layer.group_send)(
                    self.game_group_name, {'type': 'game_message',
                                        'contents': text_data_json,
                                        'channel_name': self.channel_name}
                )

                # Finish game
                self.finish_game(winner_username, draw=draw, draw_reason='Three move repetition' if draw else None)

                print(e, print_board(self.board_logic))
        except InvalidMove as e:
            print(e, print_board(self.board_logic))
        except InvalidPlayer as e:
            print(e, print_board(self.board_logic))

    def send_pawn_moves(self, player_color, check_winner=False):
        if self.game.ended():
            return

        # Only send valid moves if player is active
        active_player = self.game.get_active_player()
        if active_player == player_color and not self.board_logic.game_finished():
            valid_squares = self.board_logic.valid_pawn_moves(player_color, check_winner=check_winner)
            valid_squares_str = ''
            for square in valid_squares:
                col_char = chr(square.col + 65)
                row = square.row + 1
                square_str = f'{col_char}{row}'
                valid_squares_str += square_str

            text_data = {'action': 'pawn_moves',
                         'player_color': player_color,
                         'valid_squares': valid_squares_str,
                         'game_id': self.game.game_id}
            self.send(text_data=json.dumps(text_data))

    """
    Game termination
    """

    def update_player_rating(self, player_color, winner_username, draw=False):
        # assert winner_username
        # assert player_color == self.player_color

        # Update player's rating
        if self.game.is_rated() and not self.is_spectator() and not self.game.ratings_updated(player_color):
            self.game.update_rating(player_color, winner_username, draw)

    def finish_game(self, winner_username, draw=False, abort=False, draw_reason=None):
        """
        Assumes game has not ended
        Sets winner, updates player ratings, and messages consumers to inform about game over
        """
        assert winner_username != ''

        # Set winning user
        self.game.set_winner(winner_username, draw=draw, abort=abort)

        if not abort:
            # Update ratings
            for color in self.color2username.keys():
                self.update_player_rating(color, winner_username=winner_username, draw=draw)

        # Game over message
        text_data = {
            'action': 'game_over',
            'winner_username': winner_username,
            'winner_color': self.get_winner_color(winner_username),
            'draw': draw,
            'draw_reason': draw_reason,
            'abort': abort,
            'just_finished': True,
            'game_id': self.game.game_id
        }
        self.game_over(text_data)
        async_to_sync(self.channel_layer.group_send)(
            self.game_group_name, {'type': 'game_message',
                                   'contents': text_data,
                                   'channel_name': self.channel_name}
        )

    def game_over(self, text_data):
        # Update player's rating (it should already have been updated)
        # self.update_player_rating(winner_username=text_data['winner_username'])
        # Update ratings

        # Set winning user
        if not self.game.ended():
            self.game.set_winner(text_data['winner_username'], draw=text_data['draw'], abort=text_data['abort'])  # self.winner_username)

        if not self.game.aborted():
            # Set delta ratings
            for color, player in self.color2username.items():
                # Update rating if not updated
                self.update_player_rating(color, winner_username=text_data['winner_username'], draw=text_data['draw'])

                # Store deltas
                if self.game.is_rated():
                    delta_rating = self.game.delta_rating(player)
                    text_data[f'{color}_delta_rating'] = int(delta_rating)
                else:
                    text_data[f'{color}_delta_rating'] = None

        # Include player details
        if self.is_spectator(): # Spectator
            player_username = self.color2username['white']
            opponent_username = self.color2username['black']
        else:
            player_username = self.player
            opponent_username = self.opponent_username_nonspectator
        text_data['player_color'] = self.player_color
        text_data['player_username'] = player_username
        text_data['opponent_username'] = opponent_username
        if self.game.time_end is not None:  # TODO: Remove this line after migration
            text_data['end_time'] = self.game.time_end.strftime('%Y/%m/%d %H:%M:%S')
        text_data['time_now'] = djtz.now().strftime(
            '%Y/%m/%d %H:%M:%S')  # Ref: https://stackoverflow.com/questions/33248809/python-django-timezone-is-not-working-properly
        # datetime.utcnow()

        # Send PGN
        self.send_PGN()

    def send_game_over_message(self):
        # Game over message
        winner_username = self.game.winner_username()
        text_data = {
            'action': 'game_over',
            'winner_username': winner_username,
            'winner_color': self.get_winner_color(winner_username),
            'abort': self.game.abort,
            'draw': self.game.draw,
            'game_id': self.game.game_id
        }
        self.game_over(text_data)
        self.send(text_data=json.dumps(text_data))

    def abort(self, text_data):
        if self.is_spectator(): # Spectator
            return
        
        # TODO: 2+ players
        if not self.game.ended() and self.game.move_count() < 2:
            winner_username = '-'
            self.finish_game(winner_username, abort=True)
    
    def abort_game_if_not_started(self):
        # Automatic abortion of game if not started in 30 seconds
        abort_game_if_not_started(self.game_id) # .using(run_after=timedelta(seconds=30)).enqueue()
        self.abort(None)


    def resign(self, text_data):
        if self.is_spectator(): # Spectator
            return
        
        # TODO: 2+ players
        if not self.game.ended():
            losing_color = text_data['player_color']
            winning_color = self.next_active_player(losing_color)
            winner_username = self.color2username[winning_color]
            self.finish_game(winner_username)

    def offer_draw(self, text_data):
        if self.is_spectator(): # Spectator
            return

        if self.player_color == text_data['player_color']:
            # User proposing message to other player
            async_to_sync(self.channel_layer.group_send)(
                self.game_group_name, {'type': 'game_message',
                                       'contents': text_data,
                                       'channel_name': self.channel_name,
                                       'donotsend': True
                                       }
            )
        else:
            # Other user is proposing player to me
            self.send(text_data=json.dumps(text_data))

    def accept_draw(self, text_data):
        if self.is_spectator():  # Spectator
            return

        # User accepting draw offer from other player
        print('Accepting draw offer...', text_data)
        if self.player_color == text_data['player_color']:
            if not self.game.ended():
                winner_username = '-'
                self.finish_game(winner_username, draw=True, draw_reason='Draw accepted')

            # Send confirmation
            text_data['just_finished'] = True
            async_to_sync(self.channel_layer.group_send)(
                self.game_group_name, {'type': 'game_message',
                                       'contents': text_data,
                                       'channel_name': self.channel_name,
                                       'donotsend': True
                                       }
            )
        else:
            # Other user is accepting draw offer
            self.send(text_data=json.dumps(text_data))

    def check_time_out(self):
        """
        Checks if anyone has lost on time
        """
        if self.game.is_timed() and not self.game.ended():
            _, _, color2time = self.game.get_player_details()
            for player_color, remaining_time in color2time.items():
                if remaining_time <= 0.:
                    next_player_color = self.next_active_player(player_color)
                    winner_username = self.color2username[next_player_color]
                    self.finish_game(winner_username)
                    break

    """
    Consumer functions
    """

    def receive(self, text_data):
        # Receive message from websocket
        print('Message received from websocket: ', text_data)
        text_data = json.loads(text_data)
        is_player = not self.is_spectator()
        self.perform_action(text_data, check_active_player=is_player, make_updates=is_player)

    def acknowledge_connection(self, text_data):
        # TODO: 2+ players
        if not self.ack_conn:
            self.ack_conn = text_data['player_color'] != self.player_color

            # TODO: Needs to reply...
            # Send message to group to acknowledge connection
            text_data_json = {'action': 'acknowledge_connection',
                              'player_color': self.player_color}
            async_to_sync(self.channel_layer.group_send)(
                self.game_group_name, {'type': 'game_message',
                                       'contents': text_data_json,
                                       'channel_name': self.channel_name}
            )

    def board_logic_matches_db(self):
        return self.game.FEN().replace(' ', '').startswith(self.board_logic.partial_FEN())

    """
    Rematch
    """
    def propose_challenge(self, text_data):
        if not self.is_spectator() and self.player == text_data['challenger']:
            text_data['challenger'] = self.player

            # Check if user has an active game. If yes, automatically reject challenge
            # (allowing one active game at a time to prevent concurrent rating updates)
            if user_has_active_game(self.player, session_key=self.session_key):
                text_data = {
                    'action': 'challenge_response',
                    'response': 'reject'
                }
                self.send(text_data=json.dumps(text_data))
            else:
                if 'challenged_color' in text_data:
                    text_data['player_color'] = text_data['challenged_color']
                elif self.player_color == 'white':
                    text_data['player_color'] = 'black'
                else:
                    text_data['player_color'] = 'white'

                if self.player_color == text_data['player_color']:
                    # User proposing message to other player
                    async_to_sync(self.channel_layer.group_send)(
                        self.game_group_name, {'type': 'game_message',
                                            'contents': text_data,
                                            'channel_name': self.channel_name,
                                            'donotsend': True}
                    )
                else:  
                    # Other user is proposing player to me  
                    self.send(text_data=json.dumps(text_data))

    def respond_challenge(self, text_data):
        # TODO: Important game details should match between both players...
        #  (need avoid injecting e.g. different times when responding a challenge)

        print('Responding challenge...', text_data)
        # TODO: Check that users DON'T have active game (i.e. multiple consumers per user)
        if not self.is_spectator() and text_data['response'] == 'accept':
            if self.player == text_data['challenged']:  # self.player_color == text_data['player_color']: # if self.player == text_data['challenged']:  # Challenge accepted
                # Check that users don't have an active game.
                if not user_has_active_game(self.player, session_key=self.session_key) and \
                    not user_has_active_game(self.opponent_username_nonspectator, session_key=self.opponent_session_key):
                    time = int(text_data['time']) if 'time' in text_data else None
                    increment = int(text_data['increment']) if 'increment' in text_data else None
                    rated = bool(text_data['rated']) if 'rated' in text_data else True
                    assert self.player != text_data['challenger'] or self.session_key != self.opponent_session_key
                    game = create_game(player_username=self.player,
                                    opponent_username=text_data['challenger'],  # opponent_username_nonspectator?
                                    player_color=text_data['player_color'],
                                    time=time,
                                    increment=increment,
                                    rated=rated,
                                    player_session_key=self.session_key,
                                    opponent_session_key=self.opponent_session_key,
                                    )
                    text_data['game_id'] = game.game_id

                    print('Sending back challenge response to all users...', self.player, text_data)
                    
                    async_to_sync(self.channel_layer.group_send)(
                        self.game_group_name, {'type': 'game_message',
                                        'contents': text_data,
                                        'channel_name': self.channel_name,
                                        'donotsend': True
                                        }
                    )
                    # Other user is accepting challenge
                    self.send(text_data=json.dumps(text_data))
                else:
                    # Other user is accepting challenge
                    self.send(text_data=json.dumps(text_data))
        elif not self.is_spectator() and text_data['response'] == 'reject':
            if self.player_color == text_data['player_color']:  # self.player == text_data['challenged']:
                # Challenge rejected
                async_to_sync(self.channel_layer.group_send)(
                    self.game_group_name, {'type': 'game_message',
                                    'contents': text_data,
                                    'channel_name': self.channel_name,
                                    'donotsend': True
                                    }
                )
                self.send(text_data=json.dumps(text_data))
            else:
                self.send(text_data=json.dumps(text_data))

    def perform_action(self, text_data, check_active_player=True, make_updates=True):
        if make_updates:
            # Check if board logic and DB are up to date
            self.game.refresh_from_db()
            if not self.board_logic_matches_db():
                print('Board logic does not match DB')
                print('Board logic FEN', self.board_logic.partial_FEN())
                print('DB FEN', self.game.FEN().replace(' ', ''))
                self.reset_board_logic_from_db()

        # Check if a player has run out of time
        self.check_time_out()

        # Perform action
        try:
            if text_data['action'] == 'request_board_state':
                self.send_board_state()
            elif text_data['action'] == 'PGN':
                self.send_PGN()
            elif text_data['action'] == 'acknowledge_connection':
                self.acknowledge_connection(text_data)
            elif text_data['action'] == 'request_pawn_moves':
                print('Requesting pawn moves...', text_data)
                self.send_pawn_moves(text_data['player_color'])
            elif text_data['action'] == 'place_fence':
                self.place_fence(text_data, check_active_player, make_updates)
            elif text_data['action'] == 'move_pawn':
                self.move_pawn(text_data, check_active_player, make_updates)
            elif text_data['action'] == 'game_over':
                self.game_over(text_data)
            elif text_data['action'] == 'abort':
                self.abort(text_data)
            elif text_data['action'] == 'resign':
                self.resign(text_data)
            elif text_data['action'] == 'draw_offer':
                self.offer_draw(text_data)
            elif text_data['action'] == 'draw_reject':
                self.offer_draw(text_data)
            elif text_data['action'] == 'draw_accept':
                self.accept_draw(text_data)
            elif text_data['action'] == 'challenge_rematch':
                self.propose_challenge(text_data)
            elif text_data['action'] == 'challenge_response':
                self.respond_challenge(text_data)

        except InvalidPlayer as e:
            print(e)

    def game_message(self, contents_dict):
        # Receive message from group
        print(self.player_color, ': message received from group: ', contents_dict)
        text_data = contents_dict['contents']

        # if self.player_color != text_data['player_color']:  # Message sent by opponents consumer
        if self.channel_name != contents_dict['channel_name']:
            # Update game logic. Sending message to own player in case it has multiple consumers
            self.perform_action(text_data, check_active_player=False, make_updates=False)

        # Send message to websocket
        if not 'donotsend' in contents_dict or not contents_dict['donotsend']:
            if not 'game_id' in text_data:  # In case of challenge acceptal, game ID changes to new game 
                text_data['game_id'] = self.game.game_id
            self.send(text_data=json.dumps(text_data))
