#!/usr/bin/env python

import flask_s3
from textbooks import app

flask_s3.create_all(app)