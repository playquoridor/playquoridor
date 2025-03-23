import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from game.models import Player
from game.time_controls import time_control
import socket
import time


class MatchMakingConsumer(WebsocketConsumer):
    def connect(self):
        # Get player information
        self.username = self.scope['user'].username

        self.rating = None  # Determined in request_match
        self.rating_threshold = 300
        self.disconnected = False
        # self.connection_type = self.scope['url_route']['kwargs']['connection_type']

        # if self.connection_type == 0:  # User connecting directly via websocket
        self.group_name = f'matchmaking_{self.username}'
        # else:  # Matchmaking server connecting with consumer
        #     self.group_name = self.scope['url_route']['kwargs']['group_name']

        # Join group
        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name
        )
        print('Matchmaking ', self.username)

        # Accept the connection
        # TODO: Important! Limit the number of connections per target user!!!
        #  (otherwise we send too many irrelevant messages)
        self.accept()

        # Dummy message: For some reason, the first message to the client is lost
        self.send(text_data=json.dumps({'action': 'dummy'}))

    def request_match(self, text_data, timeout=30):
        # Check if player has active games. Important: assumes only last game can be active (!)
        # latest_player = Player.objects.filter(user__username=self.username, game__ended=False)
        has_games = True
        try:
            latest_player = Player.objects.filter(user__username=self.username).latest('game__game_time')
        except Player.DoesNotExist:
            has_games = False

        # Check if player has active games
        if has_games and not latest_player.game.ended:
            game = latest_player.game
            player_set = game.player_set.all()
            text_data = {
                'action': 'matchmaking_failed',
                'reason': 'Game already in progress',
                'game_id': game.game_id,
                'white_player_username': player_set[0].username,
                'black_player_username': player_set[1].username,
                'white_player_rating': int(player_set[0].rating),
                'black_player_rating': int(player_set[1].rating)
            }
            self.send(text_data=json.dumps(text_data))
        else:
            try:
                # Find match or join matchmaking pool
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect(('127.0.0.1', 9999))
                client.settimeout(timeout)

                t = text_data['time']
                increment = text_data["increment"]
                control = time_control(60 * t, increment)
                self.scope['user'].userdetails.check_or_create_rating(control)
                rating = self.scope['user'].userdetails.get_rating(control).rating
                # print('User:', self.scope['user'], 'Rating: ', rating, 'Control', control)
                self.rating = rating

                message = f'match_client/{self.username}/{rating}/{self.rating_threshold}/{self.channel_name}/{t}/{increment}'
                client.send(message.encode())
            except ConnectionRefusedError as e:
                print('Matchmaking failed', e)


    def request_bot_match(self, text_data, timeout=30):
        # Check if player has active games. Important: assumes only last game can be active (!)
        # latest_player = Player.objects.filter(user__username=self.username, game__ended=False)
        has_games = True
        game_ended = False
        try:
            latest_player = Player.objects.filter(user__username=self.scope['user'].username, game__abort=False).latest('game__game_time')
            game_ended = latest_player.game.ended()            
        except Player.DoesNotExist:
            has_games = False
        games = [g.game for g in Player.objects.filter(user__username=self.scope['user'].username, game__abort=False)]

        # Check if player has active games
        if has_games and not game_ended:
            game = latest_player.game
            player_set = game.player_set.all()
            text_data = {
                'action': 'matchmaking_failed',
                'reason': 'Game already in progress',
                'game_id': game.game_id,
                'white_player_username': player_set[0].username,
                'black_player_username': player_set[1].username,
                'white_player_rating': int(player_set[0].rating),
                'black_player_rating': int(player_set[1].rating)
            }
            self.send(text_data=json.dumps(text_data))
        else:
            try:
                # Find match or join matchmaking pool
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect(('127.0.0.1', 9998))
                client.settimeout(timeout)

                t = text_data['time']
                increment = text_data['increment']
                control = time_control(60 * t, increment)
                self.scope['user'].userdetails.check_or_create_rating(control)
                rating = self.scope['user'].userdetails.get_rating(control).rating
                self.rating = rating
                
                message = f'match_client/{self.username}/{rating}/{self.rating_threshold}/{self.channel_name}/{t}/{increment}'

                print('TEXT DATA', text_data)
                if 'bot_username' in text_data and 'bot_color' in text_data:
                    message += f'/{text_data["bot_username"]}/{text_data["bot_color"]}'

                client.send(message.encode())
            except ConnectionRefusedError as e:
                print('Matchmaking failed', e)


    def disconnect(self, close_code):
        print('User ', self.username, 'disconnected from matchmaking')
        if not self.disconnected:
            self.cancel_match()
            self.disconnected = True

    def cancel_match(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', 9999))
        message = f'remove_client/{self.username}/{self.rating}/{self.rating_threshold}/{self.channel_name}'
        client.send(message.encode())

    def receive(self, text_data):
        # Receive message from websocket
        print('MATCHMAKING: Message received from websocket: ', text_data, self.username)
        text_data = json.loads(text_data)
        print('Contents', text_data)
        if text_data['action'] == 'request_match':
            self.request_match(text_data)
        elif text_data['action'] == 'request_bot_match':
            self.request_bot_match(text_data)
        # elif text_data['action'] == 'receive_match_details':
        #    self.receive_match_details(text_data)

    def matchmaking_message(self, contents_dict):
        # Receive message from group
        print('MATCHMAKING: Message received from group: ', contents_dict, self.username)
        text_data = contents_dict['contents']
        if text_data['action'] == 'match_details':
            # Send message to websocket
            self.send(text_data=json.dumps(text_data))
        elif text_data['action'] == 'removed_from_pool' and text_data['bot_fallback']:
            self.request_bot_match(text_data)
