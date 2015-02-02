if [ "$dev" == "True" ]; then
  python textbooks.py
else
  echo "$cert" > cert.pem
  newrelic-admin run-program gunicorn -b "0.0.0.0:$PORT" textbooks:app --workers $WEB_CONCURRENCY --worker-class gevent --preload
fi
