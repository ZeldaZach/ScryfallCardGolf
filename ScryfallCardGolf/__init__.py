import configparser
import logging
import time
from TwitterAPI import TwitterAPI

# Config variables
TEMP_CARD_DIR = "../images/"
LOGGING_DIR = "../logs/"
TWEET_DATABASE = "../tweet_database.json"
TWEETER_ACCOUNT = "Zoozach"
SCRYFALL_RANDOM_URL = "https://api.scryfall.com/cards/random"
CONFIG_PATH = "../scryfallcardgolf.properties"

# Open and read secret properties
config = configparser.RawConfigParser()
config.read(CONFIG_PATH)

# Twitter API configuration
twitter_api = TwitterAPI(config.get('twitter', 'CONSUMER_KEY'),
                         config.get('twitter', 'CONSUMER_SECRET'),
                         config.get('twitter', 'ACCESS_TOKEN_KEY'),
                         config.get('twitter', 'ACCESS_TOKEN_SECRET')
                         )

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(asctime)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGGING_DIR + '/card_golf_' + str(time.strftime('%Y-%m-%d_%H:%M:%S')) + '.log')
    ])
