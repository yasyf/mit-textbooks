from setup import *
import datetime, calendar, json, re, random
from flask import url_for

def event_to_start_end(day, m):
	day_to_i = dict(zip(list('MTWRF'),range(5)))
	today = datetime.datetime.today()
	base = datetime.datetime(today.year, today.month, today.day) - datetime.timedelta(days=today.weekday())
	date = base + datetime.timedelta(days=day_to_i[day])
	start_hour = int(m.group(2))
	start_minute = int(m.group(3) or 0)
	end_hour = int(m.group(4) or start_hour + 1)
	end_minute = int(m.group(5) or 0)
	start = date + datetime.timedelta(hours=start_hour, minutes=start_minute)
	end = date + datetime.timedelta(hours=end_hour, minutes=end_minute)
	if m.group(6):
		if m.group(6) == "PM":
			start += datetime.timedelta(hours=12)
			end += datetime.timedelta(hours=12)
	else:
		if start_hour < 8:
			start += datetime.timedelta(hours=12)
		if end_hour < 8:
			end += datetime.timedelta(hours=12)
	return start, end


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
		self.coreqs = class_info['coreqs']
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
		d['coreqs'] = self.coreqs
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

	def units_detail(self):
		l = []
		for i, d in enumerate(['lecture', 'lab', 'homework']):
			if self.units[i]:
				l.append("{u} {d}".format(u=self.units[i], d=d))
		return ', '.join(l)

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
		formatted = ["<a href='http://textbooksearch.mit.edu/class/{c}'>{c}</a>".format(c=c) for c in self.prereqs]
		return ', '.join(formatted[:-1]) + ', and ' + formatted[-1] + ' as prerequisites' if len(formatted) > 1 else formatted[0] + ' as a prerequisite'

	def formatted_coreqs(self):
		formatted = ["<a href='http://textbooksearch.mit.edu/class/{c}'>{c}</a>".format(c=c) for c in self.coreqs]
		return ', '.join(formatted[:-1]) + ', and ' + formatted[-1] + ' as corequisites' if len(formatted) > 1 else formatted[0] + ' as a corequisite'

	def formatted_prereqs_summary(self):
		formatted = ["<a href='http://textbooksearch.mit.edu/class/{c}'>{c}</a>".format(c=c) for c in self.prereqs]
		return ', '.join(formatted[:-1]) + ', and ' + formatted[-1] if len(formatted) > 1 else formatted[0]

	def formatted_coreqs_summary(self):
		formatted = ["<a href='http://textbooksearch.mit.edu/class/{c}'>{c}</a>".format(c=c) for c in self.coreqs]
		return ', '.join(formatted[:-1]) + ', and ' + formatted[-1] if len(formatted) > 1 else formatted[0]

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

	def events(self):
		events = []
		colors = ["#e72510", "#02a5de", "#cb5c10", "#4653de", "#8a02de", "#e08b27", "#3c5fde", "#02d5de", "#4BAD00", "##3366FF", "#6633FF", "#CC33FF", "#FF33CC", "#33CCFF", "#003DF5", "#FF3366", "#FF6633"]
		color = random.choice(colors)
		i = 0
		for group in self.lecture.split(','):
			m = re.match(re.compile(r'([A-Z]{1,5})(?: EVE \()?([0-9]{0,2})\.?([0-9]{0,2})-?([0-9]{0,2})\.?([0-9]{0,2})( [A-Z]{2})?\)?'), group)
			if m:
				for day in m.group(1):
					d = {'id':"{id}#{i}".format(id=self.id, i=i), 'text': self.id, 'color': color}
					i += 1
					start, end = event_to_start_end(day, m)
					if end - start > datetime.timedelta(hours=1):
						d['text'] += '<br>' + self.short_name
					d['start_date'] = start.strftime('%m/%d/%Y %H:%M')
					d['end_date'] = end.strftime('%m/%d/%Y %H:%M')
					events.append(d)
		return events

	def events_raw(self):
		events = []
		for group in self.lecture.split(','):
			m = re.match(re.compile(r'([A-Z]{1,5})(?: EVE \()?([0-9]{0,2})\.?([0-9]{0,2})-?([0-9]{0,2})\.?([0-9]{0,2})( [A-Z]{2})?\)?'), group)
			if m:
				days = m.group(1)
				d = {}
				start, end = event_to_start_end(days[0], m)
				d['days'] = days
				d['start'] = start
				d['end'] = end
				events.append(d)
		return events

	def gcal_events(self):
		d_to_d = {'M': 'MO', 'T': 'TU', 'W': 'WE', 'R': 'TH', 'F': 'FR'}
		events = []
		for e in self.events_raw():
			d = {}
			d['summary'] = "{c} ({short})".format(c=self.id, short=self.short_name)
			d['description'] = self.description
			start = datetime.datetime(TERM_START.year, TERM_START.month, TERM_START.day, e['start'].hour, e['start'].minute) + datetime.timedelta(days=e['start'].weekday() - TERM_START.weekday())
			end = datetime.datetime(TERM_START.year, TERM_START.month, TERM_START.day, e['end'].hour, e['end'].minute) + datetime.timedelta(days=e['start'].weekday() - TERM_START.weekday())
			d['start'] = {'dateTime': start.isoformat('T'), 'timeZone': 'America/New_York'}
			d['end'] = {'dateTime': end.isoformat('T'), 'timeZone': 'America/New_York'}
			days = [d_to_d[day] for day in e['days']]
			d['recurrence'] = ["RRULE:FREQ=WEEKLY;BYDAY={days};UNTIL={until}".format(until=TERM_END.strftime("%Y%m%dT%H%M%SZ"), days=','.join(days))]
			d['location'] = self.location
			d['source'] = url_for('class_view', class_id=self.id, _external=True)
			events.append(d)
		return events



