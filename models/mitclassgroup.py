from setup import *

class MITClassGroup():
	"""MIT Class Group Object"""
	def __init__(self, group_info):
		if group_info['named']:
			self.named = True
			self.hash = None
			self.name = group_info['name']
			self.user_id = group_info['user_id']
		else:
			self.named = False
			self.hash = group_info['hash']
			self.name = None
			self.user_id = None
		self.class_ids = group_info['class_ids'].split(',')

	def to_dict(self):
		d = {}
		if self.named:
			d['named'] = True
			d['name'] = self.name
			d['user_id'] = self.user_id
		else:
			d['named'] = False
			d['hash'] = self.hash
		d['class_ids'] = ",".join(self.class_ids)
		return d

	def slug(self):
		if self.hash:
			return self.hash
		elif self.name:
			return self.name
		else:
			self.hash = md5(",".join(self.class_ids))
			return self.hash

	def display_name(self):
		if self.name:
			return self.name
		else:
			return ", ".join(self.class_ids)

	def display_description(self):
		if self.name:
			return 'Buy and sell both new and used textbooks for the textbook group {name} at MIT Textbooks.'.format(name=self.name)
		else:
			classes_string = '{first} and {last}'.format(first=", ".join(self.class_ids[:-1]), last=self.class_ids[-1])
			return 'Buy and sell both new and used textbooks for {classes} at MIT Textbooks.'.format(classes=classes_string)
		