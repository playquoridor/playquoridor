import datetime

from django.db import models
from datetime import timezone
from django.contrib import admin

from django.db import models
from django.conf import settings
from django.db.models import F  # https://docs.djangoproject.com/en/3.0/ref/models/expressions/#f-expressions
from django.db import transaction
from django.contrib.auth.models import User
from game.ratings.glicko2 import update_user_ratings
from .utils import create_game_id
from .time_controls import time_control

from dateutil.relativedelta import relativedelta
from datetime import datetime

# MAKE MIGRATIONS
# Run "python manage.py makemigrations game" after making changes to the model
# followed by "python manage.py migrate"

# RESET DB
# 1. Delete all migrations files.
# 2. Delete db. sqlite3 file.
# 3. Make new migrations files – python manage.py makemigrations game.
# 4. Migrate changes – python manage.py migrate.

# CREATE USER
# https://stackoverflow.com/questions/10372877/how-to-create-a-user-in-django
# from django.contrib.auth.models import User
# user = User.objects.create_user(username='john',
#                                  email='jlennon@beatles.com',
#                                  password='glass onion')

PLAYER_COLORS = ['white', 'black']
PLAYER_COLORS_INV = {c: i for i, c in enumerate(PLAYER_COLORS)}
TIME_CONTROLS = ['bullet', 'blitz', 'rapid', 'standard']
TIME_CONTROLS_INV = {t: i for i, t in enumerate(TIME_CONTROLS)}


# User details
class UserDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Whether the user is online
    online = models.SmallIntegerField(default=0)

    # Whether user is a bot
    bot = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['online']),
        ]

    def get_rating_query(self, control):
        time_control = TIME_CONTROLS_INV[control]
        R = self.rating_set.filter(time_control=time_control)
        return R

    def get_rating(self, control):
        R = self.get_rating_query(control)
        if len(R) > 0:
            return R[0]
        else:
            return self.create_rating(control)
            # return None

    def create_rating(self, control):
        time_control = TIME_CONTROLS_INV[control]
        R = Rating(user_details=self,
                   time_control=time_control,
                   rating=1500,
                   deviation=350,
                   volatility=0.06)
        R.save()
        return R

    def check_or_create_rating(self, control):
        R = self.get_rating_query(control)
        if not R.exists():
            R = self.create_rating(control)
            return R
        if len(R) > 0:
            return R[0]
        return

    def update_rating(self, control, rating, deviation, volatility):
        # Assumes rating for time control exists
        time_control = TIME_CONTROLS_INV[control]
        R = self.rating_set.select_for_update().filter(time_control=time_control)[0]
        """if not R.exists():  # Shouldn't happen?
            R = Rating(user_details=self,
                       time_control=time_control,
                       rating=1500,
                       deviation=350,
                       volatility=0.06)"""
        # Update
        R.update_rating(rating, deviation, volatility)
        R.save()


# Rating
class Rating(models.Model):
    user_details = models.ForeignKey(UserDetails, on_delete=models.CASCADE)
    time_control = models.PositiveSmallIntegerField()
    rating = models.FloatField()
    deviation = models.FloatField()
    volatility = models.FloatField()
    # n_games = models.PositiveIntegerField(default=0)

    def update_rating(self, rating, deviation, volatility):
        self.rating = rating
        self.deviation = deviation
        self.volatility = volatility
        # self.n_games = self.n_games + 1

    def get_time_control(self):
        return TIME_CONTROLS[self.time_control]

    class Meta:
        unique_together = ('user_details', 'time_control',)


# Game details
class SluggedModel(models.Model):
    # Ref: https://stackoverflow.com/questions/3759006/generating-a-non-sequential-id-pk-for-a-django-model
    game_id = models.SlugField(primary_key=True, unique=True, editable=False, blank=True)

    class Meta:
        abstract = True


