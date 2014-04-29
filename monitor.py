from functions import *

init_auth_browser()

while True:
	task = queue.find_one(sort=[("time", 1)])
	if task:
		queue.remove(task)
		_id = task['class_id']
		print 'Processing {_id}'.format(_id=_id)
		if task['group']:
			group_obj = get_group(_id)
			for c in group_obj.class_ids:
				get_class(c)
		elif task['update']:
			update_textbooks(_id)
		else:
			get_class(_id)
	else:
		time.sleep(5)