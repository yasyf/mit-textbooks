import pymongo, os, bottlenose, sendgrid, datetime

client = pymongo.MongoClient(os.environ['db'])
db = client.mit_textbooks
classes = db.classes
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

amazon = bottlenose.Amazon(os.getenv('ACCESS_KEY'), os.getenv('SECRET_KEY'), os.getenv('ASSOC_TAG'))

TERM = "2015FA"
TERM_LAST = "2014SP"

CURRENT_TERM = 'Fall 2014'

CURRENT_CATALOG  = "http://student.mit.edu/catalog/search.cgi?search={class_id}&style=verbatim"
LAST_CATALOG  = "http://student.mit.edu/catalog/archive/spring/search.cgi?search={class_id}&style=verbatim"

STERM = "fa14"
STERM_LAST = "sp14"

TERM_START = datetime.datetime(2014, 9, 4)
TERM_END = datetime.datetime(2014, 12, 11)

RECENTS = 20
CACHE_FOR = 2419200

host_secure = "https://tb.mit.edu" + ":444"
host_unsecure = "http://textbooksearch.mit.edu"

is_worker = os.getenv('is_worker', 'False') == 'True'

dev = (os.getenv('dev','False') == 'True')

TIME_REGEX = r'([A-Z]{1,5})(?: EVE \()?[\s]?([0-9]{0,2})[:\.]?([0-9]{0,2})-?([0-9]{0,2})[:\.]?([0-9]{0,2})( [A-Z]{2})?\)?'
CLASS_REGEX = r'((([A-Z]{2,3})|(([1][0-2,4-8]|[2][0-2,4]|[1-9])[AWFHLM]?))\.([0-9]{2,4}[AJ]?))'

if not dev:
	sg = sendgrid.SendGridClient(os.getenv('SENDGRID_USERNAME'), os.getenv('SENDGRID_PASSWORD'))