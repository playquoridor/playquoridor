import django
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def get_player_color(game, p):
    player_color = None
    for player in game.player_set.all():
        # if player.user.username.lower() == 'anonymous' and p.user.username.lower() == 'anonymous' and p.session_key == player.session_key:
        #     player_color = player.player_color
        #     break
        if player.user.username == p.user.username:
            player_color = player.player_color
            break
    return player_color


@register.simple_tag
def get_opponent_username(game, username):
    opponent_username = ''
    for player in game.player_set.all():
        if player.user.username != username:
            opponent_username = player.user.username
            break
    return opponent_username


@register.simple_tag
def get_rating_str(ud, time_control):
    r = ud.get_rating(time_control)
    if r is None:
        return '  ?  '
    out = str(int(r.rating))
    return out


@register.simple_tag
def get_player(game, username):
    player = None
    for p in game.player_set.all():
        if p.username == username:
            player = p
            break
    return player


@register.simple_tag
def get_opponent(game, username):
    player = None
    for p in game.player_set.all():
        if p.username != username:
            player = p
            break
    return player

@register.simple_tag
def get_username(user):
    if user is None or user.username == '':
        return 'Anonymous'
    return user.username

@register.simple_tag
def player_rating(player):
    if player is None or player.username == '':
        return ''
    return int(player.rating)

@register.simple_tag
def get_player(game, username):
    player = None
    for p in game.player_set.all():
        if p.username == username:
            player = p
            break
    return player


@register.simple_tag
def get_default_time(control):
    default_times = {'bullet': 1, 'blitz': 5, 'rapid': 10, 'standard': 25}
    return default_times[control]


@register.simple_tag
def get_default_increment(control):
    default_times = {'bullet': 1, 'blitz': 3, 'rapid': 5, 'standard': 10}
    return default_times[control]


@register.simple_tag
def flip_board(game, username):
    player_color = None
    for player in game.player_set.all():
        if player.user.username == username:
            player_color = player.player_color
            break
    return player_color != 'white'


@register.simple_tag
def convert2int(value):
    return int(value)


@register.simple_tag
def rating_delta(value):
    if value is None or value == '':
        return ''
    if value >= 0:
        out = f'<span class="positive-delta">+{int(value)}</span>'
    else:
        out = f'<span class="negative-delta">{int(value)}</span>'
    return mark_safe(out)


@register.simple_tag
def trim_string(s, k=12):
    if len(s) > k:
        s = s[:k] + '...'
    return s


@register.simple_tag
def convert_time_control(t):
    v = ['Bullet', 'Blitz', 'Rapid', 'Standard'][t]
    # out = f'<span class="timecontrol-{v}">{v}</span>'
    # return mark_safe(out)
    return v


@register.simple_tag
def get_online_status(player):
    # Check if player is a Django user
    if isinstance(player, django.contrib.auth.models.User):
        return 'online' if player.userdetails.online > 0 else 'offline'
    if player is None or player.username == '':
        return 'offline'
    user = player.user
    if user.userdetails.online > 0:
        return 'online'
    return 'offline'


@register.simple_tag
def get_pawn(game, username):
    color = get_player_color(game, username)
    if color == 'white':
        return '♟'
    return '♙'  # mark_safe('<span class="black-text">' + '♙' + '</span>')
