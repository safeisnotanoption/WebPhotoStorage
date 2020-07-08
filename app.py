#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import PIL
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
import hashlib

from flask import Flask, url_for, redirect, render_template, send_from_directory, flash
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField
from wtforms.validators import InputRequired, Length
from flask_sqlalchemy import SQLAlchemy

import uuid
from datetime import datetime
import pytz

app = Flask(__name__)
# Config
app.config['SECRET_KEY'] = 'my_secret_key'
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # 15MB
app.config['DEBUG'] = True
app.config['UPLOAD_FOLDER'] = 'photos/'
app.config['THUMBNAIL_FOLDER'] = 'photos_thumbnails/'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = set(['gif', 'png', 'jpg', 'jpeg', 'bmp'])

# Connect to the database
user, password = 'user', 'password'
host = 'localhost'
db = 'sqlalchemy'  # created MySQL database
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{0}:{1}@{2}/{3}'.format(user, password, host, db)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Check file extension
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Generate md5
def md5(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# Create thumbnail
def create_thumbnail(img, filename):
    base_width = 80
    w_percent = (base_width / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)
    img.save(os.path.join(app.config['THUMBNAIL_FOLDER'], filename))


# Get camera model and date of creation
def get_exif_data(img):
    info = img.getexif()
    datetime_original = ''
    camera = []
    if info:
        for tag_id in info:
            # get the tag name
            tag = TAGS.get(tag_id, tag_id)
            data = info.get(tag_id)
            # decode bytes
            # if isinstance(data, bytes):
            #     data = data.decode()
            # find our exif data
            if tag == 'DateTimeOriginal':
                datetime_original = data
            if tag == 'Make':
                camera.append(data)
            if tag == 'Model':
                camera.append(data)
    return datetime_original, ', '.join(camera)


def get_filesize(filename):
    return os.path.getsize(filename)


class UploadForm(FlaskForm):
    name = StringField("Введите название фото", validators=[InputRequired("Пожалуйста, введите название фото"),
                                                            Length(min=1, max=100)])
    file = FileField("Выберите файл", validators=[FileRequired(),
                                                  FileAllowed(app.config['ALLOWED_EXTENSIONS'],
                                                              'Разрешены только изображения')])


class StoredImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file = db.Column(db.String(100))
    name = db.Column(db.String(100))
    camera_model = db.Column(db.String(100))
    size = db.Column(db.Integer)
    date_creation = db.Column(db.String(30))
    date_upload = db.Column(db.String(30))
    hash_md5 = db.Column(db.String(100))
    deleted = db.Column(db.Boolean, default=False)

    def __init__(self, file, name, camera_model, size, date_creation, date_upload, hash_md5):
        self.file = file
        self.name = name
        self.camera_model = camera_model
        self.size = size
        self.date_creation = date_creation
        self.date_upload = date_upload
        self.hash_md5 = hash_md5

    def __repr__(self):
        return '<file:%r>' % self.file


@app.route('/', methods=['GET', 'POST'])
def index():
    form = UploadForm()
    if form.validate_on_submit():
        extension = form.file.data.filename.rsplit('.', 1)[1].lower()

        # Check file extension
        if extension.lower() not in app.config['ALLOWED_EXTENSIONS']:
            flash('Ошибка. Неподдерживаемое расширение файла.', 'danger')
            return redirect(url_for('index'))

        # Create a unique filename
        filename = '%s_%s.%s' % (datetime.now(pytz.timezone('Europe/Moscow')).strftime('%d_%H%M%S'),
                                 uuid.uuid4().hex, extension)

        # Upload a photo
        mime_type = form.file.data.mimetype
        if not mime_type.startswith('image'):
            flash('Ошибка. Загружаемый файл не является изображением (в MIME отсутствует image).', 'danger')
            return redirect(url_for('index'))
        path_to_save = app.config['UPLOAD_FOLDER'] + filename
        form.file.data.save(path_to_save)
        date_upload = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y:%m:%d %H:%M:%S')
        hash_md5 = md5(path_to_save)
        size = get_filesize(path_to_save)

        # Duplicate check
        if StoredImage.query.filter_by(size=size, hash_md5=hash_md5).first() is not None:
            os.remove(path_to_save)
            flash('Ошибка: такая фотография уже была загружена на сервер.', 'danger')
            return redirect(url_for('index'))

        # Create a thumbnail and get EXIF data
        try:
            img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        except UnidentifiedImageError:
            os.remove(path_to_save)
            flash('Ошибка: не удалось распознать изображение в файле', 'danger')
            return redirect(url_for('index'))

        create_thumbnail(img, filename)
        date_creation, camera_model = get_exif_data(img)

        # Write to database
        u = StoredImage(filename, form.name.data.strip(), camera_model, size, date_creation, date_upload,
                        hash_md5)
        db.session.add(u)
        db.session.commit()
        flash('Фотография успешно загружена', 'success')
        return redirect(url_for('show_photos'))
    return render_template('index.html', form=form)


# Show our photos
@app.route('/show_photos')
def show_photos():
    articles = StoredImage.query.all()
    return render_template('show_photos.html', articles=articles)


@app.route('/delete_photo/<int:photo_id>', methods=['GET', 'POST'])
def delete_photo(photo_id):
    filename = StoredImage.query.filter_by(id=photo_id).with_entities(StoredImage.file).first()[0]
    try:
        os.remove(app.config['UPLOAD_FOLDER'] + filename)
        os.remove(app.config['THUMBNAIL_FOLDER'] + filename)
    except FileNotFoundError:
        flash('Warning: не удаётся найти указанный файл', 'danger')

    StoredImage.query.filter_by(id=photo_id).delete()
    db.session.commit()

    flash('Фотография успешно удалена', 'success')
    return redirect(url_for('show_photos'))


# serve static files
@app.route("/photos/<string:filename>", methods=['GET'])
def get_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER']), filename=filename)


@app.route("/photos_thumbnails/<string:filename>", methods=['GET'])
def get_thumbnail(filename):
    return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename=filename)


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == "__main__":
    # app.run(host='0.0.0.0')
    app.run(debug=True)
