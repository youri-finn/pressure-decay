import numpy as np
from CoolProp.CoolProp import PropsSI


def data_processing(data, parameters):

    resample_period = '1min'
    periodic_limit = 24  # hours (be careful, as this is also temporarily hardcoded in the export file)

    if not parameters['start_time'] or parameters['start_time'] < data.date.iloc[0]:
        parameters['start_time'] = data.date.iloc[0].round('min')

    if not parameters['end_time'] or parameters['end_time'] > data.date.iloc[-1]:
        parameters['end_time'] = data.date.iloc[-1].round('min')

    data['date_resampled'] = data['date'].dt.floor(resample_period)
    data = data.groupby('date_resampled').mean().reset_index()
    data.drop('date', axis=1, inplace=True)

    data['time'] = (data.date_resampled - parameters['start_time']).dt.total_seconds()/3600

    if parameters['periodic_limit_off']:
        data['include'] = ((data.time >= 0) & (data.date_resampled <= parameters['end_time']))
    else:
        if data.time.iloc[-1] > periodic_limit:
            periods = data.time.iloc[-1] // periodic_limit
            data['include'] = (data.time >= 0) & (data.time <= periods*periodic_limit)
        else:
            raise ValueError('The data from the uploaded file is less than 24 hours, '
                             'use the checkbox to ignore this limitation and plot data shorter than 24 hours')

    data['count_period'] = ((data.time - periodic_limit) // periodic_limit + 2)*data.include

    return data, parameters


def data_analysis(data, parameters):

    data.pressure = pressure_conversion(parameters['unit_pressure'])(data.pressure)
    data.temperature = temperature_conversion(parameters['unit_temperature'])(data.temperature)

    results = {}

    data['P/T'] = data.pressure / (data.temperature + 273.15)
    data['trendline_P/T'], results['trendline_parameters_P/T'] = calculate_trendline(data, 'P/T')

    if parameters['mass']:
        try:
            volume = compute_volume(data, parameters['mass'], parameters['unit_volume'], parameters['medium'])
        except Exception:
            raise Exception('volume calculation did not succeed')
        results['measured_volume'] = round(volume*1000, 1)
    else:
        volume = mass_volume_conversion(parameters['unit_volume'])(parameters['volume'])
        results['measured_volume'] = None

    data['density'] = data.apply(lambda data_row: compute_density(data_row, parameters['medium']), axis=1)
    data.dropna(inplace=True)

    if len(data) == 0:
        raise ValueError('density is not computable for the selected data and chosen gas medium')

    data['mass'] = data['density']*volume
    data['trendline_mass'], results['trendline_parameters_mass'] = calculate_trendline(data, 'mass')

    results['ideal_gas_rate'] = calculate_ideal_gas_rate(results['trendline_parameters_P/T'][0], volume)
    results['mass_rate'] = calculate_mass_rate(results['trendline_parameters_mass'][0])
    results['bubble_rate'] = calculate_bubble_rate(results['trendline_parameters_mass'][0], data.density[data.include].mean())

    results['stabilization_time'] = round(data.time.iloc[0]*-1, 1)
    results['total_test_time'] = round(data.time[data.include].iloc[-1], 1)
    results['periods'] = data.count_period.max()

    return data, results


def calculate_trendline(data, column):

    slope, intercept = np.polyfit(data.time[data.include], data[column][data.include], 1)
    trendline_series = np.poly1d([slope, intercept])(data.time)

    return trendline_series, (slope, intercept)


def pressure_conversion(unit):

    conversions = {
        'bara': lambda p: p,
        'barg': lambda p: p + 1,
        'Pa': lambda p: p / 1e5,
        'kPa': lambda p: p / 100,
        'psi': lambda p: p / 14.5038
    }

    if unit in conversions:
        return conversions[unit]
    else:
        raise ValueError('pressure unit not in list of available conversions')


def temperature_conversion(unit):

    conversions = {
        'C': lambda t: t,
        'K': lambda t: t - 273.15,
        'F': lambda t: (t - 32) * 5/9
    }

    if unit in conversions:
        return conversions[unit]
    else:
        raise ValueError('temperature unit not in list of available conversions')


def mass_volume_conversion(unit):

    conversions = {
        'm3': lambda v: v,
        'liter': lambda v: v / 1000,
        'kg': lambda v: v,
        'gr': lambda v: v / 1000
    }

    if unit in conversions:
        return conversions[unit]
    else:
        raise ValueError('volume/mass unit not in list of available conversions')


def compute_density(data, medium):

    if medium == 'forming gas':
        medium = 'nitrogen[0.95]&hydrogen[0.05]'

    try:
        return PropsSI('D', 'T', data.temperature + 273.15, 'P', data.pressure*1e5, medium)
    except Exception:
        return np.nan


def compute_volume(data, mass, unit_mass, medium):

    if medium == 'forming gas':
        medium = 'nitrogen[0.95]&hydrogen[0.05]'

    mass = mass_volume_conversion(unit_mass)(mass)

    pressure_over_temperature = data.loc[data['P/T'].idxmax(), 'trendline_P/T']
    temperature = data.loc[data['P/T'].idxmax(), 'temperature']

    density = PropsSI('D', 'T', temperature + 273.15, 'P',
                      pressure_over_temperature*(temperature + 273.15)*1e5, medium)

    return mass/density


def calculate_ideal_gas_rate(slope, volume):
    return round(-slope * 100000 * volume * 44.009 * 24 * 365.25 / 8.3145)


def calculate_mass_rate(slope):
    return round(-slope * 24 * 365.25 * 1000)


def calculate_bubble_rate(slope, density):
    return -1 * np.sign(slope) * round((abs(slope) * 6 / 3600 / np.pi / density)**(1/3) * 1000, 1)
