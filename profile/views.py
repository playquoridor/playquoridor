from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, render, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.core.paginator import Paginator
from game.models import QuoridorGame, Player
from quoridor.views import handler404
from django.db.models import \
    Q  # Ref: https://docs.djangoproject.com/en/dev/topics/db/queries/#complex-lookups-with-q-objects
from datetime import timedelta
from datetime import date
import itertools
import pandas as pd


def last_k_games_context(request, username, k=3):
    # Unused for now
    # TODO: Consider using cache
    context = {
        'query_user': username,
        'game_list': []
    }
    try:
        played = Player.objects.filter(user__username=username).order_by('-game__game_time')[:k]
        game_list = [p.game for p in played]
        context = {
            'query_user': username,
            'game_list': game_list
        }
    except QuoridorGame.DoesNotExist:
        pass
    return context


#####################
#    User views     #
#####################
def get_user_games(request, username):
    played = Player.objects.filter(user__username=username).order_by('-game__game_time')  # '-id')
    game_list = [p.game for p in played if not p.game.aborted()]
    return game_list


def list_games(request, username):
    query_user = User.objects.get(username=username)
    game_list = get_user_games(request, username)

    # Pagination
    page = request.GET.get('page')
    paginator = Paginator(game_list, 9)  # 12 games per page
    games_page = paginator.get_page(page)

    context = {
        'query_user': query_user,
        # 'game_list': game_list,
        'games_page': games_page
    }
    return render(request, 'profile/games.html', context=context)


def list_user_user_games(request, username_1, username_2):
    try:
        # Optimising database: https://docs.djangoproject.com/en/4.2/topics/db/optimization/
        user_1 = User.objects.get(username=username_1)
        user_2 = User.objects.get(username=username_2)
        game_list = get_user_games(request, username_1)

        # Filter games
        def game_played_by_user(g, username):
            game_usernames = [p.username for p in g.player_set.all()]
            return username in game_usernames

        game_list = [g for g in game_list if game_played_by_user(g, username_2)]
        # game_list = QuoridorGame.objects.filter(player__user__username__in=[username_1, username_2])

        # Pagination
        page = request.GET.get('page')
        paginator = Paginator(game_list, 9)  # 9 games per page
        games_page = paginator.get_page(page)

        context = {
            'user_1': user_1,
            'user_2': user_2,
            'games_page': games_page
        }
        return render(request, 'profile/user_user_games.html', context=context)
    except ObjectDoesNotExist:
        context = {
            'error': f'User not found'
        }
        return handler404(request, '404.html', context=context)


def ratings_per_control(played, query_user):
    out = {}
    for control in ['bullet', 'blitz', 'rapid', 'standard']:
        ratings_control = [(p.rating, p.delta_rating, p.game.game_time.strftime('%Y-%m-%d')) for p in played if
                           p.ratings_updated() and p.game.time_control() == control]

        # Group ratings by date (use last rating of the day)
        ratings_per_day = []
        for pgroupby in itertools.groupby(ratings_control, key=lambda x: x[-1]):
            _, (*_, p) = pgroupby  # Gets last element of every day
            ratings_per_day.append([p[-1], int(p[0] + p[1])])

        if len(ratings_per_day) > 0:
            # Set initial rating
            initial_date = query_user.date_joined - timedelta(days=1)
            ratings_per_day.append([initial_date.strftime('%Y-%m-%d'), 1500])

            # Set final rating
            ratings_per_day = ratings_per_day[::-1]
            final_date = date.today()
            ratings_per_day.append([final_date.strftime('%Y-%m-%d'), ratings_per_day[-1][1]])
            out[control] = ratings_per_day

    return out


def get_ratings_table(ratings_per_day):
    # Initialize an empty list to store the rows
    rows = []

    # Iterate through the dictionary items
    for time_control, values in ratings_per_day.items():
        for date, rating in values:
            # Append a tuple with the required values to the list
            rows.append((date, time_control, rating))

    # Create a DataFrame from the list of tuples
    df = pd.DataFrame(rows, columns=['date', 'time_control', 'rating'])
    df.drop_duplicates(inplace=True)

    # Pivot the DataFrame
    pivot_df = df.pivot(index='date', columns='time_control', values='rating').reset_index()

    # Rename the columns
    pivot_df.columns.name = None  # Remove the 'time_control' label
    pivot_df.columns = ['date'] + list(ratings_per_day.keys())  # 'bullet_rating', 'blitz_rating']

    # Display the resulting DataFrame
    return pivot_df.values, list(pivot_df.columns)


def show_profile(request, username, top_k_games=3):
    try:
        query_user = User.objects.get(username=username)
        played = Player.objects.filter(user__username=username, game__abort=False).order_by('-game__game_time')  # game__game_time
        game_list = [p.game for p in played[:top_k_games]]
        n_games = played.count()
        ratings_per_day = ratings_per_control(played, query_user)
        ratings_table, ratings_columns = get_ratings_table(ratings_per_day)

        # Include
        context = {
            'query_user': query_user,
            'ratings_table': ratings_table,
            'ratings_columns': ratings_columns,
            'n_games': n_games,
            'game_list': game_list
        }
        return render(request, 'profile/profile.html', context=context)
    except ObjectDoesNotExist:
        context = {
            'error': f'User not found'
        }
        return handler404(request, '404.html', context=context)
