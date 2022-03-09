import pandas as pd
from common import filter_stats
from glob import iglob
from os import makedirs
from os.path import exists
from predictor import DATASET_NAME
from sportsipy.ncaab.rankings import Rankings
from sportsipy.ncaab.teams import Teams


def determine_location(game, team, sos, srs, opp_sos, opp_srs):
    if game.location == 'Away' or (game.location == 'Neutral' and \
       team.abbreviation not in game.boxscore_index):
        return opp_sos, opp_srs, sos, srs
    else:
        return sos, srs, opp_sos, opp_srs


def get_sos_and_srs(game, teams, team):
    sos = team.strength_of_schedule
    srs = team.simple_rating_system
    opponent = teams(game.opponent_abbr)
    opponent_sos = opponent.strength_of_schedule
    opponent_srs = opponent.simple_rating_system
    return determine_location(game, team, sos, srs, opponent_sos, opponent_srs)


def add_sos_and_srs(game, teams, team):
    df = game.dataframe_extended
    home_sos, home_srs, away_sos, away_srs = get_sos_and_srs(game, teams, team)
    try:
        df['home_strength_of_schedule'] = home_sos
        df['home_simple_rating_system'] = home_srs
        df['away_strength_of_schedule'] = away_sos
        df['away_simple_rating_system'] = away_srs
    except TypeError:
        return None
    return df


def check_path(filepath, name):
    if exists(filepath):
        return True
    else:
        if not exists('matches/%s' % name):
            makedirs('matches/%s' % name)
        return False


def pull_match_stats(teams, rankings, data):
    for team in teams:
        for game in team.schedule:
            # Skip any games that are already in the database, or which do not
            # contain valid data.
            if not game.boxscore_index or game.boxscore_index in data.index:
                continue
            path = 'matches/%s/%s.pkl' % (team.abbreviation.lower(),
                                          game.boxscore_index)
            if check_path(path, team.abbreviation.lower()) or \
               not game.boxscore_index:
                continue
            # Occurs when the opponent is Non-DI and the game should be skipped
            # since only DI matchups should be analyzed.
            if game.opponent_abbr == game.opponent_name:
                continue
            opponent = teams(game.opponent_abbr)
            df = add_sos_and_srs(game, teams, team)
            try:
                df.to_pickle(path)
            except AttributeError:
                continue


def build_dataset(data):
    frames = []
    for i, match in enumerate(iglob('matches/*/*')):
        if not i % 1000:
            data = pd.concat([data] + frames)
            frames = []
            continue
        frames.append(pd.read_pickle(match))
    return data


def process_dataset(data):
    data.drop_duplicates(inplace=True)
    data = filter_stats(data)
    data = data.dropna()
    data['home_free_throw_percentage'].fillna(0, inplace=True)
    data['away_free_throw_percentage'].fillna(0, inplace=True)
    data['points_difference'] = data['home_points'] - data['away_points']
    data.to_pickle(DATASET_NAME)


if __name__ == '__main__':
    data = pd.read_pickle(DATASET_NAME)
    teams = Teams()
    rankings = Rankings().current
    pull_match_stats(teams, rankings, data)
    data = build_dataset(data)
    process_dataset(data)
