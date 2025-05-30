import socket
# from websockets.sync.client import connect
import threading
import bisect  # https://stackoverflow.com/questions/8024571/insert-an-item-into-sorted-list-in-python
import os
# import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from collections import defaultdict

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quoridor.settings")
import django

django.setup()

from game.game_utils import create_game
import time

PORT = 8000


# Run matchmaking script from root folder with: python -m matchmaking.matchmaking_master matchmaking_master.py

# Ref: https://www.youtube.com/watch?v=_08lsRxqnm4&t=513s
class KeyWrapper:
    # Ref: https://stackoverflow.com/questions/27672494/how-to-use-bisect-insort-left-with-a-key
    def __init__(self, iterable, key):
        self.it = iterable
        self.key = key

    def __getitem__(self, i):
        return self.key(self.it[i])

    def __len__(self):
        return len(self.it)


def find_lt(a, x, key=None, **kwargs):
    # Find rightmost less than x
    # i = bisect.bisect_left(a, x, key=key)
    i = bisect.bisect_left(KeyWrapper(a, key=key), x['elo'], **kwargs)
    if i:
        return i - 1, a[i - 1]
    raise ValueError

def valid_match(client_1, client_2):
    rating_diff = abs(client_1['elo'] - client_2['elo'])
    within_thresholds = rating_diff <= client_1['elo_threshold'] and rating_diff <= client_2['elo_threshold']
    return client_1['username'] != client_2['username'] and within_thresholds


async def closing_send(channel_layer, channel, message):
    # Ref: https://github.com/django/channels_redis/issues/332#issuecomment-1400908091
    await channel_layer.send(channel, message)
    await channel_layer.close_pools()


def send_match_details(client_1, client_2, game_id):
    # Send details back...
    text_data = {
        'action': 'match_details',
        'game_id': game_id
    }
    message = {
        'type': 'matchmaking_message',
        'contents': text_data
    }
    # await channel_layer.send(client_1['channel_name'], message)
    # await channel_layer.send(client_2['channel_name'], message)

    channel_layer = get_channel_layer()
    async_to_sync(closing_send)(channel_layer, client_1['channel_name'], message)  # TODO: Convert to asyncronous???

    channel_layer = get_channel_layer()
    async_to_sync(closing_send)(channel_layer, client_2['channel_name'], message)


def removed_from_pool_message(client):
    text_data = {
        'action': 'removed_from_pool',
        'bot_fallback': client['bot_fallback'],
        'username': client['username'],
        'time': client['time'],
        'increment': client['increment']
    }
    message = {
        'type': 'matchmaking_message',
        'contents': text_data
    }
    channel_layer = get_channel_layer()
    async_to_sync(closing_send)(channel_layer, client['channel_name'], message)

def handle_match(client_1, client_2, time, increment, rated=True):
    print('Handling match...', client_1, client_2)

    # TODO: Check if there's a history of games between the two players, and choose color accordingly?
    game = create_game(client_1['username'],
                       client_2['username'],
                       player_color='random',
                       time=time,
                       increment=increment,
                       rated=rated,
                       player_session_key=client_1['session_key'] if client_1['username'].lower() == 'anonymous' else None,
                       opponent_session_key=client_2['session_key'] if client_2['username'].lower() == 'anonymous' else None
    )
    print('Game created! Id', game.game_id, client_1['username'], client_2['username'])
    # client_1['client'].send(str(game.game_id).encode())  # .send(f'game id, opponent ELO {client_2["elo"]}'.encode())
    # client_2['client'].send(str(game.game_id).encode())  # .send(f'game id, opponent ELO {client_1["elo"]}'.encode())

    send_match_details(client_1, client_2, game.game_id)


def remove_from_pool_logic(client, anonymous=False):
    print(f'Removing {anonymous} client from pool logic...', client)
    if anonymous:
        remove_client_anonymous(client)
    else:
        remove_client(client)
    removed_from_pool_message(client)


