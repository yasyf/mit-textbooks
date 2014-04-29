#!/usr/bin/env python

from setup import *
import json, hashlib, time, datetime, requests, mechanize, Levenshtein, operator, time, urllib, re
from flask import g, flash
from bs4 import BeautifulSoup
from lxml import objectify
from bson.objectid import ObjectId
from requests_futures.sessions import FuturesSession
from models.mitclass import MITClass
from models.mitclassgroup import MITClassGroup
from models.mituser import MITUser

class_objects = {}
group_objects = {}
user_objects = {}

auth_browser = None

def init_auth_browser():
	global auth_browser
	auth_browser = mechanize.Browser()
	auth_browser.set_handle_robots(False)
	auth_browser.open("https://edu-apps.mit.edu/ose-rpt/subjectEvaluationSearch.htm")
	auth_browser.select_form(nr=1)
	auth_browser["j_username"] = os.getenv('j_username')
	auth_browser["j_password"] = os.getenv('j_password')
	auth_browser.submit()
	auth_browser.select_form(nr=0)
	try:
		auth_browser.submit()
	except Exception:
		pass

def sha(text):
	return hashlib.sha256(text).hexdigest()

def md5(s):
	if md5 not in g:
		g.md5 = {}
	if s in g.md5:
		return g.md5[s]
	_hash = hashlib.md5(s).hexdigest()
	g.md5[s] = _hash
	return _hash

def clean_html(html):
	return html.strip().replace("\n"," ").encode('ascii','xmlcharrefreplace')

def get_user(email, name, phone):
	global user_objects
	if not email:
		return None
	if email in user_objects:
		return user_objects[email]
	else:
		u = MITUser(email, name, phone)
		user_objects[email] = u
		return u

def get_class(class_id):
	global class_objects
	if class_id in class_objects:
		return class_objects[class_id]
	class_info = classes.find_one({"class": class_id})
	if class_info and (time.time() - class_info['dt']) < CACHE_FOR:
		if 'error' in class_info:
			return None
		if (time.time() - class_info['textbooks']['dt']) > (CACHE_FOR/4.0) and not is_worker:
			fsession = FuturesSession()
			fsession.get(worker + url_for('update_textbooks_view', class_id=class_id))
		class_obj = MITClass(class_info)
		class_objects[class_id] = class_obj
		return class_obj
	class_info = fetch_class_info(class_id)
	if class_info:
		class_obj = MITClass(class_info)
		class_objects[class_id] = class_obj
		classes.update({"class": class_obj.id}, {"$set": class_obj.to_dict()}, upsert=True)
		return class_obj
	classes.insert({"class": class_id, "error": 404, 'dt': time.time()})

def update_textbooks(class_id):
	class_info = classes.find_one({"class": class_id})
	class_info['textbooks'] = get_textbook_info(class_info['id'], class_info['semesters'])
	classes.update({"class": class_info['class']}, {"$set": {'textbooks': class_info['textbooks']}})

def get_group(group_id):
	global group_objects
	if group_id in group_objects:
		return group_objects[group_id]
	group_info = groups.find_one({"$or": [{"name": group_id}, {"hash": group_id}]})
	if group_info:
		group_obj = MITClassGroup(group_info)
		group_objects[group_id] = group_obj
		return group_obj

def prepare_class_hash(classes):
	classes = ','.join([clean_html(c) for c in classes])
	_hash = md5(classes)
	if groups.find_one({"hash": _hash}):
		return _hash
	else:
		group_info = create_group_info(classes, _hash)
		group_obj = MITClassGroup(group_info)
		group_objects[_hash] = group_obj
		groups.insert(group_obj.to_dict())
		return _hash

def create_group_info(classes, _hash):
	group_info = {}
	group_info['named'] = False
	group_info['hash'] = _hash
	group_info['class_ids'] = classes
	return group_info

def check_json_for_class(url, class_id):
	response = requests.get(url)
	json_data = response.json()["items"]
	for element in json_data:
		if 'id' in element and element['id'] == clean_html(class_id):
			return element

def fetch_class_info(class_id):
	url = "http://coursews.mit.edu/coursews/?term={term}&courses={course_number}".format(term=TERM, course_number=class_id.split('.')[0])
	class_info = check_json_for_class(url, class_id)
	if not class_info:
		url = "http://coursews.mit.edu/coursews/?term={term}&courses={course_number}".format(term=TERM_LAST, course_number=class_id.split('.')[0])
		class_info = check_json_for_class(url, class_id)
	if class_info:
		return clean_class_info(class_info)

