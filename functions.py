#!/usr/bin/env python

from setup import *
import json, hashlib, time, datetime, requests, mechanize, Levenshtein, operator
from bs4 import BeautifulSoup
from models.mitclass import MITClass
from models.mitclassgroup import MITClassGroup

class_objects = {}
group_objects = {}

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
	return hashlib.md5(s).hexdigest()

def clean_html(html):
	return html.strip().replace("\n"," ").encode('ascii','xmlcharrefreplace')

def get_class(class_id):
	global class_objects
	if class_id in class_objects:
		return class_objects[class_id]
	class_info = classes.find_one({"class": class_id})
	if class_info and (time.time() - class_info['dt']) < CACHE_FOR:
		class_obj = MITClass(class_info)
		class_objects[class_id] = class_obj
		return class_obj
	class_info = fetch_class_info(class_id)
	if class_info:
		class_obj = MITClass(class_info)
		class_objects[class_id] = class_obj
		classes.update({"class": class_obj.id}, {"$set": class_obj.to_dict()}, upsert=True)
		return class_obj

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

def update_recents_with_class(class_id):
	recent_entry = recents.find_one({'class': class_id})
	if recent_entry:
		if (time.time() - recent_entry['dt']) > 600:
			recents.update({'class': class_id}, {'$set':{'dt': int(time.time())}})
	else:
		recents.insert({'class': class_id, 'dt': int(time.time())})

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
	title = soup.find('title').string
	if 'MIT OpenCourseWare' in title:
		title = title.split('|')[0]
	return (title.strip(), r.url)

def get_subject_evauluation(class_id):
	url = "https://edu-apps.mit.edu/ose-rpt/subjectEvaluationSearch.htm?subjectCode={class_id}&search=Search".format(class_id=class_id)
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
	textbooks = {}
	titles = set()
	for h2 in soup.findAll('h2'):
		book_category = []
		tbody = h2.next_sibling.next_sibling.contents[3]
		for tr in tbody.findAll('tr'):
			book = {}
			contents = filter(lambda x: x != '\n', tr.contents)
			for i, prop in enumerate(['author', 'title', 'publisher', 'isbn', 'price']):
				book[prop] = clean_html(contents[i].text)
			book['title'] = process_title(book['title'], book['author'], titles)
			book_category.append(book)
		textbooks[clean_html(h2.string)] = book_category
	return textbooks

def process_title(title, author, titles):
	
	replacements = {"W/6 Mo": "With 6 Month", " + ": " and ", "+": " and "}
	removals = ["4e", "(Cs)", ">Ic"]
	
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
		return title 

if __name__ == '__main__':
	print get_textbook_info('14.01')
