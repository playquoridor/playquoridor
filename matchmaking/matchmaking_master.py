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


def _valid_match(client_1, client_2):
    _, elo_1, elo_threshold_1 = client_1
    _, elo_2, elo_threshold_2 = client_2
    rating_diff = abs(elo_1 - elo_2)
    valid = rating_diff <= elo_threshold_1 and rating_diff <= elo_threshold_2
    return valid


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


def handle_match(client_1, client_2, time, increment):
    # TODO: Check if there's a history of games between the two players, and choose color accordingly?
    game = create_game(client_1['username'],
                       client_2['username'],
                       player_color='random',
                       time=time,
                       increment=increment)
    print('Game created! Id', game.game_id, client_1['username'], client_2['username'])
    # client_1['client'].send(str(game.game_id).encode())  # .send(f'game id, opponent ELO {client_2["elo"]}'.encode())
    # client_2['client'].send(str(game.game_id).encode())  # .send(f'game id, opponent ELO {client_1["elo"]}'.encode())

    send_match_details(client_1, client_2, game.game_id)


def match_client(client):
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
            print('Index', i)
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
        print(
            f"Match found! ELO1: {client['elo']}, Thr1: {client['elo_threshold']}. ELO2: {matched_client['elo']}, Thr2: {matched_client['elo_threshold']}")
    else:
        print('Match not found, inserting')

        # Not found, insert
        with threading.Lock():  # Using lock to ensure list is sorted
            insert_index = bisect.bisect_right(KeyWrapper(connected_clients, key=lambda x: x['elo']), client['elo'])
            connected_clients.insert(insert_index, client)
            connected_usernames_set.add(client['username'])


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


# Every client has an ELO threshold
def handle_client(client):
    config_str = client.recv(1024).decode()
    config_split = config_str.split('/')

    print('Received: ', config_str)
    request_type = config_split[0]
    username = config_split[1]
    elo = float(config_split[2])  # Potentially other details...
    elo_threshold = float(config_split[3])
    channel_name = config_split[4]
    client = {
        'username': username,
        'elo': elo,
        'elo_threshold': elo_threshold,
        'client': client,
        'channel_name': channel_name
    }

    if request_type == 'match_client' and client['username'] not in connected_usernames_set:
        client['time'] = int(config_split[5])  # Time in minutes
        client['increment'] = int(config_split[6])  # Increment in seconds
        match_client(client)
    elif request_type == 'remove_client':
        print('Removing client ...')
        remove_client(client)

    """
    print(f'Number of connected clients in list {len(connected_clients)}')
    for c in connected_clients:
        print(c['username'])
    """


if __name__ == '__main__':
    # New clients are appended in the end, so list is sorted by time
    # connected_clients = []  # Lists are thread safe: https://stackoverflow.com/questions/6319207/are-lists-thread-safe
    connected_clients_by_time = defaultdict(lambda: [])
    connected_usernames_set = set()
    # TODO: Set of clients to prevent adding same client to list?

    # Start server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('127.0.0.1', 9999))
    server.listen()

    while True:
        client, addr = server.accept()
        handle_client(client)
        # threading.Thread(target=handle_client, args=(client,)).start()
