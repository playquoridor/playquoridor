import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from game.game_utils import create_game
from game.models import UserDetails
from django.db.models import F
from game.models import Player


def user_has_active_game(username):
    # Check if user has an active game. If yes, automatically reject challenge
    # (allowing one active game at a time to prevent concurrent rating updates)
    return Player.objects.filter(user__username=username,
                                 game__winning_player=None,
                                 game__abort=False,
                                 game__draw=False).exists()


# Send to single channel layer: https://channels.readthedocs.io/en/stable/topics/channel_layers.html#single-channels
# Perhaps use cookies?
class ChallengeConsumer(WebsocketConsumer):
    def connect(self):
        self.target_username = self.scope['url_route']['kwargs']['username']
        self.group_name = f'challenge_{self.target_username}'

        # Get player information
        self.source_username = self.scope['user'].username

        # Update user: online
        if self.source_username == self.target_username:
            self.update_user_incr(self.scope['user'])

        # Join game group
        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name
        )

        # Accept the connection
        # TODO: Important! Limit the number of connections per target user!!!
        #  (otherwise we send too many irrelevant messages)
        self.accept()

        # Dummy message: For some reason, the first message to the client is lost
        self.send(text_data=json.dumps({'action': 'dummy'}))

    @staticmethod
    def update_user_incr(user):
        ud = UserDetails.objects.filter(pk=user.userdetails.pk)
        ud.update(online=F('online') + 1)

    @staticmethod
    def update_user_decr(user):
        UserDetails.objects.filter(pk=user.userdetails.pk).update(online=F('online') - 1)

    def disconnect(self, close_code):
        if self.source_username == self.target_username:
            self.update_user_decr(self.scope['user'])

        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name, self.channel_name
        )

    def propose_challenge(self, text_data):
        assert self.source_username != self.target_username
        text_data['challenger'] = self.source_username

        # Check if user has an active game. If yes, automatically reject challenge
        # (allowing one active game at a time to prevent concurrent rating updates)
        if user_has_active_game(self.source_username):
            text_data = {
                'action': 'challenge_response',
                'response': 'reject'
            }
            self.send(text_data=json.dumps(text_data))
        else:
            assert 'challenger_color' in text_data or 'challenged_color' in text_data
            if 'challenged_color' in text_data:
                text_data['player_color'] = text_data['challenged_color']
            elif text_data['challenger_color'] == 'white':
                text_data['player_color'] = 'black'
            elif text_data['challenger_color'] == 'black':
                text_data['player_color'] = 'white'
            else:
                text_data['player_color'] = 'random'

            # Time
            """
            t, increment = text_data['time'].split('+')
            text_data['increment'] = increment
            text_data['time'] = t
            """
            print('User ', self.source_username, 'sending challenge...')

            async_to_sync(self.channel_layer.group_send)(
                self.group_name, {'type': 'challenge_message',
                                  'contents': text_data}
            )

    def respond_challenge(self, text_data):
        # TODO: Important game details should match between both players...
        #  (need avoid injecting e.g. different times when responding a challenge)
        if text_data['response'] == 'accept':  # Challenge accepted
            time = int(text_data['time']) if 'time' in text_data else None
            increment = int(text_data['increment']) if 'increment' in text_data else None
            game = create_game(player_username=self.target_username,
                               opponent_username=text_data['challenger'],
                               player_color=text_data['player_color'],
                               time=time,
                               increment=increment)
            text_data['game_id'] = game.game_id
        else:
            # Challenge rejected
            print('Challenge rejected')

        print('Sending back challenge response to all users...', self.source_username, text_data)
        async_to_sync(self.channel_layer.group_send)(
            self.group_name, {'type': 'challenge_message',
                              'contents': text_data}
        )

    def receive(self, text_data):
        # Receive message from websocket
        print('Message received from websocket: ', text_data, self.source_username)
        text_data = json.loads(text_data)
        print('Contents', text_data)
        if text_data['action'] == 'challenge_proposal':
            self.propose_challenge(text_data)
        elif text_data['action'] == 'challenge_rematch':
            self.propose_challenge(text_data)
        elif text_data['action'] == 'challenge_response':
            self.respond_challenge(text_data)

    def challenge_message(self, contents_dict):
        # Receive message from group
        print('Message received from group: ', contents_dict, self.source_username)
        text_data = contents_dict['contents']
        if text_data['action'] == 'challenge_proposal' or text_data['action'] == 'challenge_rematch':
            # If consumer corresponds to challenged user, send message
            if self.source_username == self.target_username:
                # Check if user has an active game. If yes, automatically reject challenge
                # (allowing one active game at a time to prevent concurrent rating updates)
                if user_has_active_game(self.source_username):
                    text_data = {
                        'action': 'challenge_response',
                        'challenger': text_data['challenger'],
                        'response': 'reject'
                    }
                    # TODO: Send reason? e.g. with game ID?
                    self.respond_challenge(text_data)
                else:
                    # Send message to websocket
                    self.send(text_data=json.dumps(text_data))
        elif text_data['action'] == 'challenge_response':
            # If consumer corresponds to challenger user, send message
            # if self.source_username == text_data['challenger']:
            print('Sending back challenge response...', self.source_username)

            if text_data['response'] == 'accept' or \
                    (text_data['response'] != 'accept' and self.source_username == text_data['challenger']):
                # If accepted, send message to both consumers with game id. If rejected, only send message to challenger
                # Send message to websocket
                self.send(text_data=json.dumps(text_data))
