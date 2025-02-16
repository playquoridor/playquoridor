import random
import string

# Note: Assuming database is case sensitive
ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits


# Create game ID
def create_game_id(k=12):
    # https://stackoverflow.com/questions/13484726/safe-enough-8-character-short-unique-random-string
    game_id = ''.join(random.choices(ALPHABET, k=k))
    return game_id


if __name__ == '__main__':
    game_id = create_game_id()
    print(game_id)
