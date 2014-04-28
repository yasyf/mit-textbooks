import pymongo, os, bottlenose

client = pymongo.MongoClient(os.environ['db'])
db = client.mit_textbooks
classes = db.classes
recents = db.recents
groups = db.groups
offers = db.offers

amazon = bottlenose.Amazon(os.getenv('ACCESS_KEY'), os.getenv('SECRET_KEY'), os.getenv('ASSOC_TAG'))

TERM = "2014SP"
TERM_LAST = "2014FA"

STERM = "sp14"
STERM_LAST = "fa13"

RECENTS = 5
CACHE_FOR = 2419200

host_secure = "https://tb.mit.edu" + ":444"
host_unsecure = "http://textbooksearch.mit.edu"

worker = os.getenv('worker')
is_worker = os.getenv('is_worker', 'False') == 'True'