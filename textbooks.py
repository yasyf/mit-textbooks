#!/usr/bin/env python

from flask import Flask, Response, session, redirect, url_for, escape, request, render_template, g, flash, make_response, jsonify
from functions import *
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.environ['sk']

init_auth_browser()

def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']

@app.before_request
def preprocess_request():
	browser = request.user_agent.browser
	version = request.user_agent.version and int(request.user_agent.version.split('.')[0])
 
	if request.endpoint != 'static' and browser and version:
		if (browser == 'msie' and version < 10):
			return render_template('unsupported.html')

	email = request.cookies.get('id_email')
	if email:
		email = urllib.unquote(email)
		name = urllib.unquote(request.cookies.get('id_name',''))
		g.user = get_user(email, name)
	else:
		g.user = None

@app.after_request
def postprocess_request(response):
	if request.endpoint in ['loading_view', 'check_view']:
		response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
		response.headers['Pragma'] = 'no-cache'
		response.headers['Expires'] = '0'
	return response

@app.route('/')
def index_view():
	recent = recents.find().sort('dt',-1).limit(RECENTS)
	return render_template('index.html', recent=recent)

@app.errorhandler(404)
def _404_handler(e):
	return _404_view()

@app.route('/404')
def _404_view():
	classes = session.get('404',[])
	return render_template('404.html', classes=classes), 404

@app.errorhandler(500)
@app.route('/500')
def _500_view(e):
	if not dev:
		error_mail(e)
	return render_template('500.html', e=str(e)), 500

@app.route('/check/<class_id>')
def check_view(class_id):
	return jsonify(check_class_json(class_id))

@app.route('/update/textbooks/<class_id>')
def update_textbooks_view(class_id):
	update_textbooks(class_id)
	return redirect(url_for('json_class_view', class_id=class_id))

@app.route('/blacklist/<class_ids>')
def blacklist_view(class_ids):
	id_list = class_ids.split(',')
	if not session.get('blacklisted'):
		session['blacklisted'] = []
	for c in id_list:
		if c not in session['blacklisted']:
			session['blacklisted'] = session['blacklisted'] + id_list
			blacklist_class(c)
	return jsonify({"error": False})

@app.route('/unblacklist/<class_ids>')
def unblacklist_view(class_ids):
	id_list = class_ids.split(',')
	if not session.get('blacklisted'):
		session['blacklisted'] = []
	for c in id_list:
		if c not in session['blacklisted']:
			session['blacklisted'] = session['blacklisted'] + id_list
			unblacklist_class(c)
	return jsonify({"error": False})

@app.route('/loading/<class_ids>')
def loading_view(class_ids, override_url=None):
	t = session.get('loading')[0] if session.get('loading') and session.get('loading')[1] == class_ids else int(time.time())
	if session.get('override_url'):
		override_url = session.get('override_url')
	session['override_url'] = override_url
	session['loading'] = (t, class_ids)
	classes = class_ids.split(',')
	if len(classes) == 1:
		url = url_for('class_view', class_id=classes[0], _external=True)
	else:
		group_id = prepare_class_hash(classes)
		url = url_for('group_view', group_id=group_id, _external=True)
	statuses = {c:check_class(c) for c in classes}
	penalty = float(get_blacklist(classes))
	percent = max((len(filter(lambda x: x == True, statuses.values()))/float(len(statuses.values())))*100, int((time.time() - t) /len(statuses.values()) * (10.0/penalty)))
	g.search_val = class_ids
	can_blacklist = True
	if session.get('blacklisted'):
		can_blacklist = False in [(x in session.get('blacklisted')) for x,status in statuses.iteritems() if status == False]
		if not can_blacklist:
			message = 'This is taking longer than normal. Please wait a while or <a class="btn btn-danger btn-xs" onclick="$(\'#feedback_modal\').modal();">contact support</a>!'.format(class_ids=class_ids)
			flash(message, 'danger')
	return render_template('loading.html', class_ids=class_ids, classes=statuses, percent=percent, url=override_url if override_url else url, t=t, can_blacklist=can_blacklist, penalty=penalty)

@app.route('/class/<class_id>')
def class_view(class_id):
	if not check_class(class_id):
		send_to_worker(class_id)
		return loading_view(class_id)
	session['loading'] = None
	class_obj = get_class(class_id)
	if class_obj is None:
		session['404'] = [class_id]
		return redirect(url_for('_404_view'))
	if class_obj.master_subject_id != class_obj.id:
		return redirect(url_for('class_view', class_id=class_obj.master_subject_id))
	update_recents_with_class(class_obj)
	g.search_val = class_id
	return render_template('class.html', class_obj=class_obj)

@app.route('/calendar/<group_id>')
def calendar_view(group_id):
	group_obj = get_group(group_id)
	if not group_obj:
		if '404' in session:
			session.pop('404')
		return redirect(url_for('_404_view'))
	events = reduce(lambda x,y: x + get_class(y).events(), group_obj.class_ids, [])
	return render_template('scheduler.html', events=events)

@app.route('/overview/<class_id>')
def overview_view(class_id):
	return render_template('overview.html', class_obj=get_class(class_id))

