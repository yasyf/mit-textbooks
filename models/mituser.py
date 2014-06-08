from setup import *
import datetime

class MITUser():
	def __init__(self, email, name, create=True):
		self.email = email
		self.name = name
		self.obj = users.find_one({"email": self.email})
		if not self.obj:
			if create and self.email and self.name:
				users.insert({"name": self.name, "email": self.email, "dt": datetime.datetime.utcnow(), 'recents': []})
				self.obj = users.find_one({"email": self.email})
		elif self.obj['dt'] < (datetime.datetime.utcnow() - datetime.timedelta(days=1)):
			users.update({'_id': self.obj['_id']}, {'$set': {'dt': datetime.datetime.utcnow()}})
		if self.obj:
			self.recents = self.obj['recents']
			self.name = self.obj['name'] or name

	def get_id(self):
		return self.email

	def get_password(self):
		secret = os.environ['sk']
		weekday = str(datetime.datetime.utcnow().isocalendar()[2])
		obj_id = str(self.obj['_id'])
		i = abs(hash(weekday + secret + obj_id))
		return str(i)[:5]

	def check_password(self, password):
		if self.is_mobile_locked_out():
			return False
		else:
			users.update({'_id': self.obj['_id']}, {'$inc': {'login_attempts': 1}})
			self.obj = users.find_one({'_id': self.obj['_id']})
			return password == self.get_password()

	def is_logged_in(self):
		return self.obj != None

	def is_mobile_locked_out(self):
		return self.obj.get('login_attempts', 0) > 5

	def reset_mobile_lockout(self):
		users.update({'_id': self.obj['_id']}, {'login_attempts': 0})
		self.obj = users.find_one({'_id': self.obj['_id']})

	def is_admin(self):
		return self.email == os.getenv('admin_email')

	def get_groups(self):
		return groups.find({"named": True, "user_id": self.get_id()})

	def get_postings(self):
		return offers.find({"email": self.get_id()})

	def kerberos(self):
		return self.email.split("@")[0]

	def add_recent_class(self, c):
		if c in self.recents:
			if self.recents[-1] == c:
				return
			self.recents.remove(c)
		self.recents.append(c)
		if len(self.recents) > 50:
			self.recents = self.recents[-50:]
		users.update({'_id': self.obj['_id']}, {'$set': {'recents': self.recents}})
