import io
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use('Agg')
plt.style.use('seaborn-v0_8-white')


def plot_all(data, results):

    fig, axes = plt.subplots(2, 2, figsize=(16, 8))

    plot_pressure_over_temperature_full(axes[0, 0], data, results)
    plot_pressure_over_temperature(axes[0, 1], data, results)
    plot_pressure_and_temperature(axes[1, 0], data, results)
    plot_mass(axes[1, 1], data, results)

    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=300)
    img.seek(0)
    plt.close()

    return img


def plot_individual(data, results):

    plot_functions = [plot_pressure_over_temperature_full,
                      plot_pressure_over_temperature,
                      plot_mass,
                      plot_pressure_and_temperature]
    plot_images = []

    for plot_func in plot_functions:

        plt.figure(figsize=(10, 4.5))
        axis = plt.gca()
        plot_func(axis, data, results)

        img = io.BytesIO()
        plt.savefig(img, format='png', dpi=300)
        img.seek(0)
        plt.close()

        plot_images.append(img)

    return plot_images


def plot_pressure_over_temperature_full(axis, data, results):

    axis.plot(data.time - data.time.iloc[0], data['P/T'], label='pressure / temperature', lw=2)
    axis.plot([], [], label='system temperature', lw=1, c='C3')
    axis.plot(data.time[data.include] - data.time.iloc[0], data['trendline_P/T'][data.include], label='P/T trendline', ls='--', lw=1.5)

    axis.axvline(data.time[data.include].iloc[0] - data.time.iloc[0], ls='--', lw=1, c='k', label='analysis start & end point')
    axis.axvline(data.time[data.include].iloc[-1] - data.time.iloc[0], ls='--', lw=1, c='k')
    axis.plot([], [], label='24-hour period', ls='--', lw=0.5, c='k')

    axis.plot(data.time[data.include].iloc[0] - data.time.iloc[0], data['P/T'][data.include].iloc[0], markersize=10, marker='x', c='k')

    plot_period_lines(axis, data, full_range=True)

    axis.set_title('Pressure divided by Temperature\n(displayed over full range of uploaded data)')
    axis.set_ylabel('Pressure / Temperature [bar/K]')
    axis.set_xlabel('Time [hours]')

    twin_axis = axis.twinx()
    twin_axis.plot(data.time - data.time.iloc[0], data.temperature, lw=1, c='C3')
    twin_axis.set_ylabel('Temperature [°C]')

    handles, labels = axis.get_legend_handles_labels()
    handles_twin, labels_twin = twin_axis.get_legend_handles_labels()

    twin_axis.legend(handles + handles_twin, labels + labels_twin, frameon=True, loc='best')


def plot_pressure_over_temperature(axis, data, results):

    trendline_label = f"P/T trendline: {trendline_formula(results['trendline_parameters_P/T'])}"

    axis.plot(data.time[data.include], data['P/T'][data.include], label='pressure / temperature', lw=1)
    axis.plot(data.time[data.include], data['trendline_P/T'][data.include], label=trendline_label, ls='--', lw=3)

    plot_period_lines(axis, data)

    axis.axvline(data.time[data.include].iloc[0], ls='--', lw=1, c='k')
    axis.axvline(data.time[data.include].iloc[-1], ls='--', lw=1, c='k')
    axis.plot([], [], label='24-hour period', ls='--', lw=0.5, c='k')

    axis.set_title('Pressure divided by Temperature\n(displayed over selected analysis period)')
    axis.set_ylabel('Pressure / Temperature [bar/K]')
    axis.set_xlabel('Time [hours]')
    axis.legend(frameon=True)


def plot_pressure_and_temperature(axis, data, results):

    axis.plot(data.time[data.include], data.pressure[data.include], label='system pressure', lw=1)
    axis.plot([], [], label='system temperature', lw=1, c='C3')

    axis.axvline(data.time[data.include].iloc[0], ls='--', lw=1, c='k')
    axis.axvline(data.time[data.include].iloc[-1], ls='--', lw=1, c='k')
    axis.plot([], [], label='24-hour period', ls='--', lw=0.5, c='k')

    plot_period_lines(axis, data)

    axis.set_title('Pressure and Temperature\n(displayed over selected analysis period)')
    axis.set_ylabel('Pressure [bar]')
    axis.set_xlabel('Time [hours]')

    twin_axis = axis.twinx()
    twin_axis.plot(data.time[data.include], data.temperature[data.include], lw=1, c='C3')
    twin_axis.set_ylabel('Temperature [°C]')

    handles, labels = axis.get_legend_handles_labels()
    handles_twin, labels_twin = twin_axis.get_legend_handles_labels()

    twin_axis.legend(handles + handles_twin, labels + labels_twin, frameon=True)


def plot_mass(axis, data, results):

    trendline_label = f"mass trendline: {trendline_formula(results['trendline_parameters_mass'])}"

    axis.plot(data.time[data.include], data.mass[data.include], label='system mass', lw=1)
    axis.plot(data.time[data.include], data['trendline_mass'][data.include], label=trendline_label, ls='--', lw=3)

    axis.axvline(data.time[data.include].iloc[0], ls='--', lw=1, c='k')
    axis.axvline(data.time[data.include].iloc[-1], ls='--', lw=1, c='k')
    axis.plot([], [], label='24-hour period', ls='--', lw=0.5, c='k')

    plot_period_lines(axis, data)

    axis.set_title('System Mass\n(displayed over selected analysis period)')
    axis.set_ylabel('Mass [kg]')
    axis.set_xlabel('Time [hours]')
    axis.legend(frameon=True)


def plot_period_lines(axis, data, full_range=False):

    for line in data.time[abs(data.count_period.diff()) > 0]:

        if full_range:
            line -= data.time.iloc[0]

        axis.axvline(line, ls='--', lw=0.5, c='k')


def trendline_formula(results):

    base, exp = f'{results[0]:.2e}'.split('e')
    exp = int(exp)

    return rf"{base}×10$^{{{exp}}}$t + {results[1]:.4f}"
