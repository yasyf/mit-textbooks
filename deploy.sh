#!/bin/bash

echo "Deploying Web"
git checkout -b web_procfile
echo "web: ./web.sh" > Procfile
git add Procfile
git commit -m 'web Procfile'
git push heroku web_procfile:master --force
git checkout master

echo "Deploying Workers"
git checkout -b worker_procfile
echo "worker: ./worker.sh" > Procfile
git add Procfile
git commit -m 'worker Procfile'
git push worker-1 worker_procfile:master --force
git push worker-2 worker_procfile:master --force
git push worker-3 worker_procfile:master --force
git checkout master

git branch -D web_procfile
git branch -D worker_procfile