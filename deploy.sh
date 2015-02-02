#!/bin/bash

WEB=0
RECOMMENDERS=0
WORKERS=0
STATIC=0

case "$1" in
  static)
    STATIC=1
    ;;
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


if [[ STATIC -eq 1 ]]; then
  foreman run python upload_static.py
  heroku config:set REV=$(git rev-parse HEAD) --app mit-textbooks
  for i in `seq 1 10`; do
    curl -s 'http://textbooksearch.mit.edu/' > /dev/null &
    done
fi

if [[ WEB -eq 1 ]]; then
  echo "Deploying Web"
  git checkout -b web_procfile
  echo "web: ./web.sh" > Procfile
  git add Procfile
  git commit --amend --no-edit
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
  echo -e "\nnumpy==1.8.1\nscipy==0.14.0\nscikit-learn==0.15.1\npandas==0.14.1\nnose==1.3.4" >> requirements.txt
  git add requirements.txt
  git commit --amend --no-edit
  (git push recommender-1 recommender_procfile:master --force &)
  (git push recommender-2 recommender_procfile:master --force &)
  (git push recommender-3 recommender_procfile:master --force &)
  (git push recommender-4 recommender_procfile:master --force &)
  git checkout master
  git branch -D recommender_procfile
fi

if [[ WORKERS -eq 1 ]]; then
  echo "Deploying Workers"
  git checkout -b worker_procfile
  echo "worker: ./worker.sh" > Procfile
  git add Procfile
  git commit --amend --no-edit
  (git push worker-1 worker_procfile:master --force &)
  (git push worker-2 worker_procfile:master --force &)
  (git push worker-3 worker_procfile:master --force &)
  (git push worker-4 worker_procfile:master --force &)
  git checkout master
  git branch -D worker_procfile
fi
