import socket
# from websockets.sync.client import connect
import threading
import bisect  # https://stackoverflow.com/questions/8024571/insert-an-item-into-sorted-list-in-python
import os
# import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from collections import defaultdict
import argparse
import asyncio

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quoridor.settings")
import django

django.setup()
from game.game_utils import create_game, has_active_game
from game.time_controls import time_control
# from websocket import create_connection
# from websockets.asyncio.client import connect
import websockets
import json

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from game.models import UserDetails, Player

from pyquoridor.board import Board
from pyquoridor.utils import print_board
from pyquoridor.exceptions import GameOver
from bot.simple_bot import perform_action
import numpy as np
import time

# Add argument
parser = argparse.ArgumentParser()
parser.add_argument('--server_ip', type=str, default='127.0.0.1')
parser.add_argument('--protocol', type=str, default='wss')
parser.add_argument('--max_concurrent_bots', default=16)
parser.add_argument('--bind_port', type=int, default=9998)
args = parser.parse_args()

async def closing_send(channel_layer, channel, message):
    # Ref: https://github.com/django/channels_redis/issues/332#issuecomment-1400908091
    await channel_layer.send(channel, message)
    await channel_layer.close_pools()

def send_match_details(client, game_id):
    # Send details back...
    text_data = {
        'action': 'match_details',
        'game_id': game_id
    }
    message = {
        'type': 'matchmaking_message',
        'contents': text_data
    }

    channel_layer = get_channel_layer()
    async_to_sync(closing_send)(channel_layer, client['channel_name'], message)  # TODO: Convert to asyncronous???

def handle_match(client, bot_username):
    game = create_game(client['username'],
                       bot_username,
                       player_color='random',
                       time=client['time'],
                       increment=client['increment'])
    print('Game created! Id', game.game_id, client['username'], bot_username)
    send_match_details(client, game.game_id)
    return game

def async_play_game(protocol, server_ip, game_id, bot_username, bot_token, bot_color, active_username):
    asyncio.run(play_game(protocol, server_ip, game_id, bot_username,  bot_token, bot_color, active_username))

def simple_bot_parameters(bot_username):
    parameters = {
        'move_prob': 0.5,
        'min_turn_until_fence': 4,
        'min_best_fence_value': -3,
        'copy_prob': 0
    }
    lowercase_bot_username = bot_username.lower()
    if 'wall' in lowercase_bot_username or 'fence' in lowercase_bot_username:
        parameters['move_prob'] = 0.2
        parameters['min_turn_until_fence'] = 2
        parameters['min_best_fence_value'] = -3
    elif 'rabbit' in lowercase_bot_username or 'pawn' in lowercase_bot_username or 'sprint' in lowercase_bot_username:
        parameters['move_prob'] = 0.8
        parameters['min_turn_until_fence'] = 6
        parameters['min_best_fence_value'] = -5
    elif 'block' in lowercase_bot_username:
        parameters['move_prob'] = 0.3
        parameters['min_turn_until_fence'] = 4
        parameters['min_best_fence_value'] = -7
    elif 'maze' in lowercase_bot_username:
        parameters['move_prob'] = 0.4
        parameters['min_turn_until_fence'] = 4
        parameters['min_best_fence_value'] = -4
    elif 'zugswang' in lowercase_bot_username or 'troll' in lowercase_bot_username:
        parameters['copy_prob'] = 1

    return parameters


