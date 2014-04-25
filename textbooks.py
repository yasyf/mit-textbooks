#!/usr/bin/env python

from flask import Flask, Response, session, redirect, url_for, escape, request, render_template, g, flash, make_response
from functions import *
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.environ['sk']
dev = (os.getenv('dev','False') == 'True' or app.config['TESTING'] == True)

@app.route('/')
def index_view():
	recent = recents.find().sort('dt',-1).limit(RECENTS)
	return render_template('index.html', recent=recent)

@app.route('/class/<class_id>')
def class_view(class_id):
	update_recents_with_class(class_id)
	return render_template('class.html', class_obj=get_class(class_id))


if __name__ == '__main__':
	if os.environ.get('PORT'):
		app.run(host='0.0.0.0',port=int(os.environ.get('PORT')),debug=dev)
	else:
		app.run(host='0.0.0.0',port=5000,debug=dev)
