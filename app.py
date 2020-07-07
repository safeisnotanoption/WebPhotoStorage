#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import traceback
import PIL
from PIL import Image

from flask import Flask, url_for, redirect, render_template
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField
from wtforms.validators import InputRequired, Email, Length, EqualTo
from flask_sqlalchemy import SQLAlchemy

import uuid
from datetime import datetime
import pytz


app = Flask(__name__)
# config
app.config['SECRET_KEY'] = 'my_secret_key'
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # 15MB
app.config['DEBUG'] = True
app.config['UPLOAD_FOLDER'] = 'data/'
app.config['THUMBNAIL_FOLDER'] = 'data/thumbnail/'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = set(['gif', 'png', 'jpg', 'jpeg', 'bmp'])

# connect to the database
user, password = 'user', 'password'
host = 'localhost'
db = 'sqlalchemy'  # created MySQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{0}:{1}@{2}/{3}'.format(user, password, host, db)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def create_thumbnail(image):
    try:
        base_width = 80
        img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], image))
        w_percent = (base_width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)
        img.save(os.path.join(app.config['THUMBNAIL_FOLDER'], image))
        return True
    except:
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    app.run(host='0.0.0.0')