@app.route('/json/class/<class_id>')
def json_class_view(class_id):
	class_obj = get_class(class_id)
	if class_obj is None:
		return jsonify({"error": "{c} not found".format(c=class_id)})
	return jsonify(class_obj.json())

@app.route('/json/group/<group_id>')
def json_group_view(group_id):
	group_obj = get_group(group_id)
	group = {c:get_class(c).json() for c in group_obj.class_ids}
	g_filtered = [x for x in group.values() if x != None]
	if not g_filtered:
		return jsonify({"error": "{group} not found".format(group=group_id)})
	return jsonify(group)

@app.route('/group/<group_id>')
def group_view(group_id):
	group_obj = get_group(group_id)
	if not group_obj:
		if '404' in session:
			session.pop('404')
		return redirect(url_for('_404_view'))
	if not check_group(group_obj.class_ids):
		for class_id in group_obj.class_ids:
			send_to_worker(class_id)
		return loading_view(','.join(group_obj.class_ids))
	session['loading'] = None
	group = [get_class(class_id) for class_id in group_obj.class_ids]
	g_filtered = [x for x in group if x != None]
	g_filtered_ids = [x.master_subject_id for x in g_filtered]
	if not g_filtered:
		session['404'] = group_obj.class_ids
		return redirect(url_for('_404_view'))
	if not set(g_filtered_ids).issubset(set(group_obj.class_ids)):
		return redirect(url_for('go_view', search_term=','.join(g_filtered_ids)))
	if len(group) != len(g_filtered):
		for x in set(group_obj.class_ids) - set(g_filtered_ids):
			s = "{c} could not be found!".format(c=x)
			flash(s, 'danger')
	for overlaps in check_all_times(g_filtered):
		classes = ', '.join(overlaps[:-1]) + ' and ' + overlaps[-1] if len(overlaps) > 1 else overlaps[0]
		flash(classes + ' have conflicting lecture times!', 'warning')
	g.search_val = ', '.join(g_filtered_ids)
	return render_template('group.html', classes=g_filtered, group_obj=group_obj)

@app.route('/name_group/<group_id>/<group_name>')
def name_group_view(group_id, group_name):
	group_obj = get_group(group_id)
	return jsonify(save_group(group_obj, group_name))

@app.route('/delete_group/<group_id>')
def delete_group_view(group_id):
	delete_group(group_id)
	flash('{group} has been deleted.'.format(group=group_id), 'danger')
	return redirect(url_for('index_view'))

@app.route('/sell_textbook/<class_id>/<tb_id>', methods=['POST'])
def sell_textbook_view(class_id, tb_id):
	sell_textbook(class_id, tb_id, request.form)
	flash('You have successfully listed your textbook!', 'success')
	return redirect(url_for('class_view', class_id=class_id))

@app.route('/remove_offer/<class_id>/<offer_id>')
def remove_offer_view(class_id, offer_id):
	remove_offer(offer_id)
	flash('Your textbook has been removed from MIT Textbooks.', 'danger')
	return redirect(url_for('class_view', class_id=class_id))

@app.route('/account')
def account_view():
	if not g.user:
		return redirect(url_for('index_view'))
	classes = [offer['class_id'] for offer in g.user.get_postings()]
	if classes:
		if len(classes) == 1:
			class_id = classes[0]
			if not check_class(class_id):
				url = url_for('account_view', _external=True)
				send_to_worker(class_id)
				return loading_view(class_id, override_url=url)
		else:
			group_id = prepare_class_hash(classes)
			group_obj = get_group(group_id)
			if not check_group(group_obj.class_ids):
				send_to_worker(group_id, group=True)
				url = url_for('account_view', _external=True)
				return loading_view(','.join(group_obj.class_ids), override_url=url)
	session['loading'] = None
	return render_template('account.html')

@app.route('/search', methods=['POST'])
def search_view():
	search_term = request.form.get('search_term')
	return go_view(search_term)

@app.route('/opensearchdescription.xml')
def opensearchdescription_view():
	return Response(response=render_template('opensearchdescription.xml'), status=200, mimetype="application/xml")

@app.route('/robots.txt')
def robots_view():
	disallows = [url_for('_404_view'), url_for('account_view'), url_for('check_view',class_id=''), url_for('update_textbooks_view',class_id=''), url_for('blacklist_view',class_ids=''), url_for('loading_view',class_ids='') , url_for('name_group_view',group_id='', group_name=''), url_for('delete_group_view',group_id=''), url_for('sell_textbook_view',class_id='', tb_id=''), url_for('remove_offer_view',class_id='', offer_id='')]
	return Response(response=render_template('robots.txt', disallows=disallows), status=200, mimetype="text/plain;charset=UTF-8")

@app.route('/sitemap.xml')
def sitemap_view():
	return Response(response=render_template('sitemap.xml', allows=sitemap_allows()), status=200, mimetype="application/xml")

@app.route('/urllist.txt')
def urllist_view():
	return Response(response=render_template('urllist.txt', allows=sitemap_allows()), status=200, mimetype="text/plain;charset=UTF-8")

