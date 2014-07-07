#!/usr/bin/env python

from flask import Flask, Response, session, redirect, url_for, escape, request, render_template, g, flash, make_response, jsonify
from werkzeug.contrib.cache import MemcachedCache
from flask.ext.compress import Compress
import flask.ext.webcache.handlers as flask_web_cache
import flask.ext.webcache.modifiers as modifiers
import bugsnag, bmemcached
from flask_s3 import FlaskS3
from bugsnag.flask import handle_exceptions
from functions import *
from bson.objectid import ObjectId

cache = MemcachedCache(bmemcached.Client(os.environ.get('MEMCACHEDCLOUD_SERVERS').split(','), os.environ.get('MEMCACHEDCLOUD_USERNAME'), os.environ.get('MEMCACHEDCLOUD_PASSWORD')))

app = Flask(__name__)

app.secret_key = os.environ['sk']
app.debug = dev
app.config.update(AWS_ACCESS_KEY_ID=os.getenv('ACCESS_KEY'), AWS_SECRET_ACCESS_KEY = os.getenv('SECRET_KEY'), S3_CDN_DOMAIN = os.getenv('CF_DOMAIN'), S3_BUCKET_NAME = os.getenv('S3_BUCKET'), S3_HEADERS = {'Cache-Control': 'max-age=86400'})

if not dev:
  bugsnag.configure(api_key="e558ed40a3d0eab0598e5ac17d433ebd", project_root="/app")
  handle_exceptions(app)

flask_web_cache.RequestHandler(cache, app)
flask_web_cache.ResponseHandler(cache, app)

Compress(app)

FlaskS3(app)

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

  if browser in {"google", "aol", "ask", "yahoo"}:
    g.scraper = True
  else:
    g.scraper = False

  email = session.get('email') or urllib.unquote(request.cookies.get('id_email',''))
  if email:
    name = session.get('name') or urllib.unquote(request.cookies.get('id_name',''))
    g.user = get_user(email, name)
    session['email'] = email
    session['name'] = g.user.name
  else:
    g.user = None

  g.ip = request.headers.get("X-Forwarded-For", '')

  if request.args.get('voice'):
    session['voice'] = True

@app.after_request
def postprocess_request(response):
  response.headers['X-UA-Compatible'] = 'IE=edge,chrome=1'
  if request.endpoint in ['loading_view', 'check_view', 'account_view']:
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

@app.route('/private/up')
def uptest_view():
  return 'MIT Textbooks is up as of {} UTC'.format(datetime.datetime.utcnow())

@app.route('/textbooks')
@modifiers.cache_for(hours=1)
def textbooks_view():
  if 'override_url' in session:
    session.pop('override_url')
  all_offers = list(offers.find().sort('class_id', 1))
  classes = [offer['class_id'] for offer in all_offers]
  group_id = prepare_class_hash(classes)
  group_obj = get_group(group_id)
  if not check_group(group_obj.class_ids):
    send_to_worker(group_id, group=True)
    url = url_for('textbooks_view', _external=True)
    return redirect(url_for('loading_view', class_ids=','.join(group_obj.class_ids), override_url=url))
  textbooks = {}
  for offer in all_offers:
    c = get_class(offer['class_id'])
    if c not in textbooks:
      textbooks[c] = []
    textbooks[c].append(tb_id_to_tb_filter(offer['class_id'], offer['tb_id']))
  return render_template('textbooks.html', offers=textbooks, classes=group_obj.class_ids)

@app.route('/classes/filter/all')
@modifiers.cache_for(weeks=4)
def all_classes_view():
  return render_template('all_classes.html', classes=get_sorted_classes({'error': 'None'}))

@app.route('/classes/filter/<key>/<value>')
@modifiers.cache_for(weeks=4)
def class_kv_view(key, value):
  return render_template('classes_kv.html', k=key.upper(), v=value, classes=get_sorted_classes({key: value}))

@app.route('/classes/filter', methods=['GET','POST'])
@modifiers.cache_for(weeks=4)
def classes_filter_view():
  filters = request.values.get('filters', '{}')
  try:
    json_filters = json.loads(filters)
    sorted_classes = get_sorted_classes(json_filters)
  except Exception as e:
    return jsonify({'error': 'malformed json', 'message': str(e)})
  short_url = gen_short_url('classes_filter_view', {'filters': filters})
  return jsonify({'sorted_classes': [url_for('class_view', class_id=c['class'], _external=True) for c in sorted_classes], 'short_url': short_url, 'filters': json_filters})

@app.route('/short/<_hash>')
@modifiers.cache_for(weeks=4)
def short_url_view(_hash):
  return redirect(expand_short_url(_hash))

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

