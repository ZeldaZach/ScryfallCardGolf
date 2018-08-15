import configparser
import logging
import time
from TwitterAPI import TwitterAPI

# Config options
CONFIG_PATH = '../scryfallcardgolf.properties'

# Open and read secret properties
config = configparser.RawConfigParser()
config.read(CONFIG_PATH)

# Twitter API configuration
twitter_api = TwitterAPI(config.get('twitter', 'CONSUMER_KEY'),
                         config.get('twitter', 'CONSUMER_SECRET'),
                         config.get('twitter', 'ACCESS_TOKEN_KEY'),
                         config.get('twitter', 'ACCESS_TOKEN_SECRET')
                         )

TWEETER_ACCOUNT = config.get('twitter', 'USERNAME')
LOGGING_DIR = config.get('scryfallCardGolf', 'LOGGING_DIR')
TEMP_CARD_DIR = config.get('scryfallCardGolf', 'TEMP_CARD_DIR')
TWEET_DATABASE = config.get('scryfallCardGolf', 'TWEET_DATABASE')
SCRYFALL_RANDOM_URL = config.get('scryfallCardGolf', 'SCRYFALL_RANDOM_URL')

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(asctime)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOGGING_DIR) + 'card_golf_' + str(time.strftime('%Y-%m-%d_%H:%M:%S')) + '.log')
    ])
