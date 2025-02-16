# game/views.py
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from .models import QuoridorGame, Player
from .game_utils import create_game
from django.db.models import \
    Q  # Ref: https://docs.djangoproject.com/en/dev/topics/db/queries/#complex-lookups-with-q-objects
from quoridor.views import active_game_context
import logging

logger = logging.getLogger(__name__)

# Django authentication tutorial: https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Authentication


#####################
#    Game views     #
#####################
# @login_required
def game(request, game_id):
    game = get_object_or_404(QuoridorGame, pk=game_id)
    player_username = request.user.username

    players = game.player_set.all()
    opponent = None
    player_color = None
    for p in players:
        if player_username == p.username:
            player = p
            player_color = p.player_color
            player_rating = p.rating
        else:
            opponent = p
            opponent_rating = p.rating
        if p.player_color == 'white':
            player_white = p
            rating_white = p.rating
        elif p.player_color == 'black':
            player_black = p
            rating_black = p.rating

    if player_color is None:  # Spectator
        player = player_white
        player_rating = rating_white
        opponent = player_black
        opponent_rating = rating_black

    # Check details match
    # if player_color is None:
    #    raise ValueError('Player not matching database')
    time_end = None
    if game.time_end is not None:
        time_end = game.time_end.strftime('%Y/%m/%d %H:%M:%S')

    context = {'game': game,
            'player': player,
            'opponent': opponent,
            'player_username': player.username,
            'opponent_username': opponent.username,
            'player_color': player_color,
            'player_rating': int(player_rating),
            'opponent_rating': int(opponent_rating),
            'time_end': time_end,
            'flip_board': player_color == 'black'}
    context = {**context, **active_game_context(request)}

    return render(request, "game/game.html", context=context)


@login_required
def play(request):
    """
    Creates game
    This view starts a new game and redirects to .../game/<game_id>
    TODO: Multiplayer
    """

    # Create game
    game = create_game(player_username=request.user.username,
                       opponent_username=request.POST['opponent'],
                       player_color=request.POST['player_color'])

    return HttpResponseRedirect(reverse('game:game', args=(game.game_id,)))


# @login_required
def join(request):
    """
    This joins a game and redirects to .../game/<game_id>
    """
    # Get parameters
    player = request.user.username  # .POST['player']
    game_id = request.POST['game_id']
    print('Joining game ID:', game_id)

    # Redirect to game
    return HttpResponseRedirect(reverse('game:game', args=(game_id,)))


"""
Login views
def login_view(request):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        # Redirect to a success page.
        ...
    else:
        # Return an 'invalid login' error message.
        ...


def logout_view(request):
    logout(request)
    # Redirect to a success page.
"""
