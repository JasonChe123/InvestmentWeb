import datetime as dt
from django.shortcuts import render
import json
import logging
import os
import requests


def us_economy(request):
    # data, x_axis_label = get_us_yield_curve_10y2y()

    data = [1.5, 1, 1.2, 1, 0.5, 0, -1, 0, 1, 2]
    x_axis_label = [v for v in data]

    context = {
        'chart_t10y2y': {
            'data': data,
            'x_axis_label': json.dumps(x_axis_label),
        }
    }

    return render(request, 'us_economy/index.html', context)


def get_us_yield_curve_10y2y():
    url_base = 'https://api.stlouisfed.org/'
    endpoint = 'fred/series/observations'
    fred_api_key = os.getenv('FRED_API_KEY')
    series_id = 'T10Y2Y'
    params = {
        'api_key': fred_api_key,
        'file_type': 'json',
        'series_id': series_id,
    }
    res = requests.get(url_base + endpoint, params=params)

    if res.status_code != 200:
        logging.error(f'Error getting series from FRED: {res.json()}')
        return [], []

    # Get data and labels
    res = res.json()
    observations = res['observations']
    data = [None if v['value'] == '.' else float(v['value']) for v in observations[-5000:]]
    x_labels = [v['date'] for v in observations[-5000:]]

    # Get data for every 7 days
    new_data = []
    new_x_labels = []
    days = 0
    for d, label in zip(data, x_labels):
        if days % 7 == 0 and d:
            new_data.append(d)
            new_x_labels.append(label)
        days += 1

    return new_data, new_x_labels