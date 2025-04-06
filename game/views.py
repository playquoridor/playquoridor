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
    if player_username == '':
        player_username = 'anonymous'
    # print('Player:', player_username)
    # print('Request:', request.session.session_key)

    players = game.player_set.all()
    player_color = None
    opponent = None
    pcolor = None
    ocolor = None
    for p in players:
        if player_username == p.username or (player_username == 'anonymous' and request.session.session_key == p.session_key):
            player = p
            player_color = p.player_color
            player_rating = p.rating
            pcolor = p.player_color
        else:
            opponent = p
            opponent_rating = p.rating
            ocolor = p.player_color
        if p.player_color == 'white':
            player_white = p
            rating_white = p.rating
        elif p.player_color == 'black':
            player_black = p
            rating_black = p.rating
    
    if player_color is None:  # Spectator
        player = player_white
        player_rating = rating_white
        pcolor = 'white'
        opponent = player_black
        opponent_rating = rating_black
        ocolor = 'black'

    # Check details match
    # if player_color is None:
    #    raise ValueError('Player not matching database')
    time_end = None
    if game.time_end is not None:
        time_end = game.time_end.strftime('%Y/%m/%d %H:%M:%S')

    player_username = player.username if player.username != '' else 'anonymous'
    opponent_username = opponent.username if opponent.username != '' else 'anonymous'
    context = {'game': game,
            'player': player,
            'opponent': opponent,
            'pcolor': pcolor,  # Color of player below
            'ocolor': ocolor,  # Color of opponent above
            'player_username': player_username,
            'opponent_username': opponent_username,
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
