import io
import os
import tempfile
import json
from datetime import datetime
import pandas as pd
from flask import Flask, request, render_template, session, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from utils.validation import file_validation, parameter_validation
from utils.analysis import data_processing, data_analysis
from utils.plot import plot_all, plot_individual
from utils.export import export_word

app = Flask(__name__)
app.secret_key = 'this_secret_key_is_secret'

APP_ENV = os.getenv('APP_ENV', 'local')

if APP_ENV == 'local':
    TEMP_DIR = 'tmp'
else:
    TEMP_DIR = os.path.join('backend', 'tmp')


def cleanup_files():
    for filename in os.listdir(TEMP_DIR):
        filepath = os.path.join(TEMP_DIR, filename)

        try:
            os.remove(filepath)
        except Exception:
            continue


scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_files, trigger='cron', hour=3, minute=0)
scheduler.start()


@app.route('/')
def index():
    return render_template('index.html', params=None, results=None, errors=None)


@app.route('/analysis', methods=['POST'])
def upload_file():

    file = request.files.get('file')
    raw_parameters = request.form.to_dict()

    try:
        parameters = parameter_validation(raw_parameters)
        data = file_validation(file, parameters)
    except Exception as e:
        return render_template('index.html', params=raw_parameters, results=None, errors=e)

    try:
        data, parameters = data_processing(data, parameters)
        data, results = data_analysis(data, parameters)
    except Exception as e:
        return render_template('general_error.html', params=parameters, results=None, errors=e)

    parameters = {key: value.isoformat() if isinstance(value, (datetime, pd.Timestamp)) else value
                  for key, value in parameters.items()}

    with tempfile.NamedTemporaryFile(delete=False, dir='tmp', mode='w') as file:
        json.dump(parameters, file)
        session['parameters'] = file.name

    with tempfile.NamedTemporaryFile(delete=False, dir='tmp', mode='w') as file:
        json.dump(results, file)
        session['results'] = file.name

    with tempfile.NamedTemporaryFile(delete=False, dir='tmp', mode='w') as file:
        file.write(data.to_json())
        session['data_path'] = file.name

    return render_template('index.html', params=parameters, results=results, errors=None)


@app.route('/instructions')
def show_instructions():
    return render_template('instructions.html')


@app.route('/plot')
def get_plot():

    data = session.get('data_path')
    results = session.get('results')

    if not data or not results:
        return "missing files", 400

    data = pd.read_json(data)
    with open(results, 'r') as file:
        results = json.load(file)

    img = plot_all(data, results)
    return send_file(img, mimetype='image/png')


@app.route('/export')
def export_data():

    data_path = session.get('data_path')
    parameters = session.get('parameters')
    results = session.get('results')

    if not data_path or not results:
        return "missing files", 400

    with open(parameters, 'r') as file:
        parameters = json.load(file)

    with open(results, 'r') as file:
        results = json.load(file)

    try:
        data = pd.read_json(data_path)
    except (ValueError, FileNotFoundError):
        return render_template('index.html', params=parameters, results=None, errors='data file cannot be read. data has either been deleted or is not present (data will automatically delete after export)')

    images = plot_individual(data, results)

    try:
        doc = export_word(parameters, results, images)
    except Exception as e:
        return render_template('general_error.html', params=parameters, results=None, errors=e)

    file = io.BytesIO()
    doc.save(file)
    file.seek(0)

    current_date = datetime.now().strftime('%Y%m%d')
    file_name = current_date + '_pressure-decay-test_' + parameters['system_name'].replace(' ', '_') + '.docx'

    os.remove(data_path)

    return send_file(file, as_attachment=True, download_name=file_name,
                     mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')


if __name__ == "__main__":
    if APP_ENV == 'local':
        app.run(debug=True)
    else:
        app.run(host="0.0.0.0", port=8080)