def clean_class_info(class_info):
	class_info_cleaned = {}
	class_info_cleaned['dt'] = int(time.time())
	class_info_cleaned['class'] = class_info['id']
	class_info_cleaned['course'] = class_info['course']
	class_info_cleaned['name'] = class_info['label']
	class_info_cleaned['short_name'] = class_info['shortLabel']
	class_info_cleaned['description'] = class_info['description']
	class_info_cleaned['semesters'] = class_info['semester']
	class_info_cleaned['units'] = [int(x) for x in class_info['units'].split('-')]
	class_info_cleaned['instructors'] = {'spring': class_info['spring_instructors'], 'fall': class_info['fall_instructors']}
	class_info_cleaned['stellar_url'] = get_stellar_url(class_info['id'])
	class_info_cleaned['class_site'] = get_class_site(class_info['id'])
	class_info_cleaned['evaluation'] = get_subject_evauluation(class_info['id'])
	class_info_cleaned['textbooks'] = get_textbook_info(class_info['id'], class_info_cleaned['semesters'])

	excludes = ['staff']
	def test_instructor(instructor):
		instructor = instructor.lower()
		for phrase in excludes:
			if phrase in instructor:
				return False
		return True

	for key, instructor_set in class_info_cleaned['instructors'].iteritems():
		class_info_cleaned['instructors'][key] = [instructor for instructor in instructor_set if test_instructor(instructor)]
			

	return class_info_cleaned

def update_recents_with_class(class_obj):
	recent_entry = recents.find_one({'class': class_obj.id})
	if recent_entry:
		if (time.time() - recent_entry['dt']) > 600:
			recents.update({'class': class_obj.id}, {'$set':{'dt': int(time.time())}})
	else:
		recents.insert({'class': class_obj.id, 'dt': int(time.time()), 'display_name': class_obj.display_name(), 'description': class_obj.summary()})

def get_stellar_url(class_id):
	url = "https://stellar.mit.edu/S/course/%s/%s/%s/" % (class_id.split('.')[0], STERM, class_id)
	r = requests.get(url)
	if r.url == 'https://stellar.mit.edu/stellar-error/404.html':
		url = "https://stellar.mit.edu/S/course/%s/%s/%s/" % (class_id.split('.')[0], STERM_LAST, class_id)
		r = requests.get(url)
	if r.url == 'https://stellar.mit.edu/stellar-error/404.html':
		return None
	else:
		return r.url

