from .models import QuoridorGame, Player
from django.contrib.auth.models import User
import threading
from datetime import timedelta
import random


def has_active_game(player_username):
    try:
        latest_player = Player.objects.filter(user__username=player_username, game__abort=False).latest('game__game_time')
        return not latest_player.game.ended()
    except Player.DoesNotExist:
        return False
    

def check_rating_integrity_or_update(player_username):
    try:
        # latest_player = Player.objects.filter(user__username=player_username, game__abort=False, game__rated=True).latest('game__game_time')
        latest_player = Player.objects.filter(user__username=player_username, game__rated=True, game__winning_player=None, game__draw=False, game__abort=False).latest('game__game_time')
        
        if not latest_player.ratings_updated():
            print('WARNING: Player ratings were not updated in the last game. Updating now')
            game = latest_player.game
            if not game.ended():
                print(f"ERROR: Last game of player {player_username} didn't finish")
                # raise Exception()
            else:
                winner_username = game.winner_username()
                game.update_rating(latest_player.player_color, winner_username, game.draw)
    except Player.DoesNotExist:
        pass


def abort_game_if_not_started(game_id):
    try:
        game = QuoridorGame.objects.get(pk=game_id)
        if game.number_of_moves() < 2:
            print(f"Aborting game {game_id} because it didn't start. Number of moves", game.number_of_moves())
            game.abort = True
            game.save()
    except QuoridorGame.DoesNotExist:
        pass

def create_game(player_username, opponent_username, player_color, time=None, increment=None):
    # Important: Assumes players are not currently playing a game

    # Get parameters
    player = User.objects.get(username=player_username)  # request.user  # .username
    opponent = User.objects.get(username=opponent_username)

    # Assign player colors
    if player_color == 'random':
        color_index = random.randint(0, 1)
        player_color = ['white', 'black'][color_index]

    if player_color == 'white':
        player_white = player
        player_black = opponent
    elif player_color == 'black':
        player_white = opponent
        player_black = player

    # Create game
    if time is not None:
        time = time * 60  # Convert time to seconds
    game = QuoridorGame(total_time_per_player=time,
                        increment=increment)
    game.save()

    # If game is new, check that players have an up-to-date rating
    check_rating_integrity_or_update(player_username)
    check_rating_integrity_or_update(opponent_username)

    # Check that players have an existing rating for this time control
    control = game.time_control()
    player_white.userdetails.check_or_create_rating(control)
    player_black.userdetails.check_or_create_rating(control)

    # Create players
    R_white = player_white.userdetails.get_rating(control)
    R_black = player_black.userdetails.get_rating(control)

    player_white = game.player_set.create(user=player_white, row=0, col=4, color=0,
                                          rating=R_white.rating,
                                          deviation=R_white.deviation,
                                          volatility=R_white.volatility)
    player_black = game.player_set.create(user=player_black, row=8, col=4, color=1,
                                          rating=R_black.rating,
                                          deviation=R_black.deviation,
                                          volatility=R_black.volatility)
    player_white.save()
    player_black.save()

    # Automatic abortion of game if not started
    timer = threading.Timer(120, abort_game_if_not_started, args=(game.game_id,))
    timer.start()  # Start countdown

    return game
