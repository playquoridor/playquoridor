def time_control(total_time_per_player, increment):
    """
    Time control is calculated as follows:  (clock initial time in seconds) + 40 × (clock increment)

    ≤ 179s = Bullet
    ≤ 479s = Blitz
    ≤ 1499s = Rapid
    ≥ 1500s = Standard
    :return: time control (string)
    """
    s = total_time_per_player + 40 * increment
    if s <= 179:
        return 'bullet'
    elif s <= 479:
        return 'blitz'
    elif s <= 1499:
        return 'rapid'
    else:
        return 'standard'