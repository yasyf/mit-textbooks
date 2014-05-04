#!/usr/bin/env python

from setup import *
import json, hashlib, time, datetime, requests, mechanize, Levenshtein, operator, time, urllib, re, traceback, bleach, csv, StringIO
from flask import g, flash, url_for
from bs4 import BeautifulSoup
from lxml import objectify
from bson.objectid import ObjectId
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

def send_to_worker(class_id, update=False, group=False):
	d = {'class_id': class_id, 'update': update, 'group': group}
	if not queue.find_one(d):
		d['time'] = time.time()
		queue.insert(d)

def error_mail(e):
	message = sendgrid.Mail()
	message.add_to(os.getenv('admin_email'))
	message.set_subject('500 Internal Server Error @ MIT Textbooks')
	trace = traceback.format_exc() 
	message.set_html(request.url + '<br><br>' + e.message + '<br><br><pre>' + trace + '</pre>')
	message.set_text(request.url + '\n\n' + e.message + '\n\n' + trace)
	message.set_from('MIT Textbooks <tb_support@mit.edu>')
	try:
		print sg.send(message)
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
	return bleach.clean(html.replace("\n"," ").replace("\t"," ").encode('ascii','xmlcharrefreplace'), tags=[], strip=True).strip()

def get_user(email, name):
	global user_objects
	if not email:
		return None
	if email in user_objects:
		return user_objects[email]
	else:
		u = MITUser(email, name)
		user_objects[email] = u
		return u

def get_class(class_id):
	global class_objects
	class_id = format_class(class_id)
	if class_id in class_objects:
		return class_objects[class_id]
	class_info = classes.find_one({"class": class_id})
	if class_info and (time.time() - class_info['dt']) < CACHE_FOR:
		if 'error' in class_info:
			return None
		if (time.time() - class_info['textbooks']['dt']) > (CACHE_FOR/4.0) and not is_worker:
			send_to_worker(class_id, update=True)
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

def format_class(c):
	c = c.upper()
	if c[-1] == 'J':
		c = c[:-1]
	return c.strip()

def is_int(value):
  try:
	int(value)
	return True
  except ValueError:
	return False

def prepare_class_hash(classes):
	classes = ','.join(list(sorted(set([format_class(clean_html(c)) for c in classes]), key=lambda x: float(x) if is_float(x) else int(x.split('.')[0]) if '.' in x and is_int(x.split('.')[0]) else x)))
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
	json_data = response.json(strict=False)["items"]
	relevant = {}
	_id = clean_html(class_id)
	for element in json_data:
		if element['type'] == 'Class' and element['id'] == _id:
			relevant['class'] = element
		elif element['type'] == 'LectureSession' and element['section-of'] == _id:
			relevant['lecture'] = element
	return relevant

def fetch_class_info(class_id):
	url = "http://coursews.mit.edu/coursews/?term={term}&courses={course_number}".format(term=TERM, course_number=class_id.split('.')[0])
	class_info = check_json_for_class(url, class_id)
	if not class_info:
		url = "http://coursews.mit.edu/coursews/?term={term}&courses={course_number}".format(term=TERM_LAST, course_number=class_id.split('.')[0])
		class_info = check_json_for_class(url, class_id)
	if class_info:
		return clean_class_info(class_info['class'], class_info['lecture'] if 'lecture' in class_info else None)
	else:
		return manual_class_scrape(class_id)

def custom_parse_instructors(instructors):
	new_intructors = []
	for i in instructors:
		new_intructors.extend([x.split(':')[-1] for x in i.split('<br>')])
	return new_intructors

