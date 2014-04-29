#!/bin/bash

git checkout web_procfile
git push heroku web_procfile:master

git checkout worker_procfile
git push worker-1 worker_procfile:master
git push worker-2 worker_procfile:master
git push worker-3 worker_procfile:master

git checkout master