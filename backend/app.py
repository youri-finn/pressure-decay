import io

from flask import Flask, request, render_template, session, send_file, url_for
from datetime import datetime
from analysis import analyze_data, generate_plot
from export import export_word
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = 'some_kind_of_secret_key'
UPLOAD_FOLDER = 'tempfiles'
ALLOWED_EXTENSIONS = ('csv', 'xls', 'xlsx')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html', file_name=None, params=None, output=None, errors=None)


@app.route('/analysis', methods=['POST'])
def upload_file():

    file = request.files['file']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    params = request.form.to_dict()
    success, result = validate_inputs(file_path, params)

    if success:
        params = result
    else:
        return render_template('index.html', file_name=None, params=params, output=None, errors=result)

    df, output = analyze_data(file_path, params)
    # try:
    #     df, output = analyze_data(file_path, params)
    # except Exception as exp:
    #     return render_template('general_error.html', file_name=None, params=params, output=None, errors=exp)

    df_csv_path = os.path.join(UPLOAD_FOLDER, 'df.csv')
    df.to_csv(df_csv_path, index=False)

    session['file_path'] = file_path
    session['params'] = request.form
    session['df_path'] = df_csv_path
    session['output'] = output

    print(params, output)

    return render_template('index.html', file_name=file_path, params=params, output=output)


@app.route('/plot')
def get_plot():

    # we can edit this only to use dataframe for the time axis (maybe not even)
    df = pd.read_csv(session['df_path'])
    # params = format_inputs(session['params'])

    img = generate_plot(df)
    return send_file(img, mimetype='image/png')

@app.route('/export')
def export_data():

    params = session['params']
    output = session['output']

    df = pd.read_csv(session['df_path'])
    image = generate_plot(df)
    doc = export_word(params, output, image)

    file = io.BytesIO()
    doc.save(file)
    file.seek(0)

    current_date = datetime.now().strftime('%Y%m%d')
    file_name = current_date + '_pressure-decay-test_' + params['system_name'].replace(' ', '_') + '.docx'

    return send_file(file, as_attachment=True, download_name=file_name, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')


def validate_inputs(file_path, params):

    # blanket error throw if parameters cannot be formatted
    try:
        params = format_inputs(params)
    except Exception as exp:
        return False, "input parameters are not correct: " + str(exp)

    # check for correct extensions
    if not file_path.endswith(ALLOWED_EXTENSIONS):
        return False, "uploaded file type not allowed, only .csv, .xls and .xlsx are accepted"

    # check if column numbers do not exceed total amount of columns available in the uploaded file
    row_nums, col_nums = get_shape(file_path)
    if max(params['col_date'], params['col_pressure'], params['col_temperature']) > col_nums:
        return False, "column number must not exceed total available columns in file"

    if params['start_row'] > row_nums:
        return False, "starting row must not exceed total available rows in file"

    # for now, volume cannot be zero or blank
    if params['volume'] == 0:
        return False, "volume/mass cannot be zero"

    try:
        # check if start time is not later than end time
        if params['start_time'] > params['end_time']:
            return False, "start time must begin before end time"
        # check if total time is not lower than 24 hours
        if (params['end_time'] - params['start_time']).total_seconds() < 24 * 3600:
            return False, "the uploaded data must be at least 24 hours of data"
    except TypeError:
        print('A TypeError was thrown between comparing the start and end times, this will be caught in the analysis '
              'part')

    return True, params


def format_inputs(params):

    params['start_row'] = int(params['start_row'])
    params['col_date'] = int(params['col_date'])
    params['col_pressure'] = int(params['col_pressure'])
    params['col_temperature'] = int(params['col_temperature'])

    params['system_name'] = params['system_name'].strip()

    if params['volume'] != '':
        params['volume'] = float(params['volume'])
    else:
        params['volume'] = 0

    if params['start_time'] != '':
        params['start_time'] = datetime.strptime(params['start_time'], '%Y-%m-%dT%H:%M')

    if params['end_time'] != '':
        params['end_time'] = datetime.strptime(params['end_time'], '%Y-%m-%dT%H:%M')

    return params


def get_shape(file_path):

    line = None

    if file_path.endswith('csv'):
        line = pd.read_csv(file_path)

    elif file_path.endswith(('xls', 'xlsx')):
        line = pd.read_excel(file_path)
    print(line.shape)
    return line.shape


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
    # app.run(debug=True)