def get_google_site_guess(class_id):
		br = mechanize.Browser()
		br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:18.0) Gecko/20100101 Firefox/18.0 (compatible;)'),('Accept', '*/*')]
		br.set_handle_robots(False)
		br.open("http://www.google.com/search?&q=MIT+{q}&btnG=Google+Search&inurl=https".format(q=class_id.replace(' ', '+')))
		for link in br.links():
			url = link.url
			if 'mit.edu' in url and 'stellar' not in url and 'google' not in url and 'http' in url:
				return url

def get_class_site(class_id):
	url = "http://course.mit.edu/{class_id}".format(class_id=class_id)
	try:
		r = requests.get(url)
	except requests.exceptions.SSLError:
		r = requests.get(url, verify=False, cert='cert.pem')
	if 'stellar' in r.url or 'course.mit.edu' in r.url:
		google_guess = get_google_site_guess(class_id)
		if google_guess:
			r = requests.get(google_guess)
	soup = BeautifulSoup(r.text)
	try:
		title = soup.find('title').string
	except AttributeError:
		title = "{class_id} Class Site".format(class_id=class_id)
	if 'MIT OpenCourseWare' in title:
		title = title.split('|')[0]
	return (title.strip(), r.url)

def get_subject_evauluation(class_id):
	url = "https://edu-apps.mit.edu/ose-rpt/subjectEvaluationSearch.htm?subjectCode={class_id}&search=Search".format(class_id=class_id)
	try:
		response = auth_browser.open(url)
	except Exception:
		response = auth_browser.open(url)
	response_text = response.read()
	if 'Welcome, please identify yourself to access MIT services.' in response_text:
		init_auth_browser()
		response = auth_browser.open(url)
		response_text = response.read()
	soup = BeautifulSoup(response_text)
	for link in auth_browser.links():
		if 'subjectEvaluationReport' in link.url:
			date = str(soup.find('a', text=link.text).next_sibling).replace("End of Term","").strip()
			response = auth_browser.follow_link(link)
			break
	soup = BeautifulSoup(response.read())
	rating = soup.find('strong', text='Overall rating of subject: ')
	percentage = soup.find('strong', text='Response rate:')
	return (str(rating.next_sibling).strip(), str(percentage.next_sibling).strip(), date)

def get_textbook_info(class_id, semesters):
	pairing = {'SP': 'Spring', 'FA': 'Fall'}
	if pairing[TERM[-2:]] in semesters:
		term = TERM
	else:
		term = TERM_LAST
	url = "http://sisapp.mit.edu/textbook/books.html?Term={term}&Subject={class_id}".format(term=TERM, class_id=class_id)
	soup = BeautifulSoup(requests.get(url).text)
	textbooks = {'dt': time.time()}
	sections = {}
	titles = set()
	asin = set()
	for h2 in soup.findAll('h2'):
		book_category = []
		tbody = h2.next_sibling.next_sibling.contents[3]
		for tr in tbody.findAll('tr'):
			book = {}
			contents = filter(lambda x: x != '\n', tr.contents)
			for i, prop in enumerate(['author', 'title', 'publisher', 'isbn', 'price']):
				book[prop] = clean_html(contents[i].text)
			if 'Course Has No Materials' in book['title']:
				continue
			book['title'] = process_title(book['title'], book['author'], titles)
			book['retail'] = book['price'].replace("$","")
			del book['price']
			amazon_info = get_amazon_info(book['isbn'], book['title'], book['author'])
			book = dict(book.items() + amazon_info.items())
			if book['asin'] not in asin:
				book_category.append(book)
				asin.add(book['asin'])
		if len(book_category) > 0:
			sections[clean_html(h2.string)] = book_category
	textbooks["sections"] = sections
	return textbooks

def doItemSeach(Keywords,SearchIndex):
	i = 1
	while i <= 5:
		try:
			response = amazon.ItemSearch(Keywords=Keywords, SearchIndex=SearchIndex)
			return response
		except Exception:
			time.sleep(.5*i)
			i += 1

def doItemLookup(ItemId,ResponseGroup):
	i = 1
	while i <= 5:
		try:
			response = amazon.ItemLookup(ItemId=ItemId, ResponseGroup=ResponseGroup)
			return response
		except Exception:
			time.sleep(.5*i)
			i += 1

def get_amazon_info(isbn, title, author):
	if '[Ebook]' in title:
		title = title.replace("[Ebook]","")
		title = "{title} ebook".format(title=title)
	d = {'asin': None}
	response = doItemSeach(Keywords=isbn, SearchIndex="Books")
	if not response:
		return d
	root = objectify.fromstring(response)
	if root.Items.TotalResults == 0:
		response = doItemSeach(Keywords="{title} by {author}".format(title=title, author=author), SearchIndex='All')
		if not response:
			return d
		root = objectify.fromstring(response)
	if root.Items.TotalResults == 0:
		response = doItemSeach(Keywords=title, SearchIndex='All')
		if not response:
			return d
		root = objectify.fromstring(response)
	try:
		response = doItemLookup(ItemId=root.Items.Item.ASIN.text, ResponseGroup='ItemAttributes,Offers,OfferSummary')
		if not response:
			return d
		product = objectify.fromstring(response).Items.Item
	except AttributeError:
		return d
	d['asin'] = product.ASIN.text
	d['title'] = product.ItemAttributes.Title.text
	try:
		d['author'] = product.ItemAttributes.Author.text
	except AttributeError:
		pass
	try:
		d['new'] = (product.OfferSummary.LowestNewPrice.FormattedPrice.text).replace("$","")
		d['used'] = (product.OfferSummary.LowestUsedPrice.FormattedPrice.text).replace("$","")
		d['availability'] = product.Offers.Offer.OfferListing.Availability.text
	except AttributeError:
		pass
	try:
		d['saved'] = product.Offers.Offer.OfferListing.PercentageSaved.text
	except AttributeError:
		pass
	try:
		d['prime'] = True if product.Offers.Offer.OfferListing.IsEligibleForSuperSaverShipping.text == 1 else False
	except AttributeError:
		pass
	return d

def process_title(title, author, titles):
	
	replacements = {"W/6 Mo": "With 6 Month", " + ": " and ", "+": " and "}
	removals = ["4e", "(Cs)", ">Ic", "and Study Guide"]
	
	if "Ebk" in title and len(titles) > 0:
		Levenshtein_ratios = dict()
		for t in titles:
			Levenshtein_ratios[t[0]] = Levenshtein.ratio(t[1], title + " by " + author)
		title = max(Levenshtein_ratios.iteritems(), key=operator.itemgetter(1))[0]
		return "[Ebook] " + title
		
	else:
		for k,v in replacements.iteritems():
			title = title.replace(k,v)
		for v in removals:
			title = title.replace(v,"")
		if title not in titles:
			titles.add((title, title + " by " + author))
		return title.strip()

def check_class_json(class_id):
	loaded = classes.find_one({'class': class_id}) != None
	return json.dumps({'loaded': loaded})

def check_class(class_id):
	loaded = classes.find_one({'class': class_id}) != None
	return loaded

def check_group(class_ids):
	loaded = None not in [classes.find_one({'class': class_id}) for class_id in class_ids]
	return loaded

def save_group(group_obj, group_name):
	global group_objects
	if not g.user:
		return json.dumps({"error": True, "message": "You must be logged in to do that."})
	group_name = group_name.replace(' ','')
	if not re.match('^[\w]+$', group_name):
		return json.dumps({"error": True, "message": "The group name must be alphanumeric."})
	if groups.find_one({"name": group_name}):
		return json.dumps({"error": True, "message": "That group name is already taken."})
	group_info = {}
	group_info['named'] = True
	group_info['name'] = group_name
	group_info['user_id'] = g.user.get_id()
	group_info['class_ids'] = ",".join(group_obj.class_ids)
	named_group_obj = MITClassGroup(group_info)
	group_objects[group_name] = named_group_obj
	groups.insert(named_group_obj.to_dict())
	flash('{name} was successfully created!'.format(name=group_name), 'success')
	return json.dumps({"error": False})

def tb_id(textbook):
	if textbook['asin']:
		return textbook['asin']
	elif textbook['isbn']:
		return textbook['isbn']
	else:
		return md5(textbook['title'])

def get_mit_info(email):
		username = email[:email.find("@")]
		url = "http://web.mit.edu/bin/cgicso?options=general&query=%s" % (username)
		r = requests.get(url)
		html = r.text
		soup = BeautifulSoup(html)
		pre = soup.find("pre")
		if pre.text.find("No matches") == -1:
			l = [x.split(":")[-1].strip() for x in pre.text.split("\n")]
			return (l[0], l[2], l[3]) #name, dorm, year

def sell_textbook(class_id, tb_id, form):
	d = {}
	d['tb_id'] = tb_id
	d['price'] = int(form.get('price'))
	d['class_id'] = class_id
	d['location'] = form.get('location')
	d['dt'] = datetime.datetime.utcnow()
	d['email'] = form.get('email')
	d['condition'] = form.get('condition')
	info = get_mit_info(form.get('email'))
	if info:
		d['name'] = info[0]
		d['address'] = info[1]
		d['year'] = info[2]
	offers.insert(d)

def remove_offer(offer_id):
	offer = offers.find_one({"_id": ObjectId(offer_id)})
	if offer and g.user and g.user.get_id() == offer['email']:
		offers.remove({"_id": ObjectId(offer_id)})

def delete_group(group_id):
	group = groups.find_one({"name": group_id})
	if group and g.user.get_id() == group['user_id']:
		groups.remove({"name": group_id})

def blacklist_class(class_id):
	b = blacklist.find_one({'class_id': class_id})
	if b:
		blacklist.update({'class_id': class_id}, {"$inc": {"counter": 1}})
		if b['counter'] + 1 >= min(3, b['delay']):
			blacklist.update({'class_id': class_id}, {"$inc": {"delay": 1}, "$set": {"counter": 0}})
	else:
		blacklist.insert({'class_id': class_id, 'delay': 2, 'counter': 0})

def get_blacklist(classes):
	penalty = 1
	for c in classes:
		b = blacklist.find_one({"class_id": c})
		if b:
			penalty *= b['delay']
	return 1 + (penalty-1)/2.5