def match_client(client, patience=5):
    # Get list of clients by time control
    connected_clients = connected_clients_by_time[f'{client["time"]}+{client["increment"]}']

    # Match client
    N = len(connected_clients)
    print(f'Handling client... Number of connected clients in list {N}')
    matched_client = None
    if N > 0:
        # TODO: All this code is likely not thread-safe... Think about:
        #  * Whether this is ok
        #  * Whether master should handle this
        #  * Whether it's better to copy connected_clients
        #  * Whether it's better to use a lock
        try:
            i, _ = find_lt(connected_clients, client, key=lambda x: x['elo'])  # TODO: key=lambda x: client[1]
        except ValueError:
            i = 0

        # Check middle candidate
        min_rating_diff = float('inf')
        candidate_client = connected_clients[i]
        if valid_match(client, candidate_client):
            matched_client = candidate_client
            # min_rating_diff = abs(elo - matched_client[1])
            min_rating_diff = abs(client['elo'] - matched_client['elo'])

        # Check left and right neighbours (interleaving)
        left_pointer = i - 1
        right_pointer = i + 1
        continue_right = right_pointer < N
        continue_left = left_pointer >= 0
        while continue_left or continue_right:
            # Check client on the right
            if continue_right:
                candidate_client = connected_clients[right_pointer]
                rating_diff = abs(client['elo'] - candidate_client['elo'])

                # Match is valid is rating_diff falls within both clients thresholds
                # valid_match = rating_diff <= elo_threshold and rating_diff <= matched_client[2]
                if rating_diff < min_rating_diff and valid_match(client, candidate_client):
                    matched_client = candidate_client
                    min_rating_diff = rating_diff
                    right_pointer += 1
                    continue_right = right_pointer < N
                else:
                    continue_right = False

            # Check client on the right
            if continue_left:
                candidate_client = connected_clients[left_pointer]
                rating_diff = abs(client['elo'] - candidate_client['elo'])

                # Match is valid is rating_diff falls within both clients thresholds
                # valid_match = rating_diff <= elo_threshold and rating_diff <= matched_client[2]
                if rating_diff < min_rating_diff and valid_match(client, candidate_client):
                    matched_client = candidate_client
                    min_rating_diff = rating_diff
                    left_pointer -= 1
                    continue_left = left_pointer >= 0
                else:
                    continue_left = False

    # Check if valid match
    if matched_client is not None:
        # threading.Thread(target=handle_match, args=(client, matched_client)).start()
        handle_match(client, matched_client, client['time'], client['increment'])
        remove_client(matched_client)
        remove_client_anonymous(matched_client)
        print(
            f"Match found! ELO1: {client['elo']}, Thr1: {client['elo_threshold']}. ELO2: {matched_client['elo']}, Thr2: {matched_client['elo_threshold']}")
    else:
        print('Match not found, inserting')

        # Not found, insert
        with threading.Lock():  # Using lock to ensure list is sorted
            insert_index = bisect.bisect_right(KeyWrapper(connected_clients, key=lambda x: x['elo']), client['elo'])
            connected_clients.insert(insert_index, client)
            connected_usernames_set.add(client['username'])
        
        # TODO: This is really hacky... Spawns a thread to automatically remove client after 5 seconds
        # threading.Thread(target=remove_from_pool_logic, args=(client,)).start()
        timer = threading.Timer(patience, remove_from_pool_logic, args=(client, False))
        timer.start()


def remove_client(client):
    print('Removing client ', client['username'])
    # del connected_clients[i]
    # Thread safe? https://web.archive.org/web/20201108091210/http://effbot.org/pyfaq/what-kinds-of-global-value-mutation-are-thread-safe.htm
    # connected_clients.pop(i)
    with threading.Lock():  # Using lock to ensure list is sorted
        for connected_clients in connected_clients_by_time.values():
            N = len(connected_clients)
            if N > 0:
                remove_idx = 0
                while remove_idx < N - 1 and connected_clients[remove_idx]['username'] != client['username']:
                    remove_idx += 1
                if connected_clients[remove_idx]['username'] == client['username']:
                    del connected_clients[remove_idx]
                    connected_usernames_set.remove(client['username'])
        # i = bisect.bisect_right(KeyWrapper(connected_clients, key=lambda x: x['elo']), client['elo'])
        # This is O(n)... but should be thread safe
        # connected_clients.remove(client)

def valid_anonymous_match(client_1, client_2):
    if client_1['username'].lower() == 'anonymous' and client_2['username'].lower() == 'anonymous':
        return client_1['session_key'] != client_2['session_key']
    else:
        return client_1['username'] != client_2['username']

