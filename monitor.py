from functions import *

init_auth_browser()

task = None

def do_get_class(class_id):
	i = 1
	while i <= 5:
		try:
			return get_class(class_id)
		except AttributeError:
			init_auth_browser()
			time.sleep(.5*i)
			i += 1
		except Exception:
			time.sleep(1*i)
			i += 1
	queue.insert(task)

while True:
	task = queue.find_one(sort=[("time", 1)])
	if task:
		queue.remove(task)
		_id = task['class_id']
		print 'Processing {_id}'.format(_id=_id)
		if task['group']:
			group_obj = get_group(_id)
			for c in group_obj.class_ids:
				do_get_class(c)
		elif task['update']:
			update_textbooks(_id)
		else:
			do_get_class(_id)
	else:
		time.sleep(5)