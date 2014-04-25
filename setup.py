import pymongo, os

client = pymongo.MongoClient(os.environ['db'])
db = client.mit_textbooks
classes = db.classes
recents = db.recents
offers = db.offers
named = db.named
users = db.users

TERM = "2014SP"
TERM_LAST = "2014FA"

STERM = "sp14"
STERM_LAST = "fa13"

RECENTS = 5
CACHE_FOR = 1209600

host_secure = "https://tb.mit.edu" + ":444"
host_unsecure = "http://textbooksearch.mit.edu"