@app.route('/class/oid/<_id>')
@modifiers.cache_for(weeks=4)
def class_oid_view(_id):
  c = classes.find_one({'_id': ObjectId(_id)})
  if c:
    instant = request.args.get('instant')
    if instant:
      return redirect(url_for('class_view', class_id=c['class'], instant=instant))
    else:
      return redirect(url_for('class_view', class_id=c['class']))
  else:
    session['404'] = None
    return redirect(url_for('_404_view'))

@app.route('/class/<class_id>')
@modifiers.cache_for(hours=12)
def class_view(class_id):
  if not check_class(class_id):
    send_to_worker(class_id)
    return redirect(url_for('loading_view', class_ids=class_id))
  session['loading'] = None
  class_obj = get_class(class_id)
  if class_obj is None:
    session['404'] = [class_id]
    return redirect(url_for('_404_view'))
  if class_obj.master_subject_id != class_obj.id or class_id != class_obj.id:
    return redirect(url_for('class_view', class_id=class_obj.master_subject_id))
  if not g.scraper and not request.args.get('instant') == 'true':
    update_recents_with_class(class_obj)
    view_classes([class_id])
  g.search_val = class_id
  rec = [get_class(r) for r in class_obj.get_rec(g.user) if check_class(r)]
  return render_template('class.html', class_obj=class_obj, rec=rec)

@app.route('/calendar/<group_id>')
@modifiers.cache_for(days=7)
def calendar_view(group_id):
  group_obj = get_group(group_id)
  if not group_obj:
    if '404' in session:
      session.pop('404')
    return redirect(url_for('_404_view'))
  events = reduce(lambda x,y: x + get_class(y).events() if get_class(y) else x, group_obj.class_ids, [])
  return render_template('scheduler.html', events=events)

@app.route('/overview/<class_id>')
@modifiers.cache_for(days=1)
def overview_view(class_id):
  if not check_class(class_id):
    send_to_worker(class_id)
    return redirect(url_for('loading_view', class_ids=class_id))
  session['loading'] = None
  class_obj = get_class(class_id)
  if class_obj is None:
    session['404'] = [class_id]
    return redirect(url_for('_404_view'))
  if class_obj.master_subject_id != class_obj.id or class_id != class_obj.id:
    return redirect(url_for('overview_view', class_id=class_obj.master_subject_id))
  return render_template('overview.html', class_obj=get_class(class_id))

@app.route('/json/class/<class_id>')
@modifiers.cache_for(hours=1)
def json_class_view(class_id):
  class_obj = get_class(class_id)
  if class_obj is None:
    return jsonify({"error": "{c} not found".format(c=class_id)})
  return jsonify(class_obj.json())

@app.route('/json/group/<group_id>')
@modifiers.cache_for(hours=1)
def json_group_view(group_id):
  group_obj = get_group(group_id)
  group = {c:get_class(c).json() for c in group_obj.class_ids}
  g_filtered = [x for x in group.values() if x != None]
  if not g_filtered:
    return jsonify({"error": "{group} not found".format(group=group_id)})
  return jsonify(group)

@app.route('/group/<group_id>')
@modifiers.cache_for(hours=12)
def group_view(group_id):
  group_obj = get_group(group_id)
  if not group_obj:
    if '404' in session:
      session.pop('404')
    return redirect(url_for('_404_view'))
  if not check_group(group_obj.class_ids):
    for class_id in group_obj.class_ids:
      send_to_worker(class_id)
    return redirect(url_for('loading_view', class_ids=','.join(group_obj.class_ids)))
  session['loading'] = None
  group = [get_class(class_id) for class_id in group_obj.class_ids]
  if not g.scraper and not request.args.get('instant') == 'true':
    view_classes(group_obj.class_ids)
  g_filtered = [x for x in group if x != None]
  g_filtered_ids = [format_class(x.master_subject_id) for x in g_filtered]
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
    classes = ', '.join(overlaps[:-1]) + ' and ' + overlaps[-1] if len(overlaps) > 1 else ' and '.join(overlaps) if len(overlaps) == 2 else overlaps[0]
    flash(classes + ' have conflicting lecture times!', 'warning')
  g.search_val = ', '.join(g_filtered_ids)
  recs = [[get_class(r) for r in class_obj.get_rec(g.user) if check_class(r)] for class_obj in g_filtered]
  return render_template('group.html', classes=g_filtered, group_obj=group_obj, recs=recs)

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
  if 'override_url' in session:
    session.pop('override_url')
  if not g.user:
    return redirect(url_for('index_view'))
  classes = [offer['class_id'] for offer in g.user.get_postings()]
  if classes:
    if len(classes) == 1:
      class_id = classes[0]
      if not check_class(class_id):
        url = url_for('account_view', _external=True)
        send_to_worker(class_id)
        return redirect(url_for('loading_view', class_ids=class_id, override_url=url))
    else:
      group_id = prepare_class_hash(classes)
      group_obj = get_group(group_id)
      if not check_group(group_obj.class_ids):
        send_to_worker(group_id, group=True)
        url = url_for('account_view', _external=True)
        return redirect(url_for('loading_view', class_ids=','.join(group_obj.class_ids), override_url=url))
  session['loading'] = None
  if g.user and g.user.is_mobile_locked_out():
    flash('Your mobile account was locked out, and has now been re-enabled')
    g.user.reset_mobile_lockout()
  return render_template('account.html')

