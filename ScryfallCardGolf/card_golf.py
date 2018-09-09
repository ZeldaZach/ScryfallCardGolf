from typing import Dict, Any, List, Iterator, Tuple
import PIL.Image
import TwitterAPI
import argparse
import configparser
import datetime
import glob
import json
import logging
import os
import re
import requests
import shutil
import time
import urllib.parse as urlparse

# System Configuration
config = configparser.RawConfigParser()


def load_config(config_path: str) -> None:
    """
    Initialize the system configs
    :param config_path: path to load config properties from
    """
    # Open and read secret properties
    config.read(config_path)

    # Logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(asctime)s: %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                str(config.get('scryfallCardGolf', 'LOGGING_DIR')) + 'card_golf_' +
                str(time.strftime('%Y-%m-%d_%H:%M:%S')) + '.log')
        ])


def extract_query_length(json_dict: Dict[str, str]) -> int:
    """
    Query sort key to get length
    :param json_dict:
    :return: Length of object
    """
    return int(json_dict.get('length', 0))


def download_contents(url: str, download_type: str = 'json') -> Any:
    """
    Download contents from a URL
    :param url: URL to download
    :param download_type: Type of download (Default to JSON)
    :return: Contents
    """
    request_response: Any = {}
    if download_type == 'json':
        request_response = requests.get(url=url).json()
    elif download_type == 'image':
        request_response = requests.get(url=url, stream=True)

    logging.info('Downloaded URL {}'.format(url))
    return request_response


def delete_temp_cards() -> None:
    """
    Delete the PNG images in the image folder
    """
    for card in glob.glob(os.path.join(config.get('scryfallCardGolf', 'TEMP_CARD_DIR'), '*.png')):
        logging.info('Deleting file {}'.format(card))
        os.remove(card)


def download_random_cards(number_of_cards: int) -> List[Dict[str, Any]]:
    """
    Download random cards from Scryfall for use in SF Card Golf
    :param number_of_cards: How many cards to play with
    :return: List of card objects requested
    """
    return [download_contents(config.get('scryfallCardGolf', 'SCRYFALL_RANDOM_URL')) for _ in range(number_of_cards)]


def resize_image(url_to_open: str) -> None:
    """
    Some of the image combinations created are too large for Twitter.
    This method will resize the image to allow for proper tweet size.
    This will resize in-place.
    :param url_to_open: Local URL to get image from
    """
    try:
        im = PIL.Image.open(url_to_open)
        im.thumbnail((1024, 512), PIL.Image.ANTIALIAS)
        im.save(url_to_open, 'PNG')
    except IOError:
        logging.exception('Cannot create thumbnail for {}'.format(url_to_open))


def send_tweet(message_to_tweet: str, url_to_media: str) -> int:
    """
    Send a tweet with an image.
    :param message_to_tweet: Message to send
    :param url_to_media: Image to upload
    :return: Tweet ID (-1 if it failed)
    :raises Exception: Tweet failed to send for some reason
    """
    twitter_api = TwitterAPI.TwitterAPI(
        config.get('twitter', 'CONSUMER_KEY'),
        config.get('twitter', 'CONSUMER_SECRET'),
        config.get('twitter', 'ACCESS_TOKEN_KEY'),
        config.get('twitter', 'ACCESS_TOKEN_SECRET'),
    )

    logging.info('Tweet to send: {}'.format(message_to_tweet))
    try:
        if url_to_media is not None:
            resize_image(url_to_media)
            photo = open(url_to_media, 'rb')
            status = twitter_api.request('statuses/update_with_media', {'status': message_to_tweet}, {'media[]': photo})
            logging.info('Twitter Status Code: {}'.format(status.status_code))

            response = TwitterAPI.TwitterResponse(status, False).json()
            logging.info('Twitter Response Parsed: {}'.format(response))
            return int(response['id_str'])
        raise Exception("No image attached to tweet")
    except UnicodeDecodeError:
        logging.exception('Your message could not be encoded. Perhaps it contains non-ASCII characters?')
        raise Exception("Tweet failed to send")


def download_and_save_card_images(cards: List[Dict[str, Any]]) -> None:
    """
    Download and (temporarily) save card images for tweet processing
    :param cards: Cards to download and store
    """
    for card in cards:
        card_image_url: str = card['image_uris']['png']
        request_image = download_contents(card_image_url, 'image')
        with open(
                os.path.join(
                    config.get('scryfallCardGolf', 'TEMP_CARD_DIR'), '{}.png'.format(card['name'].replace('//', '_'))),
                'wb') as out_file:
            shutil.copyfileobj(request_image.raw, out_file)
        logging.info('Saving image of card {}'.format(card['name']))


