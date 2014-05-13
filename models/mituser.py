from setup import *

class MITUser():
	def __init__(self, email, name):
		self.email = email
		self.name = name
		self.obj = users.find_one({"email": self.email})
		if not self.obj:
			users.insert({"name": self.name, "email": self.email, "dt": datetime.datetime.utcnow()})
			self.obj = users.find_one({"email": self.email})
		elif self.obj['dt'] < (datetime.datetime.utcnow() - datetime.timedelta(days=1)):
			users.update({'_id': self.obj['_id']}, {'$set': {'dt': datetime.datetime.utcnow()}})

	def get_id(self):
		return self.email

	def is_admin(self):
		return self.email == os.getenv('admin_email')

	def get_groups(self):
		return groups.find({"named": True, "user_id": self.get_id()})

	def get_postings(self):
		return offers.find({"email": self.get_id()})

	def kerberos(self):
		return self.email.split("@")[0]

	def add_recent_class(self, c):
		try:
			recents = self.obj['recents']
		except KeyError:
			recents = []
		if c in recents:
			if recents[-1] == c:
				return
			recents.remove(c)
		recents.append(c)
		users.update({'_id': self.obj['_id']}, {'$set': {'recents': recents}})
