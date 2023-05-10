
import celery
from upscale import upscale
from celery.result import AsyncResult
from flask import jsonify

app = celery.Celery(
    backend='redis://127.0.0.1:6379/2',
    broker='redis://127.0.0.1:6379/1',
)

# проблема с Windows команда не работает - celery -A tasks.app worker
# решение  pip install eventlet
# запуск worker ов  - celery -A tasks.app worker -l info -P eventlet

@app.task
def transform_image(filename, save_path):
    upscale.upscale(f'uploads/{filename}', save_path, model_path='upscale/EDSR_x2.pb')


# делаем запрос к celery c id
@app.task
def check_result(task_id):
    task = AsyncResult(task_id, app=app)
    return jsonify({'status': task.status, 'result': task.result})