class QuoridorGame(SluggedModel):
    # player_white = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, related_name='player_white')
    # player_black = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, related_name='player_black')
    active_player = models.PositiveSmallIntegerField(
        default=0)  # models.BooleanField(default=0)  # PositiveSmallIntegerField()
    move_number = models.PositiveSmallIntegerField(default=0)  # Whether game is rated

    # Game characteristics
    game_time = models.DateTimeField(auto_now_add=True)
    total_time_per_player = models.PositiveIntegerField(default=None, null=True)
    increment = models.PositiveSmallIntegerField(default=None, null=True)
    rated = models.PositiveSmallIntegerField(default=1)  # Whether game is rated

    # Game end
    time_end = models.DateTimeField(null=True)
    draw = models.BooleanField(default=False)
    abort = models.BooleanField(default=False)
    winning_player = models.ForeignKey('Player', on_delete=models.CASCADE, default=None, null=True)

    class Meta:
        ordering = ('-game_time',)
        indexes = [
            models.Index(fields=['game_time']),
            models.Index(fields=['time_end']),  # To check if games finished
            models.Index(fields=['abort']),
            models.Index(fields=['abort', 'draw', 'winning_player']),
        ]

    def save(self, *args, **kwargs):
        while not self.game_id:
            new_game_id = create_game_id(k=8)
            if not QuoridorGame.objects.filter(pk=new_game_id).exists():
                self.game_id = new_game_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.game_id}'

    """
    Game state
    """

    def move_count(self):
        return self.move_set.count()

    """
    FEN
    """

    def FEN(self):
        """
        Format: [1] / [2] / [3.1] [3.2] [3.3*] [3.4*] / [4.1] [4.2] [4.3*] [4.4*] / [5]
        1. Horizontal wall positions
        2. Vertical wall positions
        3. Pawn positions:
            3.1 Player 1 pawn position
            3.2 Player 2 pawn position
            3.3 Player 3 pawn position*
            3.4 Player 4 pawn position*
        4. Walls available:
            4.1 player 1 walls available
            4.2 player 2 walls available
            4.3 player 3 walls available*
            4.4 player 4 walls available*
        5. Active player
        * Four player only.
        """
        # Walls
        fences = self.fence_set.all()
        vertical_fences = sorted([str(f)[:2] for f in fences if f.fence_type_str == 'v'])
        horizontal_fences = sorted([str(f)[:2] for f in fences if f.fence_type_str == 'h'])

        # Pawn positions, walls available, and remaining time
        color2position, color2walls, color2time = self.get_player_details()
        pawn_positions = ''
        walls_available = ''
        remaining_times = ''
        for c in PLAYER_COLORS:
            row, col = color2position[c]
            pawn_positions += chr(col + 65) + str(row + 1)
            walls_available += str(color2walls[c]) + ' '
            if self.is_timed():
                remaining_times += str(color2time[c]) + ' '

        winner_color = self.winner_color()
        if self.draw:
            winner_color = '-1'
        elif self.abort:
            winner_color = '-2'
        elif winner_color is None:
            winner_color = ''

        # Construct FEN
        fen = f'{"".join(horizontal_fences)} / ' \
              f'{"".join(vertical_fences)} / ' \
              f'{pawn_positions} / ' \
              f'{walls_available}/ ' \
              f'{self.active_player + 1} / ' \
              f'{self.move_count()} / ' \
              f'{winner_color} / ' \
              f'{remaining_times}'
        return fen

    """
    PGN
    """

    def PGN(self):
        n_players = len(self.player_set.all())
        moves = self.move_set.all()
        out = ''
        for i, move in enumerate(moves):
            move_number = move.move_number // n_players + 1
            if move.move_number % n_players == 0:
                out += f'{move_number}. '
            out += f'{str(move)} '
        return out

    """
    Player details
    """

    def get_player_details(self):
        color2position = {}
        color2walls = {}
        color2time = {}

        # TODO
        # total_time_per_player = 60  # 300  # self.total_time_per_player
        total_time_per_player = self.total_time_per_player

        for p in self.player_set.all():
            color2position[p.player_color] = (p.row, p.col)
            color2walls[p.player_color] = p.remaining_fences
            if self.is_timed():
                t = 0
                if PLAYER_COLORS[self.active_player] == p.player_color:
                    if self.ended():
                        current_time = self.time_end.replace(tzinfo=timezone.utc)
                    else:
                        current_time = datetime.now(timezone.utc)
                    latest_timepoint = self.latest_timepoint()
                    if latest_timepoint is not None:
                        t = (current_time - latest_timepoint).total_seconds()
                color2time[p.player_color] = max(total_time_per_player - p.time_used - t, 0)
        return color2position, color2walls, color2time

    def get_active_player(self):
        return PLAYER_COLORS[self.active_player]

    @staticmethod
    def next_active_player(player_color):
        # TODO: 2+ players
        if player_color == 'white':
            active_player = 'black'
        else:
            active_player = 'white'
        return active_player

    @transaction.atomic
    def set_active_player(self, active_player):
        self.active_player = PLAYER_COLORS_INV[active_player]  # ['white', 'black'][active_player]
        self.save()

    """
    Update times
    """

    def time_control(self):
        return time_control(self.total_time_per_player, self.increment)

    def latest_timepoint(self):
        """
        if self.move_set.exists():
            t = self.move_set.latest('move_time').move_time
        else:
            t = self.game_time
        return t
        """
        t = None
        if self.move_set.count() > 1:
            # If two moves have been played
            t = self.move_set.latest('move_time').move_time
        return t

    def update_player_time(self, player, move_time):
        latest_timepoint = self.latest_timepoint()  # returns None if move count is > 2
        if latest_timepoint is not None:
            # Updates player time
            time_diff = move_time - latest_timepoint
            increment = self.increment  # 0
            player.time_used += time_diff.total_seconds() - increment
        remaining_time = self.total_time_per_player - player.time_used
        return remaining_time

    """
    Pawn
    """

    @transaction.atomic
    def update_pawn_position(self, player_color, row, col, move_time=None):
        assert player_color == PLAYER_COLORS[self.active_player]
        if move_time is None:
            move_time = datetime.now(timezone.utc)

        # Update pawn position
        player = self.player_set.select_for_update().filter(color=PLAYER_COLORS_INV[player_color])[0]
        # with transaction.atomic():
        player.row = row
        player.col = col

        # Update player time
        remaining_time = None
        if self.is_timed():
            remaining_time = self.update_player_time(player, move_time)
        player.save()

        # Register move
        pawn_move = PawnMove.objects.create(row=row, col=col)
        self.move_set.create(pawn_move=pawn_move, move_number=self.move_number, move_time=move_time)
        self.move_number += 1

        # Set next active player
        next_active_player = self.next_active_player(player_color)
        self.set_active_player(next_active_player)

        self.save()
        return next_active_player, remaining_time

    """
    Fences
    """

    @transaction.atomic
    def place_fence(self, player_color, row, col, fence_type, move_time=None):
        assert player_color == PLAYER_COLORS[self.active_player]
        if move_time is None:
            move_time = datetime.now()

        # Place fence
        fence = self.fence_set.create(row=row, col=col, fence_type=fence_type)
        fence.save()

        # Decrease player fences
        remaining_fences = self.decrease_fences(player_color)

        # Update player time
        remaining_time = None
        if self.is_timed():
            player = self.player_set.select_for_update().filter(color=PLAYER_COLORS_INV[player_color])[0]
            remaining_time = self.update_player_time(player, move_time)
            player.save()

        # Register move
        self.move_set.create(fence=fence, move_number=self.move_number, move_time=move_time)
        self.move_number += 1

        # Set next active player
        next_active_player = self.next_active_player(player_color)
        self.set_active_player(next_active_player)

        self.save()
        return remaining_fences, next_active_player, remaining_time

    @transaction.atomic
    def decrease_fences(self, player_color):
        player = self.player_set.select_for_update().filter(color=PLAYER_COLORS_INV[player_color])[0]
        # with transaction.atomic():
        player.remaining_fences = player.remaining_fences - 1
        player.save()
        return player.remaining_fences

    def get_fence_number(self, player_color):
        player = self.player_set.filter(color=PLAYER_COLORS_INV[player_color])[0]
        return player.remaining_fences

    """
    Game finish
    """

    def winner_username(self):
        """
        winner_username = None
        for player in self.player_set.all():
            if player.player_wins():
                winner_username = player.username
        return winner_username
        """
        if self.winning_player is None:
            return None
        return self.winning_player.username

    def winner_color(self):
        """
        winner_username = None
        for player in self.player_set.all():
            if player.player_wins():
                winner_username = player.username
        return winner_username
        """
        if self.winning_player is None:
            return None
        return self.winning_player.color

    def ended(self):
        # return self.winning_player is not None or self.draw or self.abort
        return self.time_end is not None

    def aborted(self):
        return self.abort

    @transaction.atomic
    def set_winner(self, winner_username, draw=False, abort=False):
        if not self.ended():
            if abort:
                self.abort = True
            elif draw:
                self.draw = True
            else:
                winner = self.player_set.filter(user__username=winner_username)[0]
                self.winning_player = winner
            self.time_end = datetime.now()  # .now()
            self.save()

    """
    Ratings
    """

    @transaction.atomic
    def update_rating(self, player_color, winner_username, draw):
        # Assumes game has finished
        assert self.ended()
        winner = self.winner_username()
        assert winner is None or winner == winner_username or draw

        time_control = self.time_control()
        if self.is_rated():
            color_id = PLAYER_COLORS_INV[player_color]
            player = self.player_set.select_for_update().filter(color=color_id)[0]

            # Get latest finished games in last month (history for Glicko-2 algorithm)
            user_players = Player.objects.filter(
                user__username=player.username,
                game__abort=False,
                game__time_end__isnull=False,
                game__game_time__gte=datetime.now()-relativedelta(months=1)
            ).order_by('game__game_time')
            scores = []
            opponent_ratings = []
            opponent_deviations = []
            for p in user_players:
                # Record details of latest games
                if p.game.time_control() == time_control:
                    op = p.get_opponent()
                    scores.append(p.get_score())
                    opponent_ratings.append(op.rating)
                    opponent_deviations.append(op.deviation)

            # Append last results
            # scores.append(score)
            # opponent_ratings.append(opponent.rating)
            # opponent_deviations.append(opponent.deviation)
            # print('Scores', scores)
            # print('Op ratings', opponent_ratings)
            # print('Op deviations', opponent_deviations)

            # Calculate new ratings
            # opponent_ratings = [opponent.rating]
            # opponent_deviations = [opponent.deviation]
            # scores = [score]
            user_details = player.user.userdetails
            rating_, deviation_, volatility_ = update_user_ratings(rating=player.rating,
                                                                   deviation=player.deviation,
                                                                   volatility=player.volatility,
                                                                   opponent_ratings=opponent_ratings,
                                                                   opponent_deviations=opponent_deviations,
                                                                   scores=scores)
            print(f'Updating player {player_color} ratings. New rating: {rating_}')

            # Update player delta
            player.delta_rating = rating_ - player.rating
            player.delta_deviation = deviation_ - player.deviation
            player.delta_volatility = volatility_ - player.volatility
            player.save()

            # Update user ratings
            control = self.time_control()
            user_details.update_rating(control, rating_, deviation_, volatility_)
            # TODO: Different ratings for different time controls?
            # user_details.standard_rating = rating_
            # user_details.standard_rating_deviation = deviation_
            # user_details.standard_rating_volatility = volatility_
            user_details.save()

    def ratings_updated(self, player_color):
        color_id = PLAYER_COLORS_INV[player_color]
        player = self.player_set.filter(color=color_id)[0]
        return player.ratings_updated()

    def delta_rating(self, player_username):
        player = self.player_set.filter(user__username=player_username)[0]
        return player.delta_rating

    def is_rated(self):
        return self.rated == 1

    def is_timed(self):
        # return True
        return self.total_time_per_player is not None


