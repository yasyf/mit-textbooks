from functions import *

init_auth_browser()

last_task = None
task = None
mailed = False

def do_get_class(class_id):
	i = 1
	while i <= 5:
		try:
			return get_class(class_id)
		except AttributeError, e:
			print 'Worker Failure'
			print e
			init_auth_browser()
			time.sleep(.5*i)
			i += 1
		except Exception, e:
			print 'Worker Failure'
			print e
			time.sleep(1*i)
			i += 1
	task['time'] = time.time()
	queue.insert(task)

def error_mail():
	message = sendgrid.Mail()
	message.add_to(os.getenv('admin_email'))
	message.set_subject('Stuck Worker @ MIT Textbooks')
	message.set_html('<pre>' + repr(task) + '</pre>')
	message.set_text(repr(task))
	message.set_from('MIT Textbooks <tb_support@mit.edu>')
	try:
		sg.send(message)
	except Exception, e:
		print str(e)
		print 'Stuck Worker'
		print repr(task)

def fail_mail(e):
	message = sendgrid.Mail()
	message.add_to(os.getenv('admin_email'))
	message.set_subject('Crashing Worker @ MIT Textbooks')
	trace = traceback.format_exc() 
	message.set_html(request.url + '<br><br>' + e.message + '<br><br><pre>' + trace + '</pre>')
	message.set_text(request.url + '\n\n' + e.message + '\n\n' + trace)
	message.set_from('MIT Textbooks <tb_support@mit.edu>')
	try:
		sg.send(message)
	except Exception:
		pass

try:
	while True:
		last_task = task
		task = queue.find_one(sort=[("time", 1)])
		if task and last_task and task == last_task and not mailed:
			mailed = True
			error_mail()
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
except Exception, e:
	fail_mail(e)