def manual_class_scrape(class_id):
	try:
		class_info = {}
		class_info['dt'] = int(time.time())
		url = "http://student.mit.edu/catalog/search.cgi?search={class_id}&style=verbatim".format(class_id=class_id)
		html = requests.get(url).text
		if 'No matching subjects found.' in html:
			return
		soup = BeautifulSoup(html)
		ssoup = str(soup)
		name = clean_html(soup.find("h3").text).split(' ')
		class_info['class'], class_info['name'] = name[0], ' '.join(name[1:])
		class_info['short_name'] = class_info['name']
		class_info['master_subject_id'] = class_info['class']
		class_info['course'] = class_info['class'].split('.')[0]
		when = []
		for when_when,when_img in {"Fall": "fall", "IAP": "iap", "Spring": "spring"}.iteritems():
			when_img_src = "/icns/%s.gif" % (when_img)
			if soup.find("img",src=when_img_src) != None:
				when.append(when_when)
		class_info['semesters'] = when
		class_info['hass'] = ''
		for img in soup.find_all('img'):
			if img.get('src') == "/icns/hassS.gif":
				class_info['hass'] = 'S'
			elif img.get('src') == "/icns/hassA.gif":
				class_info['hass'] = 'A'
			elif img.get('src') == "/icns/hassH.gif":
				class_info['hass'] = 'H'
			elif img.get('src') == "/icns/grad.gif":
				class_info['grad'] = True
			elif img.get("src") == "/icns/hr.gif":
				nextTag = img.findNext()
				if nextTag.name == "br":
					text = ""
					while nextTag.nextSibling.name != "br":
						text += clean_html(nextTag.nextSibling)
						nextTag = nextTag.nextSibling
					instructors = nextTag.findNext().findNext().text
					all_instructors = []
					for professor in instructors.split(", "):
						prof = professor.split(". ")
						if professor not in ["Jr.","Sr."]:
							all_instructors.append(professor)
					final_instructors = [clean_html(i) for i in custom_parse_instructors(all_instructors)]
					class_info['instructors'] = {k.lower():(final_instructors if k in when else []) for k in ['Fall', 'Spring']}
		
		prereq_index_start = ssoup.find("Prereq: ") + 8
		if prereq_index_start:
			prereq_index_end = ssoup.find("<br/>",prereq_index_start)-1
			prereq_info = clean_html(ssoup[prereq_index_start:prereq_index_end])
		else:
			prereq_info = ''
		class_info['prereqs'], class_info['coreqs']  = process_prereqs(prereq_info)
		unit_index_start = ssoup.find("Units: ") + 7
		unit_index_end = ssoup.find("<br/>",unit_index_start)-1
		units_info = clean_html(ssoup[unit_index_start:unit_index_end])
		class_info['units'] = [int(x) for x in units_info.split('-')]
		lecture_node = soup.find('b', text='Lecture:')
		if lecture_node:
			class_info['lecture'] = clean_html(lecture_node.nextSibling.nextSibling.text)
			class_info['location'] = clean_html(lecture_node.nextSibling.nextSibling.nextSibling.nextSibling.text)
		else:
			class_info['lecture'] = ''
			class_info['location'] = ''
		class_info['description'] = text
		class_info['stellar_url'] = get_stellar_url(class_id)
		class_info['class_site'] = get_class_site(class_id)
		class_info['evaluation'] = get_subject_evauluation(class_id)
		class_info['textbooks'] = get_textbook_info(class_id, class_info['semesters'])
		return class_info
	except Exception:
		return

