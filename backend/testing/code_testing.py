import io
import pandas as pd
import mimetypes
import pytest
from datetime import datetime
from backend.utils.validation import file_validation, parameter_validation


class FileObjectWithAttrs:
    def __init__(self, path):
        self.file = open(path, 'r')  # open in text mode for CSV
        self.filename = path.split('/')[-1]
        self.mimetype = mimetypes.guess_type(path)[0] or 'text/csv'

    def read(self, *args, **kwargs):
        return self.file.read(*args, **kwargs)

    def __iter__(self):
        return iter(self.file)

    def close(self):
        self.file.close()


test_file = FileObjectWithAttrs('csv_test_file.csv')

valid_input = {'system_name': 'some_name ',
               'start_row': '1',
               'col_date': '2',
               'col_pressure': '3',
               'col_temperature': '5',
               'format_date': 'simex',
               'unit_pressure': 'bara',
               'unit_temperature': 'C',
               'custom_format': '',
               'volume': '55.0',
               'unit_volume': 'liter',
               'medium': 'CO2',
               'start_time': '2024-09-20T16:02',
               'end_time': '2024-09-20T16:04',
               'periodic_limit_off': 'checked'
               }

valid_validation_output = {'system_name': 'some_name',
                           'start_row': 1,
                           'col_date': 2,
                           'col_pressure': 3,
                           'col_temperature': 5,
                           'format_date': 'simex',
                           'unit_pressure': 'bara',
                           'unit_temperature': 'C',
                           'custom_format': '',
                           'volume': 55.0,
                           'unit_volume': 'liter',
                           'medium': 'CO2',
                           'start_time': datetime(2024, 9, 20, 16, 2),
                           'end_time': datetime(2024, 9, 20, 16, 4),
                           'periodic_limit_off': True,
                           'mass': None
                           }

valid_df = pd.DataFrame({'date': [datetime(2024, 9, 20, 16, 2, 54),
                                  datetime(2024, 9, 20, 16, 2, 55),
                                  datetime(2024, 9, 20, 16, 2, 56),
                                  datetime(2024, 9, 20, 16, 2, 57),
                                  datetime(2024, 9, 20, 16, 2, 58)],
                         'pressure': [0.1313, 0.0469, 0.1313, -0.1500, 0.1313],
                         'temperature': [28.94, 28.92, 28.92, 28.94, 28.94]})


def make_input(dictionary, overrides):
    base = dictionary.copy()
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    'raw_parameters, csv_file, output_parameters, dataframe',
    [
        (valid_input, test_file, valid_validation_output, valid_df),
        (make_input(valid_input, {'unit_volume': 'kg', 'volume': '2.35'}), test_file, make_input(valid_validation_output, {'unit_volume': 'kg', 'volume': None, 'mass': 2.35}), valid_df),
        #(make_input(valid_input, {'volume': '0'}), test_file, ValueError, valid_df),
    ]
)
def test_validation_processing(raw_parameters, csv_file, output_parameters, dataframe):

    print(raw_parameters, '\n', output_parameters)
    parameters = parameter_validation(raw_parameters)
    data = file_validation(csv_file, parameters)

    assert ((parameters, data), (output_parameters, dataframe)), f"{parameters, output_parameters}"











@pytest.mark.parametrize(
    'raw_parameters, expected_types',
    [
        (
                {'system_name': 'some_name ',
                 'start_row': '1',
                 'col_date': '2',
                 'col_pressure': '8',
                 'col_temperature': '4',
                 'format_date': 'simex',
                 'unit_pressure': 'bara',
                 'unit_temperature': 'C',
                 'custom_format': '%d/%m/%Y %H:%M',
                 'volume': '55.0',
                 'unit_volume': 'liter',
                 'medium': 'CO2',
                 'start_time': '2025-01-27T14:18',
                 'end_time': '2025-02-04T12:22',
                 'periodic_limit_off': 'checked'
                 },
                {'system_name': str,
                 'start_row': int,
                 'col_date': int,
                 'col_pressure': int,
                 'col_temperature': int,
                 'format_date': str,
                 'unit_pressure': str,
                 'unit_temperature': str,
                 'custom_format': str or None,
                 'volume': float,
                 'unit_volume': str,
                 'medium': str,
                 'start_time': datetime,
                 'end_time': datetime,
                 'periodic_limit_off': bool,
                 'mass': None or float}
        )
    ]
)
def test_parameter_validation_output_types(raw_parameters, expected_types):
    result = parameter_validation(raw_parameters)

    for key, expected_type in expected_types.items():
        assert isinstance(result[key], expected_type), f"{key} is not {expected_type.__name__}"
