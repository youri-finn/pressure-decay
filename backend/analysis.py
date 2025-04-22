import numpy as np
import pandas as pd
from CoolProp.CoolProp import PropsSI
import matplotlib
import matplotlib.pyplot as plt
import io

matplotlib.use('Agg')


def main():
    pass


if __name__ == "__main__":
    main()


def parse_date_format(date_series, format_type, custom_format=None):

    #print(date_series.iloc[0])
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
        except (ValueError, TypeError):
            try:
                return pd.to_datetime(date_series)
            except (ValueError, TypeError):
                raise Exception(f'{format_type.upper()} date format of file could not be parsed')
    else:
        raise ValueError('date format not in list of available formats')


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


def volume_conversion(unit):

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


def compute_density(row, medium):

    if medium == 'forming':
        medium = 'nitrogen[0.95]&hydrogen[0.05]'

    try:
        return PropsSI('D', 'T', row.temperature + 273.15, 'P', row.pressure*1e5, medium)
    except Exception:
        return np.nan


def compute_volume(df, mass, medium):

    if medium == 'forming':
        medium = 'nitrogen[0.95]&hydrogen[0.05]'

    pt = df.loc[df.pt.idxmax(), 'pt_trend']
    temperature = df.loc[df.pt.idxmax(), 'temperature']

    density = PropsSI('D', 'T', temperature + 273.15, 'P', pt*(temperature + 273.15)*1e5, medium)

    return mass/density


def gas_rate(slope, volume):
    return round(-slope * 100000 * volume * 44.009 * 24 * 365.25 / 8.3145)


def mass_rate(slope):
    return round(-slope * 24 * 365.25 * 1000)


def bubble_rate(slope, density):
    return round((-slope * 6 / 3600 / np.pi / density )**(1/3) * 1000, 1)


def analyze_data(file, params):

    if file.endswith('csv'):
        df = pd.read_csv(file)
    elif file.endswith(('xls', 'xlsx')):
        df = pd.read_excel(file)
    else:
        raise Exception('input files not of type csv, xls or xlsx')

    mass_input = False
    if params['unit_volume'] in ['kg', 'gr']:
        mass_input = True

    col_indices = [params['col_date'] - 1, params['col_pressure'] - 1, params['col_temperature'] - 1]
    df = df.iloc[params['start_row'] - 1:, col_indices].reset_index(drop=True)
    df.columns = ['date', 'pressure', 'temperature']

    df.date = parse_date_format(df.date, params['format_date'], params['custom_format'])

    try:
        df.pressure = df.pressure.astype('float')
        df.temperature = df.temperature.astype('float')
    except Exception:
        raise Exception('The selected pressure and/or temperature columns do not contain exclusively numerical data')

    if params['start_time'] == '' or params['start_time'] < df.date.iloc[0]:
        params['start_time'] = df.date.iloc[0].round('min')

    if params['end_time'] == '' or params['end_time'] > df.date.iloc[-1]:
        params['end_time'] = df.date.iloc[-1].round('min')

    start_time_conditional = df.date.dt.round('min') <= params['start_time']
    end_time_conditional = df.date.dt.round('min') <= params['end_time']

    # start and end time rows
    new_rows = pd.DataFrame([
        {'date': params['start_time'],
         'pressure': df[start_time_conditional].iloc[-1]['pressure'],
         'temperature': df[start_time_conditional].iloc[-1]['temperature']},

        {'date': params['end_time'],
         'pressure': df[end_time_conditional].iloc[-1]['pressure'],
         'temperature': df[end_time_conditional].iloc[-1]['temperature']}
    ])

    # slicing data between user start and end time
    df = df[(df.date >= params['start_time']) & (df.date <= params['end_time'])]

    # adding user start and end time entries to dataframe
    df = pd.concat([df, new_rows]).sort_values(by='date').reset_index(drop=True)

    # downgrading data to take data at 5 min intervals for speed
    df['resampled_time'] = df['date'].dt.floor('5min')
    df = df.groupby('resampled_time').mean().reset_index()

    # time in hours from start
    df['time'] = (df.date - df.date[0]).dt.total_seconds()/3600

    # unit conversions
    df.pressure = pressure_conversion(params['unit_pressure'])(df.pressure)
    df.temperature = temperature_conversion(params['unit_temperature'])(df.temperature)

    mass, volume = None, None

    # unit conversions for either mass or volume
    if mass_input:
        mass = volume_conversion(params['unit_volume'])(params['volume'])
    else:
        volume = volume_conversion(params['unit_volume'])(params['volume'])

    # calculations
    df['pt'] = df.apply(lambda row: row.pressure/(row.temperature + 273.15), axis=1)
    df['density'] = df.apply(lambda x: compute_density(x, params['medium']), axis=1)
    df = df.dropna()

    if len(df) == 0:
        raise Exception('Medium is not correct for data inserted')

    min_period = 24  # hours
    max_time = df.time.iloc[-1]

    # counting for 24 hour increments from end
    df['day_count'] = (df.time - (max_time % min_period)) // min_period + 1
    df.day_count = df.day_count.astype(int)

    # trendline of p/t data
    slope_pt, intercept_pt = np.polyfit(df.time[df.day_count > 0], df.pt[df.day_count > 0], 1)
    df['pt_trend'] = np.poly1d([slope_pt, intercept_pt])(df.time)

    if mass_input:
        try:
            volume = compute_volume(df, mass, params['medium'])
        except Exception:
            raise Exception('something went wrong with the volume calculation from the input mass, '
                            'try estimating the system volume')
        system_volume = round(volume*1000, 1)
    else:
        system_volume = ''

    # calculation of mass
    df['mass'] = df['density']*volume

    # trendline of mass data
    slope_mass, intercept_mass = np.polyfit(df.time[df.day_count > 0], df.mass[df.day_count > 0], 1)
    df['mass_trend'] = np.poly1d([slope_mass, intercept_mass])(df.time)

    output = gas_rate(slope_pt, volume), mass_rate(slope_mass), \
        bubble_rate(slope_mass, df.density.mean()), system_volume, mass_input, intercept_mass

    return df, output