def clean_class_info(class_info, lecture_info):
	class_info_cleaned = {}
	class_info_cleaned['dt'] = int(time.time())
	class_info_cleaned['class'] = class_info['id']
	class_info_cleaned['master_subject_id'] = class_info['master_subject_id'] if 'master_subject_id' in class_info else class_info['id']
	class_info_cleaned['course'] = class_info['course']
	class_info_cleaned['name'] = clean_html(class_info['label'])
	class_info_cleaned['prereqs'], class_info_cleaned['coreqs'] = process_prereqs(clean_html(class_info['prereqs']))
	class_info_cleaned['short_name'] = clean_html(class_info['shortLabel'])
	class_info_cleaned['description'] = clean_html(class_info['description'])
	class_info_cleaned['semesters'] = class_info['semester']
	class_info_cleaned['hass'] = class_info['hass_attribute'][-1:]
	class_info_cleaned['units'] = [int(x) for x in class_info['units'].split('-')]
	class_info_cleaned['instructors'] = {'spring': [clean_html(i) for i in custom_parse_instructors(class_info['spring_instructors'])], 'fall': [clean_html(i) for i in custom_parse_instructors(class_info['fall_instructors'])]}
	class_info_cleaned['stellar_url'] = get_stellar_url(class_info['id'])
	class_info_cleaned['class_site'] = get_class_site(class_info['id'])
	class_info_cleaned['evaluation'] = get_subject_evauluation(class_info['id'])
	class_info_cleaned['textbooks'] = get_textbook_info(class_info['id'], class_info_cleaned['semesters'])
	if lecture_info:
		data = lecture_info['timeAndPlace'].split(' ')
		class_info_cleaned['lecture'], class_info_cleaned['location'] = clean_html(' '.join(data[:-1])), clean_html(data[-1])
	else:
		class_info_cleaned['lecture'], class_info_cleaned['location'] = '', ''

	if class_info_cleaned['course'] == '6':
		eecs_staff = get_eecs_staff(class_info_cleaned['class'])
		class_info_cleaned['instructors']['spring'] = eecs_staff or class_info_cleaned['instructors']['spring']
		class_info_cleaned['instructors']['fall'] = eecs_staff or class_info_cleaned['instructors']['fall']

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

def get_eecs_staff(c):
	data = requests.get('https://eecs.scripts.mit.edu/eduportal/who_is_teaching_what_data_out/F/{y}/'.format(y=datetime.date.today().year)).text
	reader = csv.DictReader(StringIO.StringIO(data), fieldnames=['class','name','first_name','last_name','title'])
	instructors = []
	for row in reader:
		if row['class'] == c and 'Lecturer' in row['title']:
			instructors.append(row['first_name'] + ' ' + row['last_name'])
	def initialize(instructor):
		l = instructor.split(' ') 
		return ' '.join([x[0] + '.' for x in l[:-1]]) + ' ' + l[-1]
	return [initialize(x) for x in instructors]

def process_prereqs(prereqs):
	if not prereqs:
		return [],[]
	d = {'GIR:PHY1': '8.01', 'GIR:CAL1': '18.01','GIR:PHY2': '8.02', 'GIR:CAL2': '18.02', 'GIR:BIOL': '7.012 or equivalent', 'GIR:CHEM': '5.111 or equivalent'}
	for k,v in d.iteritems():
		prereqs = prereqs.replace(k, v)
	coreqs = re.findall(re.compile(r'\[([\w]{1,3}\.[0-9]{2,3}[\w]{0,1})\]'), prereqs)
	prereqs = re.sub(re.compile(r'\[[\w]{1,3}\.[0-9]{2,3}[\w]{0,1}\]'), '', prereqs)
	prereqs = re.findall(re.compile(r'([\w]{1,3}\.[0-9]{2,3}[\w]{0,1})'), prereqs)
	prereqs, coreqs = [x.strip() for x in prereqs], [x.strip() for x in coreqs]
	return prereqs, coreqs

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

def try_url(url):
	try:
		return requests.get(url)
	except requests.exceptions.SSLError:
		return requests.get(url, verify=False, cert='cert.pem')
	except requests.exceptions.TooManyRedirects:
		return None

