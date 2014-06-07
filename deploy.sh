#!/bin/bash

WEB=0
RECOMMENDERS=0
WORKERS=0

case "$1" in
	web) 
		WEB=1
		;;
	recommenders)
		RECOMMENDERS=1
		;;
	workers)
		WORKERS=1
		;;
	all)
		WORKERS=1
		WEB=1
		RECOMMENDERS=1
		;;
	*)
		WEB=1
		;; 
esac


if [[ WEB -eq 1 ]]; then
	echo "Deploying Web"
	heroku config:set REV=$(git rev-parse HEAD) --app mit-textbooks
	git checkout -b web_procfile
	echo "web: ./web.sh" > Procfile
	git add Procfile
	git commit -m 'web Procfile'
	git push heroku web_procfile:master --force
	git checkout master
	git branch -D web_procfile
	for i in `seq 1 10`; do
		curl -s 'http://textbooksearch.mit.edu/' > /dev/null &
    done
fi

if [[ RECOMMENDERS -eq 1 ]]; then
	echo "Deploying Recommenders"
	git checkout -b recommender_procfile
	echo "worker: ./recommender.sh" > Procfile
	git add Procfile
	echo -e "\nnumpy==1.7.0\nscipy==0.11.0\nscikit-learn==0.14.1\npandas==0.13.1" >> requirements.txt
	git add requirements.txt
	git commit -m 'recommender Procfile and requirements.txt'
	git push recommender-1 recommender_procfile:master --force
	git push recommender-2 recommender_procfile:master --force
	git push recommender-3 recommender_procfile:master --force
	git checkout master
	git branch -D recommender_procfile
fi

if [[ WORKERS -eq 1 ]]; then
	echo "Deploying Workers"
	git checkout -b worker_procfile
	echo "worker: ./worker.sh" > Procfile
	git add Procfile
	git commit -m 'worker Procfile'
	git push worker-1 worker_procfile:master --force
	git push worker-2 worker_procfile:master --force
	git push worker-3 worker_procfile:master --force
	git checkout master
	git branch -D worker_procfile
fi
