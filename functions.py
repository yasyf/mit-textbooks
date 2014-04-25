#!/usr/bin/env python

from setup import *
import json, hashlib, time, datetime, requests
from bs4 import BeautifulSoup
from models.mitclass import MITClass

class_objects = {}

def sha(text):
	return hashlib.sha256(text).hexdigest()

def clean_html(html):
	return html.strip().replace("\n"," ").encode('ascii','xmlcharrefreplace')

def get_class(class_id):
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
		classes.insert(class_obj.to_dict())
		return class_obj

def fetch_class_info(class_id):
	url = "http://coursews.mit.edu/coursews/?term={term}&courses={course_number}".format(term=TERM, course_number=class_id.split('.')[0])
	response = requests.get(url)
	json_data = response.json()["items"]
	for element in json_data:
		if 'id' in element and element['id'] == class_id:
			class_info = element
			break
	class_info_cleaned = {}
	class_info_cleaned['dt'] = int(time.time())
	class_info_cleaned['class'] = class_info['id']
	class_info_cleaned['course'] = class_info['course']
	class_info_cleaned['name'] = class_info['label']
	class_info_cleaned['short_name'] = class_info['shortLabel']
	class_info_cleaned['description'] = class_info['description']
	class_info_cleaned['semesters'] = class_info['semester']
	class_info_cleaned['units'] = class_info['units'].split('-')
	class_info_cleaned['instructors'] = {'spring': class_info['spring_instructors'], 'fall': class_info['fall_instructors']}
	return class_info_cleaned

def update_recents_with_class(class_id):
	recent_entry = recents.find_one({'class': class_id})
	if recent_entry:
		if (time.time() - recent_entry['dt']) > 600:
			recents.update({'class': class_id}, {'dt': int(time.time())})
	else:
		recents.insert({'class': class_id, 'dt': int(time.time())})

if __name__ == '__main__':
	print json.dumps(fetch_class_info('6.01'))