@app.route('/go/<search_term>')
def go_view(search_term):
	classes = [format_class(c) for c in search_term.split(',')]
	if len(classes) == 1:
		if request_wants_json():
			return redirect(url_for('json_class_view', class_id=classes[0]))
		return redirect(url_for('class_view', class_id=classes[0]))
	else:
		group_id = prepare_class_hash(classes)
		if request_wants_json():
			return redirect(url_for('json_group_view', group_id=group_id))
		return redirect(url_for('group_view', group_id=group_id))

@app.route('/site/<class_id>')
def site_view(class_id):
	class_obj = get_class(class_id)
	return redirect(class_obj.class_site_url())

@app.route('/stellar/<class_id>')
def stellar_view(class_id):
	class_obj = get_class(class_id)
	if class_obj and class_obj.stellar_site_url():
		return redirect(class_obj.stellar_site_url())
	return redirect(url_for('site_view', class_id=class_id))

@app.route('/amazon/product/<asin>')
def amazon_product_view(asin):
	url = "http://www.amazon.com/dp/{asin}/?tag=mit-tb-20".format(asin=asin)
	return redirect(url)

@app.route('/amazon/search/<title>')
def amazon_search_view(title):
	url = "http://www.amazon.com/s/?tag=mit-tb-20&field-keywords={title}".format(title=title)
	return redirect(url)

@app.route('/evaluation/<class_id>')
def class_evaluation_view(class_id):
	url = "https://edu-apps.mit.edu/ose-rpt/subjectEvaluationSearch.htm?subjectCode={class_id}&search=Search".format(class_id=class_id)
	return redirect(url)

@app.route('/evaluation/<class_id>/<professor>')
def professor_evaluation_view(class_id, professor):
	url = "https://edu-apps.mit.edu/ose-rpt/subjectEvaluationSearch.htm?subjectCode={class_id}&instructorName={professor}&search=Search".format(class_id=class_id, professor=professor)
	return redirect(url)

@app.route('/export/courseroad/<class_ids>', methods=['POST'])
def courseroad_export_view(class_ids):
	year = TERM[:4]
	i = int(request.form.get('year'))
	semester = int(request.form.get('semester'))
	term = 4*(i-1) + semester
	session['year'] = i
	session['semester'] = semester
	url = "https://courseroad.mit.edu/?hash={kerberos}&addclasses={class_ids}&year={year}&term={term}".format(kerberos=g.user.kerberos(), class_ids=class_ids, year=year, term=term)
	return redirect(url)

@app.template_filter('id_to_obj')
def id_to_obj_filter(class_id):
	return get_class(class_id)

@app.template_filter('last_name')
def last_name_filter(name):
	return name.split('.')[-1].strip()

@app.template_filter('sum_units')
def sum_units_filter(classes):
	return sum([sum(c.units) for c in classes])

@app.template_filter('tb_id')
def tb_id_filter(textbook):
	return tb_id(textbook)

@app.template_filter('tb_id_to_tb')
def tb_id_to_tb_filter(class_id, textbook_id):
	class_obj = get_class(class_id)
	for section in class_obj.textbooks['sections'].values():
		for book in section:
			if tb_id(book) == textbook_id:
				return book

@app.template_filter('space_out')
def space_out_filter(s):
	return ', '.join(s.split(','))

@app.template_filter('prices')
def prices_filter(textbook):
	prices = []
	for x in ['used', 'new', 'retail']:
		if x in textbook and textbook[x]:
			prices.append((x,textbook[x]))
	return prices

@app.template_filter('year_from_i')
def year_from_i_filter(i):
	d = {'1': 'Freshman', '2': 'Sophomore', '3': 'Junior', '4': 'Senior', 'G': 'Graduate'}
	return d[i] if i in d else i

@app.template_filter('image')
def image_filter(classes):
	for c in classes:
		if c.image():
			return c.image()

@app.template_filter('current_term')
def current_term_filter(n):
	return CURRENT_TERM

@app.template_filter('term_start_formatted')
def term_start_formatted_filter(n):
	return TERM_START.strftime("%B %d, %Y")

@app.template_filter('gcal_events')
def gcal_events_filter(classes):
	events = []
	for c in classes:
		events.extend(c.gcal_events())
	return events

@app.template_filter('section_saved')
def section_saved_filter(section):
	percentages = []
	p = None
	for book in section:
		if 'retail' in book and book['retail']:
			if 'used' in book and book['used']:
				p = max(100 * (1 - float(book['used'])/float(book['retail'])), float(book['saved']) if 'saved' in book else 0)
			elif 'new' in book and book['new']:
				p = max(100 * (1 - float(book['new'])/float(book['retail'])), float(book['saved']) if 'saved' in book else 0)
			else:
				p = float(book['saved'] if 'saved' in book else 0)
		elif 'saved' in book and book['saved']:
			p = float(book['saved'])
	return "up to {p}%".format(p=int(p)) if p and p > 20 else 'a ton'


if __name__ == '__main__':
	if os.environ.get('PORT'):
		app.run(host='0.0.0.0',port=int(os.environ.get('PORT')),debug=dev)
	else:
		app.run(host='0.0.0.0',port=5000,debug=dev)