def merge_card_images(cards: List[Dict[str, Any]]) -> str:
    """
    Taken from SO, but this method will merge all images in the
    images folder into one image. All prior images will be
    side-by-side
    :param cards: Cards to merge into one image
    :return: Resting URL of merged image
    """
    cards_to_merge: List[str] = glob.glob(os.path.join(config.get('scryfallCardGolf', 'TEMP_CARD_DIR'), '*.png'))

    images: Iterator[Any] = map(PIL.Image.open, cards_to_merge)
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = PIL.Image.new('RGB', (total_width, max_height))

    images = map(PIL.Image.open, cards_to_merge)
    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]

    combined_name: str = '{}-{}.png'.format(cards[0]['name'].replace('/', '_'), cards[1]['name'].replace('/', '_'))
    save_url: str = os.path.join(config.get('scryfallCardGolf', 'TEMP_CARD_DIR'), combined_name)

    new_im.save(save_url)
    logging.info('Saved merged image to {}'.format(save_url))

    return save_url


def write_to_json_db(file_name: str, entry: Any, database: bool = False) -> None:
    """
    Write out a dictionary into the json database
    :param file_name: Database location
    :param entry: New dictionary entry to add
    :param database: Write to database
    """
    feeds: Dict[str, Any] = {}
    if database:
        if os.path.isfile(file_name):
            with open(file_name) as json_feed:
                feeds = json.load(json_feed)
        feeds[time.strftime('%Y-%m-%d_%H:%M:%S')] = entry
    else:
        feeds['standard'] = sorted(entry[0], key=extract_query_length, reverse=False)
        feeds['regex'] = sorted(entry[1], key=extract_query_length, reverse=False)

    with open(file_name, mode='w') as f:
        # For some reason, backslashes appear as \\ instead of \. This fixes it :(
        f.write(json.dumps(feeds, indent=4, sort_keys=True))


def load_json_db(file_name: str) -> Any:
    """
    Load the database and return the contents
    :param file_name: Location of database
    :return: Database contents
    """
    if not os.path.isfile(file_name):
        return {}

    with open(file_name) as json_feed:
        return json.load(json_feed)


def is_active_contest_already(force_new_contest: bool) -> bool:
    """
    Determine if there is a current competition live.
    If the contest is finished, gather the results (separate function)
    :return: Active contest status
    """
    # See if a current contest is active
    json_db: Dict[str, Any] = load_json_db(config.get('scryfallCardGolf', 'TWEET_DATABASE'))
    try:
        max_key: str = max(json_db.keys())
    except ValueError:
        logging.warning("Database was empty, continuing")
        return False

    current_contest_start_date: datetime.datetime = datetime.datetime.strptime(max_key, '%Y-%m-%d_%H:%M:%S')
    current_contest_end_date: datetime.datetime = current_contest_start_date + datetime.timedelta(days=1)

    if not force_new_contest and current_contest_end_date > datetime.datetime.now():
        logging.warning('Current contest from {} still active'.format(max_key))
        return True

    write_results(get_results())
    return False


def test_query(user_name: str, scryfall_url: str) -> str:
    """
    Load up the Scryfall URL tweeted by the user and see if it
    matches the competition requirements (i.e. is it exclusively
    the two cards we are looking for)
    :param user_name: Twitter username
    :param scryfall_url: Scryfall URL they tweeted
    :return: Winning query ('' if failed)
    """
    try:
        query: str = urlparse.parse_qs(urlparse.urlparse(scryfall_url).query)['q'][0]

        scryfall_api_url = 'https://api.scryfall.com/cards/search?q={}'.format(urlparse.quote_plus(query))
        response: Dict[str, Any] = download_contents(scryfall_api_url)

        if response['total_cards'] != 2:
            logging.info('{} result has wrong number of cards: {}'.format(user_name, response['total_cards']))

        json_db: Dict[str, Any] = load_json_db(config.get('scryfallCardGolf', 'TWEET_DATABASE'))
        max_key: str = max(json_db.keys())
        valid_cards: List[str] = [json_db[max_key]['cards'][0]['name'], json_db[max_key]['cards'][1]['name']]
        for card in response['data']:
            if card['name'] not in valid_cards:
                logging.info('{} result has wrong card: {}'.format(user_name, card['name']))
                return ''

        if ' or ' in query.lower():
            logging.info("{} was correct, but they may have used 'OR': {}".format(user_name, query))
            return urlparse.unquote(query)

        # Correct response!
        logging.info('{} was correct! [ {} ] ({})'.format(user_name, query, len(query)))
        return urlparse.unquote(query)
    except KeyError:
        logging.info('{} submitted a bad Scryfall URL: {}'.format(user_name, scryfall_url))
        return ''


