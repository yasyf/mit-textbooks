#!/usr/bin/env python

from flask import Flask, Response, session, redirect, url_for, escape, request, render_template, g, flash, make_response
from functions import *
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.environ['sk']
dev = (os.getenv('dev','False') == 'True' or app.config['TESTING'] == True)

init_auth_browser()

@app.route('/')
def index_view():
	recent = recents.find().sort('dt',-1).limit(RECENTS)
	return render_template('index.html', recent=recent)

@app.route('/check/<class_id>')
def check_view(class_id):
	return Response(response=check_class_json(class_id), status=200, mimetype="application/json")

@app.route('/update/textbooks/<class_id>')
def update_textbooks_view(class_id):
	update_textbooks(class_id)
	return redirect(url_for('json_view', class_id=class_id))

@app.route('/loading/<class_ids>')
def loading_view(class_ids):
	classes = class_ids.split(',')
	if len(classes) == 1:
		url = url_for('class_view', class_id=classes[0], _external=True)
	else:
		group_id = prepare_class_hash(classes)
		url = url_for('group_view', group_id=group_id, _external=True)

	return render_template('loading.html', desc=', '.join(classes), class_ids=json.dumps(classes), class_status=json.dumps({c:False for c in classes}), url=url)

@app.route('/class/<class_id>')
def class_view(class_id):
	update_recents_with_class(class_id)
	if not check_class(class_id) and not is_worker:
		g = grequests.get(worker + url_for('json_view', class_id=class_id))
		grequests.send(g)
		return loading_view(class_id)
	return render_template('class.html', class_obj=get_class(class_id))

@app.route('/overview/<class_id>')
def overview_view(class_id):
	return render_template('overview.html', class_obj=get_class(class_id))

@app.route('/json/<class_id>')
def json_view(class_id):
	class_obj = get_class(class_id)
	return Response(response=class_obj.json(), status=200, mimetype="application/json")

@app.route('/group/<group_id>')
def group_view(group_id):
	group_obj = get_group(group_id)
	if not check_group(group_obj.class_ids) and not is_worker:
		g = grequests.get(worker + url_for('group_view', group_id=group_id))
		grequests.send(g)
		return loading_view(','.join(group_obj.class_ids))
	return render_template('group.html', classes=[get_class(class_id) for class_id in group_obj.class_ids], group_obj=group_obj)

@app.route('/search', methods=['POST'])
def search_view():
	search_term = request.form.get('search_term')
	return go_view(search_term)

@app.route('/go/<search_term>')
def go_view(search_term):
	classes = search_term.split(',')
	if len(classes) == 1:
		return redirect(url_for('class_view', class_id=classes[0]))
	else:
		group_id = prepare_class_hash(classes)
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

@app.template_filter('id_to_obj')
def id_to_obj_filter(class_id):
	return get_class(class_id)

@app.template_filter('last_name')
def last_name_filter(name):
	return name.split('.')[-1].strip()

@app.template_filter('sum_units')
def sum_units_filter(classes):
	return sum([sum(c.units) for c in classes])


if __name__ == '__main__':
	if os.environ.get('PORT'):
		app.run(host='0.0.0.0',port=int(os.environ.get('PORT')),debug=dev)
	else:
		app.run(host='0.0.0.0',port=5000,debug=dev)
