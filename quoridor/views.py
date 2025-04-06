# game/views.py
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from django.contrib.auth.views import PasswordChangeView
from game.models import QuoridorGame, Player, UserDetails, Rating
import numpy as np
import random

# Django authentication tutorial: https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Authentication

def active_game_context(request):
    context = {'active_game_exists': False}
    player_username = request.user.username
    if player_username == '':
        player_username = 'Anonymous'

    # If user is authorised, check if game is in progress
    if request.user.is_authenticated:
        try:
            latest_player = Player.objects.filter(user__username=request.user.username,
                                                  game__winning_player=None, game__draw=False, game__abort=False).latest(
                'game__game_time')
            game = latest_player.game
            if not game.ended():  # Game not finished
                opponent = None
                player = None
                player_username_ = None
                opponent_username_ = None
                for p in game.player_set.all():
                    if player_username == p.username or (player_username.lower() == 'anonymous' and request.session.session_key == p.session_key): # p.username == request.user.username:
                        player = p
                        player_username_ = p.username
                    else:
                        opponent = p
                        opponent_username_ = p.username

                if player_username_ == '':
                    player_username_ = 'Anonymous'
                if opponent_username_ == '':
                    opponent_username_ = 'Anonymous'
                context = {
                    'active_game_exists': True,
                    'active_game': game,
                    'active_game_id': game.game_id,
                    'active_game_player': player,
                    'active_game_opponent': opponent,
                    'active_game_player_username': player_username_,
                    'active_game_opponent_username': opponent_username_,
                }
        except Player.DoesNotExist:
            pass
    return context


def top_game_context(request, active_game_id=None):
    # TODO: Consider using cache
    context = {'top_active_game_exists': False, 'top_active_game_ismine': False}

    try:
        # TODO: Can this be achieved with a single query?
        ongoing_games = QuoridorGame.objects.filter(winning_player=None, draw=False, abort=False, move_number__gt=1)
        active_players = []
        active_players_ratings = []
        for game in ongoing_games:
            game_players = game.player_set.all()
            for player in game_players:
                active_players.append(player)
                active_players_ratings.append(player.rating)

        if len(active_players_ratings) > 0:
            # Find top rated player
            top_player_idx = np.argmax(active_players_ratings)
            top_player = active_players[top_player_idx]
            game = top_player.game

            if active_game_id == game.game_id:
                # Top game matches active game
                context = {
                    'top_active_game_exists': True,
                    'top_active_game_ismine': True,
                    'top_active_game_message': 'Your active game is being featured worldwide 🏆'
                }
                pass
            else:
                # Add game details to context
                opponent = None
                player = None
                for p in game.player_set.all():
                    if p.username == top_player.username:
                        player = p
                    else:
                        opponent = p
                context = {
                    'top_active_game_exists': True,
                    'top_active_game_ismine': False,
                    'top_active_game': game,
                    'top_active_game_id': game.game_id,
                    'top_active_game_player': player,
                    'top_active_game_opponent': opponent,
                }
    except QuoridorGame.DoesNotExist:
        pass
    return context


def leaderboard_context(request, k=50):
    # top_rated_user_details = UserDetails.objects.filter(user__is_active=True).order_by('standard_rating')[::-1][:k]
    if len(Rating.objects.all()) == 0:
        top_ratings_bullet = []
        top_ratings_blitz = []
        top_ratings_rapid = []
        top_ratings_standard = []
    else:
        # Select best standard ratings
        top_ratings = Rating.objects.order_by('rating')[::-1][:100]
        # top_rated_user_details = [r.user_details for r in top_ratings]

        top_ratings_bullet = list(filter(lambda r: r.get_time_control() == 'bullet' and r.user_details.user.username.lower() != 'anonymous', top_ratings))[:k]
        top_ratings_blitz = list(filter(lambda r: r.get_time_control() == 'blitz' and r.user_details.user.username.lower() != 'anonymous', top_ratings))[:k]
        top_ratings_rapid = list(filter(lambda r: r.get_time_control() == 'rapid' and r.user_details.user.username.lower() != 'anonymous', top_ratings))[:k]
        # top_ratings_standard = list(filter(lambda r: r.get_time_control() == 'standard', top_ratings))[:k]

    context = {
        # 'top_ratings': top_ratings,
        'top_ratings_bullet': top_ratings_bullet,
        'top_ratings_blitz': top_ratings_blitz,
        'top_ratings_rapid': top_ratings_rapid,
        # 'top_ratings_standard': top_ratings_standard
    }
    return context


def online_users_context(request, k=50):
    ud = UserDetails.objects.filter(online__gt=0).exclude(user__username=request.user.username)
    # online_ratings = Rating.objects.filter(user_details__online__gt=0)
    # print('Online ratings', online_ratings)

    online_users = list(ud)
    if len(online_users) > k:
        online_users = random.sample(list(ud), k)
    context = {
        'online_users_count': ud.count()+1,
        'online_user_details': online_users
    }
    return context


#####################
#    Main views     #
#####################
# @login_required
def index(request):
    # Force session creation (useful for anonymous users)
    if not request.session.session_key:
        request.session.save()

    context = active_game_context(request)
    active_game_id = context['active_game_id'] if 'active_game_id' in context else None
    context = {**context,
               **leaderboard_context(request),
               **top_game_context(request, active_game_id),
               **online_users_context(request)}
    return render(request, 'index.html', context)

def community(request):
    context = active_game_context(request)
    context = {}
    return render(request, 'community.html', context)

#####################
#    Error pages    #
#####################

def handler404(request, template_name="404.html", **kwargs):
    response = render(request, template_name)
    response.status_code = 404
    return response


def handler500(request, template_name="500.html", **kwargs):
    response = render(request, template_name)
    response.status_code = 500
    return response
