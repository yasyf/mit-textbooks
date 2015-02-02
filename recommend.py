from setup import *
import pandas as pd
from sklearn.metrics.pairwise import euclidean_distances
import pickle, Levenshtein, time, re, os, traceback, sys
import multiprocessing, gc

fail_mailed = 0

def get_accept_function(i):
  def f1(c):
    course = c.split('.')[0]
    return course.isdigit() and int(course) in range(1,10) and not int(course) in {6, 8}
  def f2(c):
    course = c.split('.')[0]
    return course.isdigit() and (int(course) == 6 or int(course) in range(16,25))
  def f3(c):
    course = c.split('.')[0]
    return not course.isdigit() or int(course) in range(10,12)
  def f4(c):
    course = c.split('.')[0]
    return course.isdigit() and int(course) in [8] + range(12,16)
  return {1: f1, 2: f2, 3: f3, 4:f4}[i]

def fail_mail(e):
  global fail_mailed

  message = sendgrid.Mail()
  message.add_to(os.getenv('admin_email'))
  message.set_subject('Crashing Recommender @ MIT Textbooks')
  trace = traceback.format_exc()
  message.set_html('<br><br>' + str(e) + '<br><br><pre>' + trace + '</pre>')
  message.set_text('\n\n' + str(e) + '\n\n' + trace)
  message.set_from('MIT Textbooks <tb_support@mit.edu>')
  try:
    if fail_mailed < 5:
      sg.send(message)
      fail_mailed += 1
    else:
      sys.exit(str(e.message))
  except Exception:
    pass

def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)

def calculate_similarity(c1, c2):
  class1 = data[c1]
  class2 = data[c2]
  dists = []
  if class1['evaluation'] and class2['evaluation']:
    for f in distance_fields:
      dists.append(euclidean_distances(class1['evaluation'][f] if f in class1['evaluation'] else 0, class2['evaluation'][f] if f in class2['evaluation'] else 0)[0][0] / 7.0)
  else:
    dists.extend([1.0]*len(distance_fields))
  for f in bool_fields:
    class_1_f = class1[f] if f in class1 else None
    class_2_f = class2[f] if f in class2 else None
    if class_1_f is None and class_2_f is None:
      dists.append(0.0)
    else:
      dists.append(float(class_1_f != class_2_f))
  for f_orig in bool_fields_deep:
    f = f_orig.split('.')
    if len(f) == 2:
      class_1_f = class1[f[0]][f[1]] if f[0] in class1 and f[1] in class1[f[0]] else None
      class_2_f = class2[f[0]][f[1]] if f[0] in class2 and f[1] in class2[f[0]] else None
    else:
      f = f[0]
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
  #less_advanced
  dists.append(1.0)

  return dists

def sd_worker((i,c1)):
  sd = []
  for c2 in set(filter(lambda x: x.split('.')[0] == c1.split('.')[0], all_c) + all_r):
    if c2 != c1:
      row = [c1, c2] + calculate_similarity(c1, c2)
      sd.append(row)
  print 'Processing {c1}'.format(c1=c1)
  return sd

def simple_distances():
  p = multiprocessing.Pool()
  sd_to_flatten = p.map(sd_worker, enumerate([x for x in all_c if accept_function(x)]))
  p.close()
  print 'Flattening simple_distances'
  sd = []
  map(sd.extend, sd_to_flatten)
  del sd_to_flatten
  cols = ['c1', 'c2'] + fields
  df = pd.DataFrame(sd, columns=cols)
  del sd
  print 'Garbage Collecting'
  gc.collect()
  return df

def calc_distance(dists, c1, c2, weights):
  mask = (dists.c1 == c1) & (dists.c2 == c2)
  row = dists[mask]
  row = row[fields]
  dist = weights * row
  return dist.sum(axis=1).tolist()[0]

def default_weights(user_id, c, c_cmp):
  weights = [0.8]*len(distance_fields) + [1]*(len(fields)-len(distance_fields))
  defaults = [('course', 1.5), ('in_groups', 2.75), ('in_history', 3.5), ('prereqs', 1.5), ('coreqs', 1.5), ('name', 4), ('description', 1.75)]

  for k, v in defaults:
    weights[fields.index(k)] = v

  if user_id in user_recents and c_cmp in user_recents[user_id]:
    weights[fields.index('in_history')] = 0

  weights[fields.index('less_advanced')] = 0
  if c.split('.')[0] == c_cmp.split('.')[0]:
    try:
      c_f = float("."+re.findall("\d+", c.split('.')[-1])[0])
      c_cmp_f = float("."+re.findall("\d+", c_cmp.split('.')[-1])[0])
      if c_cmp_f < c_f:
        weights[fields.index('less_advanced')] = 5
    except Exception:
      pass

  return [float(w) / sum(weights) for w in weights]

def save_sd():
  if not os.path.exists("dat/"):
    os.makedirs("dat/")
  touch("dat/sd.dat")
  sd = simple_distances()
  pickle.dump(sd, open("dat/sd.dat","wb"))
  del sd

