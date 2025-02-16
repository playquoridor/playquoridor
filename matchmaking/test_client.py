import socket

if __name__ == '__main__':
    # Player details
    elo = input('Your ELO: ')
    elo_threshold = input('Your ELO threshold: ')
    username = elo

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', 9999))
        message = f'match_client/{username}/{elo}/{elo_threshold}'
        client.send(message.encode())
        print('Match made!', client.recv(1024).decode())

    except KeyboardInterrupt:
        print('Removing client')
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', 9999))
        message = f'remove_client/{username}/{elo}/{elo_threshold}'
        client.send(message.encode())