def generate_plot(df):

    fig, ax = plt.subplots(3, 1, figsize=(10, 13), sharex=True)

    ax[0].plot(df.time, df.pressure, label='System Pressure', lw=1)

    for day in df.day_count.unique()[1:]:
        line = df.time[df.day_count == day].iloc[0]
        ax[0].axvline(line, ls='--', lw=0.5, c='k')

    ax[0].set_title('Pressure Decay Plot')
    ax[0].set_ylabel('Pressure (bar)')
    ax[0].legend()

    # p/t plot

    slope = (df.pt_trend.iloc[-1] - df.pt_trend.iloc[0]) / (df.time.iloc[-1] - df.time.iloc[0])
    intercept = df.pt_trend.iloc[-1] - slope*df.time.iloc[-1]

    ax[1].plot(df.time, df.pt, label='P/T', lw=1)
    ax[1].plot(df.time[df.day_count > 0], df.pt_trend[df.day_count > 0], label=f'trendline: {slope: .2e}t +{intercept: .4f}', ls='--', lw=3)

    ax2 = ax[1].twinx()
    # ax2.plot(df.time, df.pt, c='C1', label='P/T/h')

    for day in df.day_count.unique()[1:]:
        line = df.time[df.day_count == day].iloc[0]
        ax[1].axvline(line, ls='--', lw=0.5, c='k')

    ax[1].set_title('P/T Decay Plot')
    ax[1].set_ylabel('P/T (bar/K)')
    ax[1].legend()

    # mass plot

    slope = (df.mass_trend.iloc[-1] - df.mass_trend.iloc[0]) / (df.time.iloc[-1] - df.time.iloc[0])
    intercept = df.mass_trend.iloc[-1] - slope*df.time.iloc[-1]

    ax[2].plot(df.time, df.mass, label='System Mass', lw=1)
    ax[2].plot(df.time[df.day_count > 0], df.mass_trend[df.day_count > 0], label=f'trendline: {slope: .2e}t +{intercept: .3f}', ls='--', lw=3)

    for day in df.day_count.unique()[1:]:
        line = df.time[df.day_count == day].iloc[0]
        ax[2].axvline(line, ls='--', lw=0.5, c='k')

    ax[2].set_title('Mass Decay Plot')
    ax[2].set_ylabel('Mass (kg)')
    ax[2].legend()
    ax[2].set_xlabel('Time (hours)')

    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()

    return img