def get_sd():
  if not os.path.exists("dat/"):
    os.makedirs("dat/")
  import boto
  c = boto.connect_s3(os.getenv('ACCESS_KEY'), os.getenv('SECRET_KEY'))
  b = c.get_bucket(os.getenv('S3_BUCKET'))
  k = b.get_key('dat/sd.dat')
  k.get_contents_to_filename('dat/sd.dat')

def recommend_worker((u,c,c_cmp)):
  try:
    weights = default_weights(u, c, c_cmp)
    dist = calc_distance(sd, c, c_cmp, weights)
    return (c_cmp, dist)
  except IndexError:
    return None

def recommend(u, c):
  p = multiprocessing.Pool()
  recs_to_flatten = p.map(recommend_worker, [(u, c, c_cmp) for c_cmp in all_c])
  p.close()
  recs = filter(lambda x: x != None, recs_to_flatten)
  return [x[0] for x in sorted(recs, key=lambda x: x[1])[:5]]

if __name__ == '__main__':
  print 'Initializing Globals'
  SERVER_NUM = int(os.environ['SERVER_NUM'])
  accept_function = get_accept_function(SERVER_NUM)

  all_classes = list(classes.find({'error': None}))
  all_recents = list(recents.find().sort("dt", -1).limit(100))
  all_groups = [x['class_ids'] for x in groups.find()]
  user_recents = {x['email']:x['recents'] for x in users.find()}

  all_c = [x['class'] for x in all_classes]
  all_r = [x['class'] for x in all_recents]
  data = dict(zip(all_c, all_classes))
  distance_fields = ['rating', 'learning_objectives_met', 'home_hours', 'classroom_hours', 'pace', 'assigments_useful', 'expectations_clear', 'grading_fair', 'lab_hours', 'prep_hours']
  bool_fields = ['course', 'grad', 'hass', 'ci']
  bool_fields_deep = ['units', 'prereqs', 'coreqs', 'semesters', 'meta.keywords', 'meta.entities']
  custom_fields = ['name', 'description', 'in_groups', 'in_history', 'less_advanced']
  fields = distance_fields + bool_fields + bool_fields_deep + custom_fields

  # print 'Saving Recommendations'
  # save_sd()
  # print 'Fetching Recommendations'
  # get_sd()

  print 'Generating Recommendations'
  sd = simple_distances()
  start_time = time.time()

  print 'Loading Initial Tasks'
  for c in recommendations.find({'default.class_ids': {"$size": 0}}):
    try:
      d = {'class_id': c['class_id'], 'user_id': c['default_uids'][0], 'queue': 'recommender', 'safe': True}
      if not queue.find_one(d):
        recommendations.remove(c['_id'], safe=True)
        d['time'] = time.time()
        queue.insert(d, safe=True)
    except Exception:
      continue
  print 'Starting Run Loop'
  last_task = None
  is_safe = True
  try:
    while True:
      try:
        query = {'queue': 'recommender', 'ignore': {'$nin': [SERVER_NUM]}}
        if not is_safe:
          query['safe'] =  None
        task = sorted(queue.find(query, snapshot=True), key=lambda x: x['time'])[0]
      except Exception:
        task = None
      if task:
        try:
          queue.remove(task['_id'], safe=True)
        except Exception:
          continue
        if task == last_task:
          continue
        _id = task['class_id']
        uid = task['user_id'].split("@")[0]
        if not accept_function(_id):
          print 'Skipping {_id} for user {uid}'.format(_id=_id, uid=uid)
          s = set(task.get('ignore',[]))
          s.add(SERVER_NUM)
          task['ignore'] = list(s)
          try:
            queue.insert(task, safe=True)
          except pymongo.errors.DuplicateKeyError:
            pass
          continue
        if task.get('safe', False) and _id not in all_c:
          print '{c} not in master class list, this server is no longer reliable!'.format(c=_id)
          is_safe = False
          try:
            queue.insert(task, safe=True)
          except pymongo.errors.DuplicateKeyError:
            pass
          continue
        last_task = task
        print 'Processing {_id} for user {uid}'.format(_id=_id, uid=uid)
        r = {'class_ids': recommend(uid, _id)}
        r['time'] = time.time()
        current = recommendations.find_one({'class_id': _id})
        if current:
          if r['class_ids'] == current['default']['class_ids']:
            recommendations.update({'class_id': _id}, {"$addToSet": {"default_uids": uid}})
          else:
            recommendations.update({'class_id': _id}, {"$pull": {"default_uids": uid}, "$set": {"users.{uid}".format(uid=uid): r}})

          if (time.time() - current['default']['time']) > CACHE_FOR:
            recommendations.update({'class_id': _id}, {"$set": {"default": r, "default_uids": []}})

        else:
          recommendations.update({'class_id': _id}, {"$set": {"default": r, "default_uids": [uid], 'users': {}}}, upsert=True)
      else:
        time.sleep(5)
  except Exception, e:
    fail_mail(e)
