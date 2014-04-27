from setup import *

class MITUser():
	def __init__(self, email, name, phone):
		self.email = email
		self.name = name
		self.phone = phone

	def get_id(self):
		return self.email

	def get_groups(self):
		return groups.find({"named": True, "user_id": self.get_id()})