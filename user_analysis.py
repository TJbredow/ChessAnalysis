"""
Class set for game analysis Version 0.0.1
includes class GameAnalysis, Userdata and may be expanded later
"""

import json
import os
import re

import requests
import pandas as pd

PLAYER_CACHE_DIR = "./playercache/"
DATABASE_FILE = './eco.json'
with open(DATABASE_FILE,'r', encoding='utf-8') as databasefile:
    OPENING_DATABASE = json.loads(databasefile.read())

class UserData:
    """Non-terable General data class for a user.
        Takes one required parameter: Username (str) of a chess player on chess.com
        Read the __init__ doc for optional.
        Default attributes:
        - user (str): provided username
        - games (list): list of games in memory
        - cache (Bool): Whether to save data to disk in cache
        Methods:
        - pullgames: pulls games from Chess.com. Optionally caches archives.
        - analysis: analyses the game. Takes additional arguments.
    """

    def pullgames(self, url: str) -> list:
        """Pulls games from chess.com database from provided url.
        returns list of games from month, and chaches.
        """
        print(url)
        lastsix = url[::-1][0:6][::-1].replace('/','-')
        if f'{self.user}-{lastsix}' in os.listdir(PLAYER_CACHE_DIR) and self.cache:
            with open(
                os.path.join(PLAYER_CACHE_DIR, lastsix),
                'r',
                encoding='utf-8')\
            as cachefile:
                return json.loads(cachefile.read())
        print('requesting')
        games = requests.get(url).json()['games']
        if self.cache:
            with open(
                os.path.join(PLAYER_CACHE_DIR, f'{self.user}-{lastsix}'),
                'w',
                encoding='utf-8')\
            as cachefile:
                cachefile.write(
                    json.dumps(games, sort_keys=False, indent=2))
        return games

    def __init__(self, username: str, **kargs):
        """Parameters
        Required: Username (str)
        Optional:
            - incbullet (True/False): include bullet games, default False
            - samplesize (int): How many months you want to look back, default 12
            - cache (True/False): Cache game archive and analysis on disk, default True"""
        self.user = username.lower()
        self.games= [] #Build game list
        if kargs.get('cache', True):
            self.cache = True
        else:
            self.cache = False
        archives = requests.get(f"https://api.chess.com/pub/player/{username}/games/archives")
        months = archives.json()['archives'][::-1][0:int(kargs.get('samplesize',12))]
        for month in months:
            self.games.extend(
                self.pullgames(month)
                )
        if not kargs.get('incbullet', False):
            self.games = list(filter(
                lambda x: x['time_class'] != 'bullet', self.games
                ))



    def analysis(self, color: str, openingdepth='deep') -> pd.DataFrame:
        """Analyses the set of games and returns a Pandas Dataframe according to parameters
        Required Parameters:
        openingdepth: Choose from firstmove, root, family, or deepest line in database

        """
        games_byopening = {}
        for game in self.games:
            game_data = GameAnalysis(self.user, game)
            if game_data.color == color:
                opening = game_data.filter_openings(depth=openingdepth)
                if not games_byopening.get(opening['name']):
                    games_byopening[opening['name']] = {
                        'eco' : opening.get('eco'),
                        'gamesplayed' : 0,
                        'win' : 0,
                        'loss' : 0,
                        'draw' : 0
                        }
                #increment the opening
                games_byopening[opening.get('name')]['gamesplayed'] += 1
                games_byopening[opening.get('name')][game_data.result] += 1
                for o in games_byopening:
                    try:
                        games_byopening[o]['winvsloss'] = float(
                            games_byopening[o]['win'] / (games_byopening[o]['win'] + games_byopening[o]['loss']))
                    except ZeroDivisionError:
                        games_byopening[o]['winvsloss'] = 0.0
                    games_byopening[o]['wintotalpct'] = float(
                        games_byopening[o]['win'] / games_byopening[o]['gamesplayed'])
                    games_byopening[o]['drawtotal'] = float(
                        games_byopening[o]['draw'] / games_byopening[o]['gamesplayed'])
        return pd.DataFrame.from_dict(games_byopening, orient='index')