@app.route('/login', methods=['GET', 'POST'])
def login_view():
  g.user = None
  session['email'] = None
  if request.method == 'POST':
    email = request.form.get('email')
    password = request.form.get('password')
    user = get_user(email, None, create=False)
    if user.is_logged_in():
      if user.check_password(password):
        g.user = user
        session['email'] = email
        session['name'] = user.name
        g.user.reset_mobile_lockout()
        flash('You are now logged in!', 'success')
        return redirect(url_for('account_view'))
      else:
        session['email'] = False
        mail_password(user)
        if user.is_mobile_locked_out():
          flash('You account has been locked out. Login on desktop to restore access.', 'danger')
          return(redirect(url_for('forgot_view')))
        flash('Your password was incorrect. Check your email for a reminder.', 'danger')

    else:
      session['email'] = False
      flash("That user doesn't exist!", 'danger')
    return redirect(url_for('login_view'))  
  else:
    return render_template('login.html', hide_search=True)

@app.route('/forgot')
def forgot_view():
  if session.get('email'):
    user = get_user(session.get('email'), None, create=False)
    if user.is_logged_in():
      mail_password(user)
  return render_template('forgot.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout_view():
  g.user = None
  session['email'] = None
  return redirect(url_for('index_view'))

@app.route('/search', methods=['POST', 'GET'])
def search_view():
  if request.method == 'GET':
    return redirect(url_for('index_view'))
  _id = request.form.get('_id') 
  search_term = request.form.get('search_term')
  return go_view(search_term, _id=_id)

@app.route('/opensearchdescription.xml')
def opensearchdescription_view():
  return Response(response=render_template('opensearchdescription.xml'), status=200, mimetype="application/xml")

@app.route('/robots.txt')
@modifiers.cache_for(days=1)
def robots_view():
  disallows = [url_for('_404_view'), url_for('account_view'), url_for('check_view',class_id=''), url_for('update_textbooks_view',class_id=''), url_for('blacklist_view',class_ids=''), url_for('loading_view',class_ids='') , url_for('name_group_view',group_id='', group_name=''), url_for('delete_group_view',group_id=''), url_for('sell_textbook_view',class_id='', tb_id=''), url_for('remove_offer_view',class_id='', offer_id='')]
  return Response(response=render_template('robots.txt', disallows=disallows), status=200, mimetype="text/plain;charset=UTF-8")

@app.route('/sitemap.xml')
@modifiers.cache_for(days=1)
def sitemap_view():
  return Response(response=render_template('sitemap.xml', allows=sitemap_allows()), status=200, mimetype="application/xml")

@app.route('/urllist.txt')
@modifiers.cache_for(days=1)
def urllist_view():
  return Response(response=render_template('urllist.txt', allows=sitemap_allows()), status=200, mimetype="text/plain;charset=UTF-8")

@app.route('/suggest/<search_term>')
@modifiers.cache_for(days=7)
def suggest_view(search_term):
  return jsonify(suggestion(search_term))

@app.route('/popover/<class_id>')
@modifiers.cache_for(days=7)
def popover_view(class_id):
  return jsonify(popover(format_class(class_id)))

@app.route('/go/<search_term>')
def go_view(search_term, _id=None):
  if _id:
    return redirect(url_for('class_oid_view', _id=_id))
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
@modifiers.cache_for(days=7)
def site_view(class_id):
  class_obj = get_class(class_id)
  if class_obj is None:
    session['404'] = [class_id]
    return redirect(url_for('_404_view'))
  return redirect(class_obj.class_site_url())

@app.route('/stellar/<class_id>')
@modifiers.cache_for(days=7)
def stellar_view(class_id):
  class_obj = get_class(class_id)
  if class_obj and class_obj.stellar_site_url():
    return redirect(class_obj.stellar_site_url())
  return redirect(url_for('site_view', class_id=class_id))

@app.route('/amazon/product/<asin>')
@modifiers.cache_for(days=7)
def amazon_product_view(asin):
  url = u"http://www.amazon.com/dp/{asin}/?tag=mit-tb-20".format(asin=asin)
  return redirect(url)

@app.route('/amazon/search/<title>')
@modifiers.cache_for(days=7)
def amazon_search_view(title):
  url = u"http://www.amazon.com/s/?tag=mit-tb-20&field-keywords={title}".format(title=title)
  return redirect(url)

@app.route('/evaluation/<class_id>')
@modifiers.cache_for(days=7)
def class_evaluation_view(class_id):
  url = u"https://edu-apps.mit.edu/ose-rpt/subjectEvaluationSearch.htm?subjectCode={class_id}&search=Search".format(class_id=class_id)
  return redirect(url)

@app.route('/evaluation/<class_id>/<professor>')
@modifiers.cache_for(days=7)
def class_professor_evaluation_view(class_id, professor):
  url = u"https://edu-apps.mit.edu/ose-rpt/subjectEvaluationSearch.htm?subjectCode={class_id}&instructorName={professor}&search=Search".format(class_id=class_id, professor=professor)
  return redirect(url)

@app.route('/professor/<professor>')
@modifiers.cache_for(days=7)
def professor_view(professor):
  term = professor + ' + MIT'
  urls = search_google(term)
  if urls:
    return redirect(urls[0])
  else:
    return redirect(get_google_url(term))

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

@app.route('/amazon_prime_student')
@modifiers.cache_for(days=7)
def amazon_prime_student_view():
  return redirect('http://www.amazon.com/gp/student/signup/info?ie=UTF8&tag=mit-tb-20&refcust=UF4ETMRRZEYWDKZETGTJUD2IV4&ref_type=generic')

@app.route('/out/<_hash>')
@modifiers.cache_for(days=7)
def out_view(_hash):
  return redirect(url_for('amazon_product_view',asin=get_asin_from_hash(_hash)))

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
  return ', '.join(s)

@app.template_filter('prices')
def prices_filter(textbook, class_obj):
  prices = []
  if class_obj.has_local():
    offers = [x['price'] for x in class_obj.offers(tb_id_filter(textbook))]
    if offers:
      prices.append(('Local', "%.2f" % min(offers)))
  for x in ['used', 'new', 'retail']:
    if x in textbook and textbook[x]:
      prices.append((x[0].upper() + x[1:], textbook[x]))
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
def section_saved_filter(section, class_obj):
  percentages = []
  all_p = [0.0]
  for book in section:
    p = 0
    if 'retail' in book and book['retail']:
      if class_obj.has_local():
        offers = [x['price'] for x in class_obj.offers(tb_id_filter(book))]
      if class_obj.has_local() and offers:
        p = max(100 * (1 - float(min(offers))/float(book['retail'])), float(book['saved']) if 'saved' in book else 0)
      elif 'used' in book and book['used']:
        p = max(100 * (1 - float(book['used'])/float(book['retail'])), float(book['saved']) if 'saved' in book else 0)
      elif 'new' in book and book['new']:
        p = max(100 * (1 - float(book['new'])/float(book['retail'])), float(book['saved']) if 'saved' in book else 0)
      else:
        p = float(book['saved'] if 'saved' in book else 0)
    elif 'saved' in book and book['saved']:
      p = float(book['saved'])
    all_p.append(p)
  p = int(max(all_p))
  return "up to {p}%".format(p=p) if p and p > 20 else 'a ton'

@app.template_filter('tb_len')
def tb_len_filter(textbooks):
  s = 0
  for section in textbooks['sections'].values():
    s += len(section)
  return s

@app.template_filter('queue_length')
def queue_length_filter(t):
  return queue.find({'queue': t}).count()

@app.template_filter('classes_length')
def classes_length_filter(s):
  return classes.find({'error': None}).count()

@app.template_filter('errors_length')
def errors_length_filter(s):
  return classes.find({'error': {'$ne': None}}).count()

@app.template_filter('get_display_names')
def get_display_names_filter(classes):
  return [x.display_name() for x in classes]

@app.template_filter('get_half_star')
def get_half_star_filter(i):
  return float('.'+str(i).split('.')[-1]) > 0.5

@app.template_filter('get_cache_buster')
def get_cache_buster_filter(s):
  return os.environ.get('REV', '')

if __name__ == '__main__':
  if os.environ.get('PORT'):
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT')),debug=dev)
  else:
    app.run(host='0.0.0.0',port=5000,debug=dev)
