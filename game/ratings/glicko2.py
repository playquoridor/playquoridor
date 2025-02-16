import numpy as np

# Glicko-2: http://www.glicko.net/glicko/glicko2.pdf
TAU = 0.3  # Reasonable choices are between 0.3 and 1.2
EPSILON = 0.000001


def convert_glicko2(rating, deviation):
    mu = (rating - 1500) / 173.7178
    phi = deviation / 173.7178
    return mu, phi


def convert_glicko2_inverse(mu, phi):
    rating = 173.7178 * mu + 1500
    deviation = 173.7178 * phi
    return rating, deviation


def g(deviation):
    return 1.0 / np.sqrt(1 + 3 * deviation ** 2 / np.pi ** 2)


def E(rating, opponent_rating, opponent_deviation):
    return 1.0 / (1 + np.exp(-g(opponent_deviation) * (rating - opponent_rating)))


def _f(x, delta_squared, phi, v, a, tau):
    ex = np.exp(x)
    return ex * (delta_squared - phi ** 2 - v - ex) / (2 * (phi ** 2 + v + ex) ** 2) - (x - a) / tau ** 2


def update_user_ratings(rating, deviation, volatility,
                        opponent_ratings, opponent_deviations, scores, tau=TAU):
    # Opponents deviations
    opponents_mus, opponents_phis = convert_glicko2(np.array(opponent_ratings), np.array(opponent_deviations))
    scores = np.array(scores)

    # Convert to Glicko-2 scale
    mu, phi = convert_glicko2(rating, deviation)

    # Compute variance of player's rating based on game outcomes
    gs = g(opponents_phis)
    Es = E(mu, opponents_mus, opponents_phis)
    v = 1 / np.sum(gs ** 2 * Es * (1 - Es))

    # Compute estimated improvement in rating by comparing the pre-period rating to performance rating based
    # on game outcomes
    delta = v * np.sum(gs * (scores - Es))
    delta_squared = delta ** 2

    # Determine the new volatility
    f = lambda x: _f(x, delta_squared, phi, v, a, tau)
    a = np.log(volatility ** 2)
    A = a
    if delta_squared > phi ** 2 + v:
        B = np.log(delta_squared - phi ** 2 - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        B = a - k * tau

    fA = f(A)
    fB = f(B)
    while np.abs(B - A) > EPSILON:
        C = A + (A - B) * fA / (fB - fA)
        fC = f(C)
        if fC * fB <= 0:
            A = B
            fA = fB
        else:
            fA = fA / 2
        B = C
        fB = fC

    # Update rating, deviation, and volatility
    new_volatility = np.exp(A / 2)
    phi_star = np.sqrt(phi ** 2 + new_volatility ** 2)
    new_phi = 1 / (np.sqrt(1 / phi_star ** 2 + 1 / v))
    new_mu = mu + new_phi ** 2 * np.sum(gs * (scores - Es))

    # Convert to original scale
    new_rating, new_deviation = convert_glicko2_inverse(new_mu, new_phi)

    return new_rating, new_deviation, new_volatility


if __name__ == '__main__':
    tau = 0.5
    rating = 1500
    deviation = 200
    volatility = 0.06
    opponent_ratings = [1400, 1550, 1700]
    opponent_deviations = [30, 100, 300]
    scores = [1, 0, 0]

    new_rating, new_deviation, new_volatility = update_user_ratings(rating, deviation, volatility, opponent_ratings,
                                                                    opponent_deviations, scores, tau=tau)
    print('Rating: ', new_rating)
    print('Deviation: ', new_deviation)
    print('Volatility: ', new_volatility)

    new_rating = rating
    new_deviation = deviation
    new_volatility = volatility
    for i in range(len(scores)):
        new_rating, new_deviation, new_volatility = update_user_ratings(new_rating, new_deviation, new_volatility,
                                                                        opponent_ratings[i], opponent_deviations[i],
                                                                        scores[i],
                                                                        tau=tau)
        print(f'Rating {i}: ', new_rating)
        print(f'Deviation {i}: ', new_deviation)
        print(f'Volatility {i}: ', new_volatility)