class GameAnalysis:
    """Non-iterable User Object with the following attributes:
        Initial Paramters: chess.com game data (dict) and username (str)
        Attributes:
        - color (str): White/Black
        - pgn (str): pgn file represented as raw string
        - opening_list (list): The openings and variations that this game matches
        - time_class (Time Control): Bullet, Blitz, Rapid, etc.
        - moves (str): String of moves in PGN notation, clean of any clock data
        - accuracy (float): Accuracy of the player according to chess.com (coming soon)
        methods:
        - result (str)(win/loss/draw): Result for the user in question
        - filter_openings: filters down opening_list to preferred opening depth
    """
    # pylint: disable=too-many-instance-attributes

    def findcolor(self) -> str:
        """Returns which color the analyzed player played."""
        if self.user in self.game.get('white').get('username').lower():
            return "white"
        if self.user in self.game.get('black').get('username').lower():
            return "black"
        return "Unknown"

    def findresult(self) -> str:
        """Returns string (win/loss/draw) for player, from chess.com more detailed results"""
        drawcons = ['agreed','repetition','stalemate','timevsinsufficient','insufficient']
        if self.game[self.color]['result'] == 'win':
            return 'win'
        if self.game[self.color]['result'] in drawcons:
            return 'draw'
        return 'loss'


    def move_clean(self) -> str:
        """Returns moves without clock data or headers."""
        cleanmoves = re.sub( # regex to remove clock data from moves
            r'(\{.+?\})|( [0-9]+?\.\.\. )',
            '',
            self.pgn.split('\n')[-2:-1][0])\
            .replace('  ',' ')
        return cleanmoves

    def find_opening(self) -> list:
        """Returns dict value from database that matches opening."""
        openings = list(filter( # filters all openings that match
            lambda x: x['moves'] in self.moves, OPENING_DATABASE
            ))
        if openings:
            return openings
        return [{
                "name": "Unknown",
                "eco": "UNK",
                "fen": "",
                "moves": ""
                }]

    def __init__(self, username: str, game: dict):
        """ Initialize values, requires one argument:
        game: dict value from Chess.com for one game
        """
        self.user = username
        self.game = game #allow for theses items to be used
        self.pgn = game.get('pgn')
        self.rules = game.get('rules')
        self.time_class = game.get('time_class')
        self.color = self.findcolor()
        self.result = self.findresult()
        #self.accuracy = float(game.get("accuracies").get(self.color))
        self.moves = self.move_clean()
        self.opening_list = self.find_opening()


    #Class methods designed for external use

    def filter_openings(self, **kargs) -> dict:
        """Filter set of openings based on need, returns only one based on arguments.
        Argument: depth = ('firstmove','root','family','deep')
            - firstmove: returns white's first move
            - root: returns the opening based on the letter of the opening in the ECO
            - family: returns the opening based on the letter and first number of the ECO
            - deep(default): returns the deepest knowledge of the opening in the database.
        """
        maxlength = max(map(
            lambda x: len(x['moves']),self.opening_list
            ))
        for opening in self.opening_list:
            if len(opening.get('moves')) == maxlength:
                deepopening = opening
        # Using a switcher dictionary to find the different values. Defaults to maxlength.
        depth = {
            'firstmove': \
                min(map(
                    lambda x: len(x['moves']),self.opening_list
                    )),
            'root': \
                min(map(
                    lambda y: len(y['moves']),
                    list(filter(
                        lambda x: x['eco'][0:2] == deepopening['eco'][0:2],
                        self.opening_list
                        ))
                    )),
            # its okay if root == family, but not family == deep
            'family': \
                min(map(
                    lambda y: len(y['moves']),
                    list(filter(
                        lambda x: x['eco'][0:3] == deepopening['eco'][0:3],
                        self.opening_list
                        ))
                    )),
        }
        choice = depth.get(kargs.get('depth'), maxlength)
        for opening in self.opening_list:
            if len(opening.get('moves')) == choice:
                return opening
        return False


                