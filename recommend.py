from setup import *
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import euclidean_distances
import pickle, Levenshtein

all_classes = list(classes.find({'error': None}))
all_groups = [x['class_ids'] for x in groups.find()]
for x in users.find():
	if 'recents' not in x:
		print x
user_recents = {x['email']:x['recents'] for x in users.find()}

raw_data = [x for x in all_classes if x['evaluation']]
all_c = [x['class'] for x in raw_data]
data = dict(zip(all_c, raw_data))
distance_fields = ['rating', 'learning_objectives_met', 'home_hours', 'classroom_hours', 'pace', 'assigments_useful', 'expectations_clear', 'grading_fair', 'lab_hours', 'prep_hours']
bool_fields = ['course', 'grad', 'hass']
bool_fields_deep = ['units', 'prereqs', 'coreqs', 'semesters']
custom_fields = ['name', 'description', 'in_groups', 'in_history']
fields = distance_fields + bool_fields + bool_fields_deep + custom_fields

sd = pickle.load(open("dat/sd.dat","rb"))

def calculate_similarity(c1, c2):
	class1 = data[c1]
	class2 = data[c2]
	dists = []
	for f in distance_fields:
		dists.append(euclidean_distances(class1['evaluation'][f] if f in class1['evaluation'] else 0, class2['evaluation'][f] if f in class2['evaluation'] else 0)[0][0] / 7.0)
	for f in bool_fields:
		class_1_f = class1[f] if f in class1 else None
		class_2_f = class2[f] if f in class2 else None
		if class_1_f is None and class_2_f is None:
			dists.append(0.0)
		else:
			dists.append(float(class_1_f != class_2_f))
	for f in bool_fields_deep:
		class_1_f = class1[f] if f in class1 else None
		class_2_f = class2[f] if f in class2 else None
		if class_1_f is None or class_2_f is None or len(class_1_f)+len(class_2_f) == 0:
			dists.append(0.0)
		else:
			total = 0.0
			for x,y in zip(class_1_f,class_2_f):
				total += float(x == y)
			for x,y in zip(class_2_f,class_1_f):
				total += float(x == y)
			dists.append(1.0 - total/float(len(class_1_f)+len(class_2_f)))
	#name
	dists.append(1.0 - Levenshtein.ratio(class1['name'], class2['name']))
	#description
	dists.append(1.0 - Levenshtein.ratio(class1['description'], class2['description']))
	#in_groups
	total = 0.0
	for group in all_groups:
		total += float(c1 in group and c2 in group)
	dists.append(1.0 - total/float(len(all_groups)))
	#in_history
	dists.append(1.0)
	return dists


def simple_distances():
	sd = []
	for c1 in all_c:
		print 'Processing', c1
		for c2 in all_c:
			if c2 != c1:
				row = [c1, c2] + calculate_similarity(c1, c2)
				sd.append(row)
	cols = ['c1', 'c2'] + fields
	return pd.DataFrame(sd, columns=cols)

def calc_distance(dists, c1, c2, weights):
	mask = (dists.c1 == c1) & (dists.c2 == c2)
	row = dists[mask]
	row = row[fields]
	dist = weights * row
	return dist.sum(axis=1).tolist()[0]

def default_weights(user_id, c):
	weights = [0.8]*len(distance_fields) + [1]*(len(fields)-len(distance_fields))
	defaults = [('course', 1.25), ('in_groups', 2.75), ('in_history', 3.5), ('prereqs', 1.5), ('coreqs', 1.5), ('name', 4), ('description', 1.75)]
	for k, v in defaults:
		weights[fields.index(k)] = v
	if user_id in user_recents and c in user_recents[user_id]:
		weights[fields.index('in_history')] = 0
	return [float(w) / sum(weights) for w in weights]

def save_sd():
	pickle.dump(simple_distances(), open("dat/sd.dat","wb"))


def recommend(u, c):
	results = {}
	for c_cmp in all_c:
		if c != c_cmp:
			try:
				weights = default_weights(u, c)
				dist = calc_distance(sd, c, c_cmp, weights)
				results[c_cmp] = dist
			except IndexError:
				pass
	return sorted(results.keys(), key=lambda x: results[x])[:5]