class Player(models.Model):
    game = models.ForeignKey(QuoridorGame, on_delete=models.CASCADE)
    # username = models.CharField(max_length=32)  # , primary_key=True
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # , default='Anonymous'
    row = models.PositiveSmallIntegerField()
    col = models.PositiveSmallIntegerField()
    color = models.PositiveSmallIntegerField()
    remaining_fences = models.PositiveSmallIntegerField(default=10)

    # Time variables
    time_used = models.FloatField(default=0., null=True)

    # Rating variables
    delta_rating = models.FloatField(default=None, null=True)
    delta_deviation = models.FloatField(default=None, null=True)
    delta_volatility = models.FloatField(default=None, null=True)

    # Set initial user ratings
    rating = models.FloatField(default=None, null=True)
    deviation = models.FloatField(default=None, null=True)
    volatility = models.FloatField(default=None, null=True)

    @property
    def player_color(self):
        return PLAYER_COLORS[self.color]

    @property
    def username(self):
        return self.user.username

    def player_wins(self):
        if PLAYER_COLORS[self.color] == 'white':
            return self.row == 8
        elif PLAYER_COLORS[self.color] == 'black':
            return self.row == 0
        return None

    def get_opponent(self):
        # TODO: Only 2 players
        return self.game.player_set.filter(color=(self.color + 1) % len(PLAYER_COLORS_INV))[0]

    def get_score(self):
        # Assumes game has finished and not aborted
        assert self.game.time_end is not None
        if self.game.draw:
            return 0.5
        elif self.game.winning_player == self:
            return 1
        return 0

    # Ratings
    def ratings_updated(self):
        return self.delta_rating is not None \
               and self.delta_deviation is not None \
               and self.delta_volatility is not None


