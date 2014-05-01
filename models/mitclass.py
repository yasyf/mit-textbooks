from setup import *
import datetime, calendar, json, re
from flask import url_for

class MITClass():
	"""MIT Class Object"""
	def __init__(self, class_info):
		self.dt = datetime.datetime.fromtimestamp(class_info['dt'])
		self.id = class_info['class']
		self.master_subject_id = class_info['master_subject_id']
		self.course = class_info['course']
		self.name = class_info['name']
		self.short_name = class_info['short_name']
		self.description = class_info['description']
		self.prereqs = class_info['prereqs']
		self.lecture = class_info['lecture']
		self.location = class_info['location']
		self.hass = class_info['hass']
		self.semesters = class_info['semesters']
		self.units = class_info['units']
		self.instructors = class_info['instructors']
		self.stellar_url = class_info['stellar_url']
		self.class_site = tuple(class_info['class_site'])
		self.evaluation = tuple(class_info['evaluation'])
		self.textbooks = class_info['textbooks']
		self.grad = class_info['grad'] if 'grad' in class_info else False
		self._image = None

	def to_dict(self):
		d = {}
		d['dt'] = calendar.timegm(self.dt.utctimetuple())
		d['class'] = self.id
		d['master_subject_id'] = self.master_subject_id
		d['course'] = self.course
		d['name'] = self.name
		d['short_name'] = self.short_name
		d['description'] = self.description
		d['prereqs'] = self.prereqs
		d['lecture'] = self.lecture
		d['location'] = self.location
		d['hass'] = self.hass
		d['semesters'] = self.semesters
		d['units'] = self.units
		d['instructors'] = self.instructors
		d['stellar_url'] = self.stellar_url
		d['class_site'] = self.class_site
		d['evaluation'] = self.evaluation
		d['textbooks'] = self.textbooks
		d['grad'] = self.grad
		return d

	def json(self):
		d = self.to_dict()
		del d['dt']
		d['stellar_url'] = url_for('stellar_view', class_id=self.id, _external=True)
		d['class_site'] = url_for('site_view', class_id=self.id, _external=True)
		return d

	def image(self):
		if self._image:
			return self._image
		for section in self.textbooks['sections'].values():
			for book in section:
				if 'image' in book:
					self._image = book['image']
					return self._image

	def safe_id(self):
		return self.id.replace(".","")

	def display_name(self):
		return '{id} {name}'.format(id=self.id, name=self.name)

	def summary(self):
		if len(self.description) < 150:
			return self.description
		else:
			return self.description[:150] + "..."

	def current_instructors(self):
		if TERM[-2:] == 'SP' and 'Spring' in self.semesters:
			return self.instructors['spring']
		elif TERM[-2:] == 'FA' and 'Fall' in self.semesters:
			return self.instructors['fall']
		else:
			return self.instructors.values()[0]

	def is_currently_available(self):
		pairing = {'SP': 'Spring', 'FA': 'Fall'}
		return pairing[TERM[-2:]] in self.semesters

	def formatted_availability(self):
		if len(self.semesters) == 1:
			return '{semester} semester'.format(semester=self.semesters[0])
		else:
			semesters_string = '{first} and {last}'.format(first=", ".join(self.semesters[:-1]), last=self.semesters[-1])
			return '{semesters} semesters'.format(semesters=semesters_string)

	def formatted_summarized_availability(self):
		availability = self.semesters[:]
		for suffix, name in [('SP', 'Spring'), ('FA', 'Fall')]:
			if TERM[-2:] == suffix and name in availability:
				availability[availability.index(name)] = "<span class='now'>{name}</span>".format(name=name)
				break
		return ', '.join(availability)


	def formatted_units(self):
		return '-'.join([str(x) for x in self.units])

	def class_site_url(self):
		return self.class_site[1]

	def stellar_site_url(self):
		return self.stellar_url

	def ocw_site_url(self):
		return self.class_site[1] if 'ocw.mit.edu' in self.class_site[1] else None

	def offers(self, tb_id):
		return offers.find({"class_id": self.id, "tb_id": tb_id}).limit(3)

	def has_local(self):
		return offers.find({"class_id": self.id}).count() > 0

	def formatted_prereqs(self):
		return re.sub(re.compile(r'([\w]{1,3}\.[0-9]{2,3}[\w]{0,1})'),r'<a href="http://textbooksearch.mit.edu/class/\1">\1</a>', self.prereqs)

	def formatted_lecture(self):
		d = {'M': 'Mondays', 'T':'Tuesdays', 'W': 'Wednesdays', 'R': 'Thursdays', 'F': 'Fridays'}
		times = []
		for group in self.lecture.split(','):
			m = re.match(re.compile(r'([A-Z]{1,5})(?: EVE \()?([0-9]{0,2})\.?([0-9]{0,2})-?([0-9]{0,2})\.?([0-9]{0,2})( [A-Z]{2})?\)?'), group)
			if m:
				days = [d[x] for x in list(m.group(1))]
				days = ', '.join(days[:-1]) + ' and ' + days[-1] if len(days) > 1 else days[0]
				start_hour = m.group(2)
				start_minute = m.group(3) or '00'
				end_hour = m.group(4) or int(start_hour) + 1
				end_minute = m.group(5) or '00'
				if m.group(6):
					start_a = m.group(6)
					end_a = m.group(6)
				else:
					start_a = 'AM' if (int(start_hour) < 12 and int(start_hour) > 8) else 'PM'
					end_a = 'AM' if (int(end_hour) < 12 and int(end_hour) > 8) else 'PM'
				time = "{0}:{1} {2} to {3}:{4} {5}".format(start_hour, start_minute, start_a, end_hour, end_minute, end_a)
				times.append(time + ' on ' + days)
				return 'from ' + ', '.join(times[:-1]) + ' and ' + times[-1] if len(times) > 1 else times[0]
			else:
				return 'at ' + self.lecture
