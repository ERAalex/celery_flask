import os

from flask import Flask, render_template, request, send_from_directory, url_for

#!!! внимание надо зайти в библиотеку flask_uploads и подправить импорт на
# from werkzeug.utils import secure_filename
# from werkzeug.datastructures import  FileStorage

from flask_uploads import UploadSet, IMAGES, configure_uploads
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask import jsonify, request, send_file
from werkzeug.utils import secure_filename
from wtforms import SubmitField
from tasks import transform_image, check_result

import datetime
import redis

redis_server = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)


# https://www.youtube.com/watch?v=dP-2NVUgh50

app_flask = Flask(__name__)
app_flask.config['SECRET_KEY'] = 'sdsdsdsdds'
app_flask.config['UPLOADED_PHOTOS_DEST'] = 'uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


photos = UploadSet('photos', IMAGES)
configure_uploads(app_flask, photos)


class UploadForm(FlaskForm):
    photo = FileField(
        validators=[
            FileAllowed(photos, 'Только картинки допускаются к загрузке'),
            FileRequired('Поле не может быть пустым')
        ]
    )
    submit = SubmitField('Upload')


@app_flask.route('/uploads/<filename>')
def get_file(filename):
    return send_from_directory(app_flask.config['UPLOADED_PHOTOS_DEST'], filename)


@app_flask.route("/", methods=['GET', 'POST'])
def upload_image():

    # Загрузка картинки через Сайт - страницу
    file_url = 0
    form = UploadForm()
    if form.validate_on_submit():
        filename = photos.save(form.photo.data)
        file_url = url_for('get_file', filename=filename)

        #запускаем обработку Celery-Redis
        async_result = transform_image.delay(filename, filename)

    # API POST - загрузка картинки на сервер и ее обработка
    if request.method == 'POST':
        if 'file' not in request.files:
            return {'error': 'файл не загружен'}
        file = request.files['file']

        if file.filename == '':
            return {'error': 'файлов нет'}
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app_flask.config['UPLOADED_PHOTOS_DEST'], filename))

            # запускаем обработку Celery-Redis
            async_result = transform_image.delay(filename, f'image_done/{filename}')

            # сохраняем в Redis ключ-значение, чтобы потом достать картинку для загрузки
            redis_server.set(f'{async_result.id}', filename)

            return {'Файл загружен его id_задачи для проверки': f'{async_result.id}'}

    # API - запрос на проверку наличия картинки
    if request.method == 'GET':
        if 'task_id' not in request.form:
            return {'Вы не задали параметр': 'task_id'}
        task_id = request.form['task_id']

        result = check_result(task_id).json
        if result['status'] == 'SUCCESS':

            # идем в Redis и ищем картинку по ключу-id
            path = f"image_done/{redis_server.get(f'{task_id}')}"
            return send_file(path, as_attachment=True)

        return result

    else:
        file_url = None

    return render_template('index.html',  form=form, file_url=file_url)






if __name__ == '__main__':
    app_flask.run()