class Fence(models.Model):
    game = models.ForeignKey(QuoridorGame, on_delete=models.CASCADE)
    row = models.PositiveSmallIntegerField()  # max_length=1
    col = models.PositiveSmallIntegerField()
    fence_type = models.BooleanField(default=False)

    @property
    def fence_type_str(self):
        # return 'v' if self.fence_type == b'\x00' else 'h'
        return 'v' if self.fence_type else 'h'

    def __str__(self):
        col_char = chr(self.col + 65)
        row = self.row + 1
        return f'{col_char}{row}{self.fence_type_str}'


class PawnMove(models.Model):
    row = models.PositiveSmallIntegerField()  # max_length=1
    col = models.PositiveSmallIntegerField()

    def __str__(self):
        return chr(self.col + 65) + str(self.row + 1)


class Move(models.Model):
    game = models.ForeignKey(QuoridorGame, on_delete=models.CASCADE)
    # player = models.ForeignKey(Player, on_delete=models.CASCADE)
    move_time = models.DateTimeField(null=True)
    fence = models.ForeignKey(Fence, on_delete=models.CASCADE, default=None, null=True, related_name='fence')
    pawn_move = models.ForeignKey(PawnMove, on_delete=models.CASCADE, default=None, null=True, related_name='pawn')
    move_number = models.PositiveSmallIntegerField(default=0)

    # Save FEN? To check 3-fold repetition

    class Meta:
        ordering = ('move_number',)

    def __str__(self):
        # Assumes only fence or move is not None
        if self.fence is not None:
            m = str(self.fence)
        else:
            m = str(self.pawn_move)
        return m  # f'{self.move_number}'
