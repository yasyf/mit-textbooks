from setup import *

class MITUser():
	def __init__(self, email, name):
		self.email = email
		self.name = name
		obj =  users.find_one({"email": self.email})
		if not obj:
			users.insert({"name": self.name, "email": self.email, "dt": datetime.datetime.utcnow()})
		elif obj['dt'] < (datetime.datetime.utcnow() - datetime.timedelta(days=1)):
			users.update({'_id': obj['_id']}, {'$set': {'dt': datetime.datetime.utcnow()}})

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