def match_client_anonymous(client, patience=5):
    print('Requesting anonymous match...', client)
    # Get list of clients by time control
    connected_clients = connected_clients_anonymous

    # Match client
    N = len(connected_clients)
    print(f'Handling client... Number of connected clients in anonymous list {N}')
    matched_client = None
    if N > 0:
        # TODO: All this code is likely not thread-safe... Think about:
        #  * Whether this is ok
        #  * Whether master should handle this
        #  * Whether it's better to copy connected_clients
        #  * Whether it's better to use a lock
        for i in range(N):
            candidate_client = connected_clients[i]
            if valid_anonymous_match(client, candidate_client): # client['username'].lower() != 'anonymous' and client['username']:
                matched_client = candidate_client
                break        

    # Check if valid match
    if matched_client is not None:
        # threading.Thread(target=handle_match, args=(client, matched_client)).start()
        handle_match(client, matched_client, client['time'], client['increment'], rated=False)
        remove_client(matched_client)
        if matched_client['username'] == 'anonymous':
            remove_client_anonymous(matched_client)
        print(
            f"Match found! ELO1: {client['elo']}, Thr1: {client['elo_threshold']}. ELO2: {matched_client['elo']}, Thr2: {matched_client['elo_threshold']}")
    else:
        print('Match not found, inserting ', client)

        connected_clients.append(client)
        connected_anonymous_keys_set.add(client['session_key'])  # Store anonymous key so that it cannot be added twice / play again themselves
        
        timer = threading.Timer(patience, remove_from_pool_logic, args=(client, True))
        timer.start()

def remove_client_anonymous(client):
    print('Removing client ', client['username'])
    with threading.Lock():  # Using lock to ensure list is sorted
        for connected_clients in connected_clients_anonymous:
            N = len(connected_clients_anonymous)
            if N > 0:
                remove_idx = 0
                while remove_idx < N - 1 and connected_clients_anonymous[remove_idx]['session_key'] != client['session_key']:
                    remove_idx += 1
                if connected_clients_anonymous[remove_idx]['session_key'] == client['session_key']:
                    del connected_clients_anonymous[remove_idx]
                    connected_anonymous_keys_set.remove(client['session_key'])
    print('Length of anonymous clients:', len(connected_clients_anonymous))

# Every client has an ELO threshold
def handle_client(client):
    config_str = client.recv(1024).decode()
    config_split = config_str.split('/')

    print('Received: ', config_str)
    request_type = config_split[0]
    username = config_split[1]
    elo = None if config_split[2] == 'None' else float(config_split[2])  # Potentially other details...
    elo_threshold = None if config_split[3] == 'None' else float(config_split[3])
    channel_name = config_split[4]
    t = None if len(config_split) < 6 or config_split[5] == 'None' else int(config_split[5])
    increment = None if len(config_split) < 7 or config_split[6] == 'None' else int(config_split[6])
    session_key = None if len(config_split) < 8 or config_split[7] == 'None' else config_split[7]
    bot_fallback = True  # TODO: Let user decide?
    client_details = {
        'username': username,
        'elo': elo,
        'elo_threshold': elo_threshold,
        'client': client,
        'bot_fallback': bot_fallback,
        'channel_name': channel_name,
        'time': t,  # Time in minutes
        'increment': increment, # Increment in seconds
        'session_key': session_key # Session key for anonymous users
    }
    
    if request_type == 'match_client' and client_details['username'] not in connected_usernames_set:
        match_client(client_details)
    elif request_type == 'remove_client':
        print('Removing client ...')
        remove_client(client_details)
    elif request_type == 'match_anonymous' and client_details['session_key'] not in connected_anonymous_keys_set:
        print('Placing client to anonymous queue...')
        match_client_anonymous(client_details)
    elif request_type == 'remove_anonymous':
        print('Removing client from anonymous queue...')
        remove_client_anonymous(client_details)


if __name__ == '__main__':
    # New clients are appended in the end, so list is sorted by time
    # connected_clients = []  # Lists are thread safe: https://stackoverflow.com/questions/6319207/are-lists-thread-safe
    connected_clients_by_time = defaultdict(lambda: [])
    connected_usernames_set = set()  # Set of clients to prevent adding same client to list?
    connected_clients_anonymous = []
    connected_anonymous_keys_set = set()  # Set of anonymous session keys to prevent adding same client to list

    # Start server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('127.0.0.1', 9999))
    server.listen()

    while True:
        client, addr = server.accept()
        handle_client(client)
        # threading.Thread(target=handle_client, args=(client,)).start()