def get_google_site_guess(class_id):
		br = mechanize.Browser()
		br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:18.0) Gecko/20100101 Firefox/18.0 (compatible;)'),('Accept', '*/*')]
		br.set_handle_robots(False)
		br.open("http://www.google.com/search?&q=MIT+{q}&btnG=Google+Search&inurl=https".format(q=class_id.replace(' ', '+')))
		for link in br.links():
			url = link.url
			if 'mit.edu' in url and 'stellar' not in url and 'textbooksearch' not in url and 'google' not in url and 'http' in url:
				get = try_url(url)
				if get:
					return get

def get_class_site(class_id):
	url = "http://course.mit.edu/{class_id}".format(class_id=class_id)
	r = try_url(url)
	if r is None or 'stellar' in r.url or 'course.mit.edu' in r.url:
		r = get_google_site_guess(class_id)
	soup = BeautifulSoup(r.text)
	try:
		title = soup.find('title').string
		if 'no title' in title.lower():
			title = "{class_id} Class Site".format(class_id=class_id)
	except AttributeError:
		title = "{class_id} Class Site".format(class_id=class_id)
	if 'MIT OpenCourseWare' in title:
		title = title.split('|')[0]
	return (clean_html(title), r.url)

def get_subject_evauluation(class_id):
	try:
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
		for i,link in enumerate(auth_browser.links()):
			if 'subjectEvaluationReport' in link.url:
				date = str(soup.findAll('a')[i].next_sibling).replace("End of Term","").strip()
				response = auth_browser.follow_link(link)
				break
		soup = BeautifulSoup(response.read())
		rating = soup.find('strong', text='Overall rating of subject: ')
		percentage = soup.find('strong', text='Response rate:')
		return (clean_html(str(rating.next_sibling)), clean_html(str(percentage.next_sibling)), date)
	except AttributeError:
		return (None,)

def get_textbook_info(class_id, semesters):
	pairing = {'SP': 'Spring', 'FA': 'Fall'}
	if pairing[TERM[-2:]] in semesters:
		term = TERM
		term_l = TERM_LAST
	else:
		term = TERM_LAST
		term_l = TERM

	textbooks = {'dt': time.time()}
	sections = {}
	titles = set()
	asin = set()

	url = "http://sisapp.mit.edu/textbook/books.html?Term={term}&Subject={class_id}".format(term=term, class_id=class_id)
	html = requests.get(url).text
	if 'No text books are recorded for your request.' in html:
		url = "http://sisapp.mit.edu/textbook/books.html?Term={term}&Subject={class_id}".format(term=term_l, class_id=class_id)
		html = requests.get(url).text
	if 'No text books are recorded for your request.' in html:
		textbooks["sections"] = sections
		return textbooks
	soup = BeautifulSoup(html)

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
			abe_info = get_abe_info(book['isbn'])
			update_new_prices(book, abe_info)
			if book['asin'] not in asin:
				book_category.append(book)
				asin.add(book['asin'])
		if len(book_category) > 0:
			sections[clean_html(h2.string)] = book_category
	textbooks["sections"] = sections
	return textbooks

def get_abe_info(isbn):
	d = {}
	try:
		url = "http://search2.abebooks.com/search?clientkey={key}&outputsize=short&isbn={isbn}&bookcondition=newonly".format(key=os.getenv('abe_key'), isbn=isbn)
		response = str(requests.get(url).text)
		root = objectify.fromstring(response)
		d['new'] = root.Book.listingPrice.text
		listing_url = urllib.quote_plus('http://'+root.Book.listingUrl.text)
		d['purchase'] = ('AbeBooks', "http://affiliates.abebooks.com/c/92729/77416/2029?u={u}".format(u=listing_url))
	except Exception:
		pass
	try:
		url = "http://search2.abebooks.com/search?clientkey={key}&outputsize=short&isbn={isbn}&bookcondition=usedonly".format(key=os.getenv('abe_key'), isbn=isbn)
		response = str(requests.get(url).text)
		root = objectify.fromstring(response)
		d['used'] = root.Book.listingPrice.text
		listing_url = urllib.quote_plus('http://'+root.Book.listingUrl.text)
		d['purchase'] = ('AbeBooks', "http://affiliates.abebooks.com/c/92729/77416/2029?u={u}".format(u=listing_url))
	except Exception:
		pass
	return d

def update_new_prices(book, info):
	for kind in ['new', 'used']:
		if kind in info:
			if not kind in book or float(info[kind]) < float(book[kind]):
				book[kind] = info[kind]
				book['purchase'] = info['purchase']
	return book

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
		response = doItemLookup(ItemId=root.Items.Item.ASIN.text, ResponseGroup='ItemAttributes,Offers,OfferSummary,Images')
		if not response:
			return d
		product = objectify.fromstring(response).Items.Item
	except AttributeError:
		return d
	d['asin'] = product.ASIN.text
	d['title'] = product.ItemAttributes.Title.text

	try:
		d['image'] = product.LargeImage.URL.text
	except AttributeError:
		pass
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
	return {'loaded': loaded}

def check_class(class_id):
	loaded = classes.find_one({'class': class_id}) != None
	return loaded

def check_group(class_ids):
	loaded = None not in [classes.find_one({'class': class_id}) for class_id in class_ids]
	return loaded

def save_group(group_obj, group_name):
	global group_objects
	if not g.user:
		return {"error": True, "message": "You must be logged in to do that."}
	group_name = group_name.replace(' ','')
	if not re.match('^[\w]+$', group_name):
		return {"error": True, "message": "The group name must be alphanumeric."}
	if groups.find_one({"name": group_name}):
		return {"error": True, "message": "That group name is already taken."}
	group_info = {}
	group_info['named'] = True
	group_info['name'] = group_name
	group_info['user_id'] = g.user.get_id()
	group_info['class_ids'] = ",".join(group_obj.class_ids)
	named_group_obj = MITClassGroup(group_info)
	group_objects[group_name] = named_group_obj
	groups.insert(named_group_obj.to_dict())
	flash('{name} was successfully created!'.format(name=group_name), 'success')
	return {"error": False}

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

def unblacklist_class(class_id):
	b = blacklist.find_one({'class_id': class_id})
	if b:
		blacklist.update({'class_id': class_id}, {"$inc": {"counter": -1}})
		if b['counter'] - 1 < 0:
			blacklist.update({'class_id': class_id}, {"$inc": {"delay": -1}, "$set": {"counter": 0}})

def get_blacklist(classes):
	penalty = 1
	for c in classes:
		b = blacklist.find_one({"class_id": c})
		if b:
			penalty *= b['delay']
	return 1 + (penalty-1)/2.5

def sitemap_allows():
	allows = [url_for('index_view', _external=True), url_for('textbooks_view', _external=True)]
	for c in classes.find({}):
		if 'textbooks' not in c:
			continue
		allows.append(url_for('class_view', class_id=c['class'], _external=True))
		allows.append(url_for('overview_view', class_id=c['class'], _external=True))
		if 'class_site' in c:
			allows.append(url_for('site_view', class_id=c['class'], _external=True))
		if 'stellar_url' in c:
			allows.append(url_for('site_view', class_id=c['class'], _external=True))
		allows.append(url_for('class_evaluation_view', class_id=c['class'], _external=True))
		for section in c['textbooks']['sections'].values():
			for book in section:
				if 'asin' in book and book['asin']:
					allows.append(url_for('amazon_product_view', asin=book['asin'], _external=True))
	for gr in groups.find({}):
		allows.append(url_for('group_view', group_id=gr['name'] if 'name' in gr else gr['hash'], _external=True))
	return allows


def reset_class_db(verify=False):
	if not verify:
		return
	all_classes = set()
	for c in classes.find():
		classes.remove(c["_id"])
		all_classes.add(c["class"])
	time.sleep(5)
	for c in all_classes:
		send_to_worker(c)

def check_all_times(classes):
	free = {}
	for j in list('MTWRF'):
		free[j] = {}
		for i in range(7,18):
			free[j][i] = []
			free[j][i+0.5] = []
	overlap = set()
	for c in classes:
		lecture = c.lecture.split(',')
		for group in lecture:
			m = re.match(re.compile(r'([A-Z]{1,5})([0-9]{1,2})\.?([0-9]{0,2})-?([0-9]{0,2})\.?([0-9]{0,2})'), group)
			if m:
				for day in list(m.group(1)):
					start_hour = int(m.group(2))
					if start_hour < 7:
						start_hour += 12
					if m.group(3) == '30':
						start_hour += 0.5
					end_hour = int(m.group(4)) if m.group(4) else start_hour + 1
					if end_hour < 7:
						end_hour += 12
					if m.group(5) == '30':
						end_hour += 0.5
					current = start_hour
					while current < end_hour:
						free[day][current].append(c.id)
						if len(free[day][current]) > 1:
							overlap.add(tuple(free[day][current]))
						current += 0.5
	return overlap

def is_float(n):
	try:
		float(n)
		return True
	except ValueError:
		return False
