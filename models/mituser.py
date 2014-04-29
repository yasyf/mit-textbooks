from setup import *

class MITUser():
	def __init__(self, email, name, phone):
		self.email = email
		self.name = name
		self.phone = phone
		if users.find_one({"email": self.email}) == None:
			users.insert({"name": self.name, "email": self.email, "phone": self.phone})

	def get_id(self):
		return self.email

	def get_groups(self):
		return groups.find({"named": True, "user_id": self.get_id()})

	def get_postings(self):
		return offers.find({"email": self.get_id()})