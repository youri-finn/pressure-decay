import pandas as pd
from datetime import datetime


def parameter_validation(parameters):

    parameters = parameters.copy()

    parameters['system_name'] = parameters['system_name'].strip()

    parameters['start_row'] = int(parameters['start_row'])
    parameters['col_date'] = int(parameters['col_date'])
    parameters['col_pressure'] = int(parameters['col_pressure'])
    parameters['col_temperature'] = int(parameters['col_temperature'])

    parameters['volume'] = float(parameters['volume'])

    if parameters['volume'] <= 0:
        raise ValueError('volume or mass cannot be zero')

    if parameters['unit_volume'] in ['kg', 'gr']:
        parameters['mass'] = float(parameters['volume'])
    elif parameters['unit_volume'] in ['liter', 'm3']:
        parameters['mass'] = None
    else:
        raise ValueError('unit for volume/mass not in list of available units')

    if parameters['start_time']:
        parameters['start_time'] = datetime.strptime(parameters['start_time'], '%Y-%m-%dT%H:%M')

    if parameters['end_time']:
        parameters['end_time'] = datetime.strptime(parameters['end_time'], '%Y-%m-%dT%H:%M')

    if parameters['start_time'] and parameters['end_time']:
        if parameters['start_time'] >= parameters['end_time']:
            raise ValueError('end time must be later than the start time')

    parameters['periodic_limit_off'] = 'periodic_limit_off' in parameters

    return parameters


def file_validation(file, parameters):

    data = read_file(file)

    n_rows, n_cols = data.shape
    column_indices = [parameters['col_date'] - 1, parameters['col_pressure'] - 1, parameters['col_temperature'] - 1]

    if max(column_indices) > n_cols:
        raise ValueError('column number must not exceed total available columns in data file')

    if parameters['start_row'] > n_rows + 1:
        raise ValueError('header row must not exceed total available rows in data file')

    data = data.iloc[parameters['start_row'] - 1:, column_indices].reset_index(drop=True)
    data.columns = ['date', 'pressure', 'temperature']

    data.date = parse_date_format(data.date, parameters['format_date'], parameters['custom_format'])

    if data.date.iloc[0] >= data.date.iloc[-1]:
        raise ValueError('end time in the data file must be later than the start time')

    try:
        data.pressure = data.pressure.astype('float')
        data.temperature = data.temperature.astype('float')
    except Exception:
        raise ValueError('the selected pressure and/or temperature column does not exclusively contain numerical data')

    return data


def read_file(file):

    allowed_file_formats = {
        'csv': ['text/csv', 'application/vnd.ms-excel'],
        'xls': ['application/vnd.ms-excel'],
        'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
    }

    if not file or file.filename == '':
        raise FileNotFoundError('no file has been uploaded')

    extension = file.filename.rsplit('.')[-1].lower()
    mimetype = file.mimetype

    if extension not in allowed_file_formats and mimetype not in allowed_file_formats[extension]:
        raise ValueError(f'uploaded file type not allowed, only the following file types are accepted:'
                         f' {allowed_file_formats.keys}')

    if extension == 'csv':
        data = pd.read_csv(file)
    else:
        data = pd.read_excel(file)

    return data


def parse_date_format(date_series, format_type, custom_format=None):

    date_formats = {
        'simex': ("%d/%m/%Y %H:%M:%S", None),
        'scada': ("%Y/%m/%d %H:%M:%S.%f", None),
        'xls': (None, 's'),
        'unix': (None, 's'),
        'custom': (custom_format, None)
    }

    if format_type == 'xls':
        date_series = date_series.apply(lambda t: 86400 * t - 2209161600)

    if format_type in date_formats:
        try:
            return pd.to_datetime(date_series, format=date_formats[format_type][0], unit=date_formats[format_type][1])
        except Exception:
            try:
                return pd.to_datetime(date_series)
            except Exception:
                raise ValueError(f'{format_type.upper()} date format of file could not be parsed')
    else:
        raise ValueError('date format not in list of available formats')
