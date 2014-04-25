if [ "$dev" == "True" ]; then
        python textbooks.py
else
		gunicorn -b "0.0.0.0:$PORT" textbooks:app
fi