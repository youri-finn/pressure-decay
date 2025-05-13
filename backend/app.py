import io
import tempfile
import json
from datetime import datetime
import pandas as pd
from flask import Flask, request, render_template, session, send_file
from utils.validation import file_validation, parameter_validation
from utils.analysis import data_processing, data_analysis
from utils.plot import plot_all, plot_individual
from utils.export import export_word

app = Flask(__name__)
app.secret_key = 'this_secret_key_is_secret'


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

    parameters_file = tempfile.NamedTemporaryFile(delete=False)
    with open(parameters_file.name, 'w') as f:
        json.dump(parameters, f)

    results_file = tempfile.NamedTemporaryFile(delete=False)
    with open(results_file.name, 'w') as f:
        json.dump(results, f)

    data_file = tempfile.NamedTemporaryFile(delete=False)
    data.to_json(data_file.name)
    data_file.close()

    session['parameters'] = parameters_file.name
    session['results'] = results_file.name
    session['data'] = data_file.name

    return render_template('index.html', params=parameters, results=results, errors=None)


@app.route('/instructions')
def show_instructions():
    return render_template('instructions.html')


@app.route('/plot')
def get_plot():

    data = session.get('data')
    results = session.get('results')

    if not data or not results:
        return "missing files", 400

    data = pd.read_json(data)
    with open(results, 'r') as f:
        results = json.load(f)

    img = plot_all(data, results)
    return send_file(img, mimetype='image/png')


@app.route('/export')
def export_data():

    data = session.get('data')
    parameters = session.get('parameters')
    results = session.get('results')

    if not data or not results:
        return "missing files", 400

    data = pd.read_json(data)

    with open(parameters, 'r') as f:
        parameters = json.load(f)

    with open(results, 'r') as f:
        results = json.load(f)

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

    return send_file(file, as_attachment=True, download_name=file_name,
                     mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
