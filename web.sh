if [ "$dev" == "True" ]; then
	python textbooks.py
else
	echo "$cert" > cert.pem
	newrelic-admin run-program gunicorn -b "0.0.0.0:$PORT" textbooks:app -w $WEB_CONCURRENCY -k gevent --preload
fi