async def play_game(protocol, server_ip, game_id, bot_username, bot_token, bot_color, active_username):
    parameters = simple_bot_parameters(bot_username)
    print(f'Bot ({bot_username}) parameters:', parameters)

    # Select from available bots
    uri = f'{protocol}://{server_ip}/ws/game/{game_id}/?token={bot_token}'
    origin='https://playquoridor.online'  # Without origin, when using HTTPS, the connection is refused (CRSF_TRUSTED_ORIGINS: https://docs.djangoproject.com/en/5.1/ref/settings/#csrf-trusted-origins)
    print(f"Connecting to {uri} ...")
    async with websockets.connect(uri, origin=origin) as websocket:
        message = {
            'action': 'request_board_state',
            'player_color': bot_color
        }
        await websocket.send(json.dumps(message))

        # While loop to keep the game running
        board = Board()
        time.sleep(1)
        last_action = 'move_pawn'
        try:
            while not board.game_finished():
                response = await websocket.recv()
                # print(f"Game response: {response}", 'Current player:', board.current_player())
                time.sleep(np.random.rand() * 0.5)

                data = json.loads(response)
                if data['action'] == 'FEN':
                    # TODO: Is it necessary to update the board?
                    pass
                elif data['action'] == 'place_fence':
                    orientation = data['wall_type']
                    row = data['row']
                    col = data['col']
                    if data['player_color'] != bot_color:  # Only update board when opponent plays
                        board.place_fence(row=row, col=col, orientation=orientation)
                        last_action = 'place_fence'
                elif data['action'] == 'move_pawn':
                    row = data['target_row']
                    col = data['target_col']
                    player = data['player_color']
                    if data['player_color'] != bot_color: # Only update board when opponent plays
                        board.move_pawn(player, target_row=row, target_col=col)
                        last_action = 'move_pawn'
                elif data['action'] == 'draw_offer':
                    message = {'action': 'draw_reject'}
                elif data['action'] == 'game_over':
                    break

                # Make move if it's the bot's turn
                # print('Current player:', board.current_player(), 'bot_color:', bot_color, active_username)
                if board.current_player() == bot_color:
                    # if active_username == bot_username:
                    board, action_details = perform_action(board, bot_color, last_action, **parameters)
                    message = action_details
                    # print('Bot action:', message)
                    # print_board(board)
                    await websocket.send(json.dumps(message))
        except GameOver as e:
            print(f"Game over: {e}")

if __name__ == '__main__':
    bot_usernames = []

    # Start server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((args.server_ip, args.bind_port))
    server.listen()

    while True:
        client, addr = server.accept()
        
        # Get details
        config_str = client.recv(1024).decode()
        config_split = config_str.split('/')
        request_type = config_split[0]
        username = config_split[1]
        elo = float(config_split[2])  # Potentially other details...
        elo_threshold = float(config_split[3])  # Unused
        channel_name = config_split[4]
        client = {
            'username': username,
            'elo': elo,
            'elo_threshold': elo_threshold,
            'client': client,
            'channel_name': channel_name,
            'time': int(config_split[5]),  # Time in minutes
            'increment': int(config_split[6])  # Increment in seconds
        }

        if has_active_game(username):
            print(f"ERROR: {username} already has an active game")
            continue

        # Retrieve users from database corresponding to bot username set
        bot_uds = UserDetails.objects.filter(bot=True)

        available_bot_uds = []
        busy_bot_count = 0
        for bot_ud in bot_uds:
            if not has_active_game(bot_ud.user.username):
                available_bot_uds.append(bot_ud)
            else:
                busy_bot_count += 1
        print('Available bots:', available_bot_uds, 'Busy bots:', busy_bot_count)

        if len(available_bot_uds) > 0 and busy_bot_count < args.max_concurrent_bots:
            # Choose bot
            control = time_control(60*client['time'], client['increment'])
            rating_diffs = []
            for bot_ud in available_bot_uds:
                R = bot_ud.get_rating(control)
                rating_diff = abs(client['elo'] - R.rating)
                rating_diffs.append(rating_diff)
            bot_idx = np.argmin(rating_diffs)

            # Create game
            bot_user = available_bot_uds[bot_idx].user
            bot_username = bot_user.username
            bot_token = Token.objects.get(user=bot_user)
            game = handle_match(client, bot_username)
            bot_color = game.player_set.get(user__username=bot_username).player_color
            active_username = bot_username if bot_color == 'white' else client['username']

            # async_play_game(args.protocol, args.server_ip, game.game_id, bot_username, bot_token, bot_color, active_username)
            threading.Thread(target=async_play_game, args=(args.protocol, args.server_ip, game.game_id, bot_username, bot_token, bot_color, active_username)).start()
            # threading.Thread(target=handle_client, args=(client,)).start()