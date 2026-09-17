"""Collect a bounded corpus of history pages and primary-source book chapters."""
import json
import time
from urllib.parse import urlsplit, urljoin, quote, unquote
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from collect import fetch, RAW, ROOT

ROBOTS = {}
ERRORS = []

def page(url, key):
    origin = urlsplit(url).scheme + '://' + urlsplit(url).netloc
    if origin not in ROBOTS:
        data = fetch(origin + '/robots.txt', key.split('/')[0] + '/robots.txt')
        parser = RobotFileParser()
        parser.parse(data.decode('utf-8', errors='replace').splitlines())
        ROBOTS[origin] = parser
    if not ROBOTS[origin].can_fetch('CocktailResearch', url):
        raise RuntimeError('robots.txt disallows ' + url)
    data = fetch(url, key)
    time.sleep(0.8)
    return BeautifulSoup(data, 'html.parser')

def safe(url, key):
    try:
        soup = page(url, key)
        print('OK', key, flush=True)
        return soup
    except Exception as exc:
        ERRORS.append({'url': url, 'error': str(exc)})
        print('FAILED', url, str(exc), flush=True)

def main():
    book = 'https://en.wikisource.org/wiki/The_Bar-tender%27s_Guide'
    soup = safe(book, 'wikisource/index.html')
    if soup:
        links = sorted({urljoin(book, a['href']) for a in soup.select('a[href]')
                        if unquote(a['href']).startswith("/wiki/The_Bar-tender's_Guide/") and '#' not in a['href']})
        for i, url in enumerate(links):
            safe(url, f'wikisource/chapter_{i:02}.html')
    titles = ['Cocktail', 'History_of_alcoholic_drinks', 'Jerry_Thomas_(bartender)',
              'Harry_Craddock', 'Ada_Coleman', 'Dale_DeGroff', 'Donn_Beach', 'Trader_Vic',
              'Old_fashioned_(cocktail)', 'Martini_(cocktail)', 'Manhattan_(cocktail)',
              'Negroni', 'Daiquiri', 'Margarita', 'Mojito', 'Mai_Tai', 'Sazerac',
              'Sidecar_(cocktail)', 'Aviation_(cocktail)', 'Bloody_Mary_(cocktail)',
              'French_75_(cocktail)', 'Tom_Collins', 'Singapore_sling', 'Pisco_sour',
              'Whiskey_sour', 'Ramos_gin_fizz', 'Mint_julep', 'Cosmopolitan_(cocktail)',
              'Espresso_martini', 'Penicillin_(cocktail)', 'Zombie_(cocktail)',
              'Bramble_(cocktail)', 'Boulevardier_(cocktail)', 'Hanky_panky_(cocktail)',
              'Vesper_(cocktail)', 'Last_Word_(cocktail)', 'Corpse_reviver',
              'Piña_colada', 'Caipirinha', 'Dark_%27n%27_stormy',
              'Gin', 'Rum', 'Tequila', 'Mezcal', 'Whisky', 'Bourbon_whiskey',
              'Rye_whiskey', 'Brandy', 'Cognac', 'Vodka', 'Vermouth', 'Absinthe',
              'Bitters', 'Triple_sec', 'Campari', 'Orgeat_syrup', 'Grenadine',
              'Cocktail_shaker', 'Jigger', 'Cocktail_strainer', 'Muddler',
              'Highball', 'Sour_(cocktail)', 'Fizz_(cocktail)', 'Flip_(cocktail)',
              'Tiki_culture', 'Prohibition_in_the_United_States']
    for title in titles:
        safe('https://en.wikipedia.org/wiki/' + quote(unquote(title), safe="_()'"),
             'wikipedia/' + quote(unquote(title), safe='_()') + '.html')
    safe('https://iba-world.com/cocktails/', 'iba_official/index.html')
    (ROOT / 'data' / 'collection_errors.json').write_text(json.dumps(ERRORS, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
