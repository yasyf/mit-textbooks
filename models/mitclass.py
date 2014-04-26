from setup import *
import datetime, calendar, json
from flask import url_for

class MITClass():
	"""MIT Class Object"""
	def __init__(self, class_info):
		self.dt = datetime.datetime.fromtimestamp(class_info['dt'])
		self.id = class_info['class']
		self.course = class_info['course']
		self.name = class_info['name']
		self.short_name = class_info['short_name']
		self.description = class_info['description']
		self.semesters = class_info['semesters']
		self.units = class_info['units']
		self.instructors = class_info['instructors']
		self.stellar_url = class_info['stellar_url']
		self.class_site = tuple(class_info['class_site'])
		self.evaluation = tuple(class_info['evaluation'])
		self.textbooks = class_info['textbooks']

	def to_dict(self):
		d = {}
		d['dt'] = calendar.timegm(self.dt.utctimetuple())
		d['class'] = self.id
		d['course'] = self.course
		d['name'] = self.name
		d['short_name'] = self.short_name
		d['description'] = self.description
		d['semesters'] = self.semesters
		d['units'] = self.units
		d['instructors'] = self.instructors
		d['stellar_url'] = self.stellar_url
		d['class_site'] = self.class_site
		d['evaluation'] = self.evaluation
		d['textbooks'] = self.textbooks
		return d

	def json(self):
		d = self.to_dict()
		del d['dt']
		d['stellar_url'] = url_for('stellar_view', class_id=self.id, _external=True)
		d['class_site'] = url_for('site_view', class_id=self.id, _external=True)
		return json.dumps(d)

	def display_name(self):
		return '{id} {name}'.format(id=self.id, name=self.name)

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
