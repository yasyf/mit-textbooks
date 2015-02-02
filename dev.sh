if [ "$is_worker" == "True" ]; then
  python monitor.py
else
  if [ "$dev" == "True" ]; then
    memcached -d
    python textbooks.py
    killall memcached
  else
    echo "$cert" > cert.pem
    gunicorn -b "0.0.0.0:$PORT" textbooks:app
  fi
fi