def get_results() -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Get the results from the competition and print it out
    :return: Winner's name and their query
    """
    twitter_api = TwitterAPI.TwitterAPI(
        config.get('twitter', 'CONSUMER_KEY'),
        config.get('twitter', 'CONSUMER_SECRET'),
        config.get('twitter', 'ACCESS_TOKEN_KEY'),
        config.get('twitter', 'ACCESS_TOKEN_SECRET'),
    )

    valid_normal_entries: List[Dict[str, Any]] = []
    valid_regex_entries: List[Dict[str, Any]] = []

    logging.info('GET RESULTS')

    json_db: Dict[str, Any] = load_json_db(config.get('scryfallCardGolf', 'TWEET_DATABASE'))
    max_key: str = max(json_db.keys())

    r = TwitterAPI.TwitterPager(twitter_api, 'statuses/mentions_timeline', {
        'count': 200,
        'since_id': json_db[max_key]['tweet_id']
    })

    for item in r.get_iterator():
        if 'text' not in item:
            logging.warning('SUSPEND, RATE LIMIT EXCEEDED: ' + item['message'])
            break

        logging.info('[TWEET] ' + item['user']['screen_name'] + ': ' + item['text'])
        for url in item['entities']['urls']:
            test_url = url['expanded_url']
            if 'scryfall.com' not in test_url:
                continue

            logging.info('{} submitted solution: {}'.format(item['user']['screen_name'], test_url))
            test_query_results = test_query(item['user']['screen_name'], test_url)
            if test_query_results:
                user_json_entry: Dict[str, Any] = {
                    'name': item['user']['screen_name'],
                    'length': len(test_query_results),
                    'query': test_query_results
                }

                if re.search(r'/.+/', test_query_results):
                    valid_regex_entries.append(user_json_entry)
                else:
                    valid_normal_entries.append(user_json_entry)

    return valid_normal_entries, valid_regex_entries


def write_results(results: Tuple[List[Dict[str, str]], List[Dict[str, str]]]) -> None:
    """
    Take a list of results and put it to the winners file for that contest
    :param results: List of winners
    """
    file_key: str = max(load_json_db(config.get('scryfallCardGolf', 'TWEET_DATABASE')).keys())
    write_to_json_db(
        os.path.join(config.get('scryfallCardGolf', 'WINNING_DIR'), 'winners_{}.json'.format(file_key)), results)


def start_game(force_new: bool = False) -> None:
    """
    Start the process of validating an old game and/or creating a new one
    :param force_new: Start a new game, even if one is running. End the old game
    """
    # If contest is over, print results and continue. Otherwise exit
    if is_active_contest_already(force_new):
        exit(0)

    # Clear out the cards directory
    delete_temp_cards()

    # Get 2 random cards
    cards: List[Dict[str, Any]] = download_random_cards(2)
    card1 = '{}: {}'.format(cards[0]['name'], cards[0]['scryfall_uri'].replace('api', 'card_golf'))
    card2 = '{}: {}'.format(cards[1]['name'], cards[1]['scryfall_uri'].replace('api', 'card_golf'))

    for card in cards:
        logging.info('Card to merge: {}'.format(card['name']))

    # Save the images
    download_and_save_card_images(cards)

    # Merge the images
    tweet_image_url: str = merge_card_images(cards)

    message = ("Can you make both of these cards show up in a Scryfall search without using 'or'?\n"
               "• {}\n"
               "• {}\n"
               "Reply to this tweet with a Scryfall URL in the next 24 hours to enter!").format(card1, card2)

    # Send the tweet
    tweet_id: int = send_tweet(message, tweet_image_url)

    json_entry: Dict[str, Any] = {
        'tweet_id': tweet_id,
        'cards': [{
            'name': cards[0]['name'],
            'url': cards[0]['scryfall_uri'],
        }, {
            'name': cards[1]['name'],
            'url': cards[1]['scryfall_uri'],
        }],
    }

    write_to_json_db(config.get('scryfallCardGolf', 'TWEET_DATABASE'), json_entry, True)


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description='Handle Scryfall Card Golf')
    parser.add_argument('--config', type=str, required=True, nargs='?', help='config for system')
    parser.add_argument('--results', action='store_true', help='get latest contest results')
    parser.add_argument('--force-new', action='store_true', help='force start next contest')

    args = parser.parse_args()
    load_config(args.config)

    if args.results:
        write_results(get_results())
        return

    start_game(args.force_new)


if __name__ == '__main__':
    main()
