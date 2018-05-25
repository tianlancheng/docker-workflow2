# -*- coding: utf-8 -*-
from flask import Flask
from flask import request
from flask import jsonify
import json,os
import docker
from config import config
from flask_pymongo import PyMongo




app = Flask(__name__)
app.config.from_object(config['default'])


mongo = PyMongo(app)

from .dag import dag
from .operator import operator
app.register_blueprint(dag,url_prefix='/api')
app.register_blueprint(operator,url_prefix='/api')

