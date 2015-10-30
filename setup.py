import pymongo, os, bottlenose, sendgrid, datetime
from algoliasearch import algoliasearch

client = pymongo.MongoClient(os.environ['db'],  w='majority')
algolia = algoliasearch.Client(os.getenv('ALGOLIA_APP'), os.getenv('ALGOLIA_KEY')).initIndex("classes")
db = client.mit_textbooks
classes = db.classes
overrides = db.overrides
recents = db.recents
groups = db.groups
offers = db.offers
blacklist = db.blacklist
queue = db.queue
users = db.users
google_cache = db.google_cache
recommendations = db.recommendations
rankings = db.rankings
shortlinks = db.shortlinks
flags = db.flags
buttons = db.buttons
orders = db.orders

amazon = bottlenose.Amazon(os.getenv('ACCESS_KEY'), os.getenv('SECRET_KEY'), os.getenv('ASSOC_TAG'))

YEAR = datetime.date.today().year
if 4 <= datetime.date.today().month < 12:
  TERM = "{}FA".format(YEAR+1)
  TERM_LAST = "{}SP".format(YEAR)
  STERM = "fa{}".format(str(YEAR)[-2:])
  STERM_LAST = "sp{}".format(str(YEAR)[-2:])
  CURRENT_TERM = "Fall {}".format(YEAR)
  TERM_START = datetime.datetime(YEAR, 9, 3)
  TERM_END = datetime.datetime(YEAR, 12, 10)
else:
  if datetime.date.today().month == 12:
    YEAR += 1
  TERM = "{}SP".format(YEAR)
  TERM_LAST = "{}FA".format(YEAR)
  STERM = "sp{}".format(str(YEAR)[-2:])
  STERM_LAST = "fa{}".format(str(YEAR-1)[-2:])
  CURRENT_TERM = "Spring {}".format(YEAR)
  TERM_START = datetime.datetime(YEAR, 2, 3)
  TERM_END = datetime.datetime(YEAR, 5, 14)

CURRENT_CATALOG  = "http://student.mit.edu/catalog/search.cgi?search={class_id}&style=verbatim"
LAST_CATALOG  = "http://student.mit.edu/catalog/archive/spring/search.cgi?search={class_id}&style=verbatim"

RECENTS = 20
CACHE_FOR = 2419200

host_secure = "https://tb.mit.edu" + ":444"
host_unsecure = "http://textbooksearch.mit.edu"

is_worker = os.getenv('is_worker', 'False') == 'True'

dev = (os.getenv('dev','False') == 'True')

TIME_REGEX = r'([A-Z]{1,5})(?: EVE \()?[\s]?([0-9]{0,2})[:\.]?([0-9]{0,2})-?([0-9]{0,2})[:\.]?([0-9]{0,2})( [A-Z]{2})?\)?'
CLASS_REGEX = r'((([A-Z]{2,3})|(([1][0-2,4-8]|[2][0-2,4]|[1-9])[AWFHLM]?))\.(([S]?[0-9]{2,4}[AJ]?)|(UA[TR])))'

if not dev:
  sg = sendgrid.SendGridClient(os.getenv('SENDGRID_USERNAME'), os.getenv('SENDGRID_PASSWORD'))
