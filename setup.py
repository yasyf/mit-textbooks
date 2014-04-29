import pymongo, os, bottlenose, sendgrid

client = pymongo.MongoClient(os.environ['db'])
db = client.mit_textbooks
classes = db.classes
recents = db.recents
groups = db.groups
offers = db.offers
blacklist = db.blacklist
queue = db.queue
users = db.users

amazon = bottlenose.Amazon(os.getenv('ACCESS_KEY'), os.getenv('SECRET_KEY'), os.getenv('ASSOC_TAG'))

TERM = "2014SP"
TERM_LAST = "2014FA"

STERM = "sp14"
STERM_LAST = "fa13"

RECENTS = 20
CACHE_FOR = 2419200

host_secure = "https://tb.mit.edu" + ":444"
host_unsecure = "http://textbooksearch.mit.edu"

is_worker = os.getenv('is_worker', 'False') == 'True'

dev = (os.getenv('dev','False') == 'True' or app.config['TESTING'] == True)

if not dev:
	sg = sendgrid.SendGridClient(os.getenv('SENDGRID_USERNAME'), os.getenv('SENDGRID_PASSWORD'))