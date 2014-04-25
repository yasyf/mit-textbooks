from setup import *
import datetime, calendar

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
		return d

		