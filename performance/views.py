import datetime as dt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views import View
import logging
import numpy as np
import pandas as pd
from long_short_strategy.models import Stock, CandleStick



class PerformanceView(View):
    def get(self, request):
        return render(request, 'performance/index.html')

    def post(self, request):
        uploaded_file = request.FILES.get('portfolio_file')

        # Empty file
        try:
            df = pd.read_csv(uploaded_file)
        except pd.errors.EmptyDataError:
            messages.warning(request, "The file is empty or not in .csv format.")
            return render(request, 'performance/index.html')

        # Invalid columns
        if not {'Financial Instrument', 'Position', 'Avg Price'}.issubset(df.columns):
            messages.warning(request, "The file must contain 'Financial Instrument', 'Position' and 'Avg Price' columns.")
            return render(request, 'performance/index.html')

        # Invalid data
        replace_position = {'K': 1000, 'M': 1000000, "'": "", ",": ""}
        df['Position'] = df['Position'].replace(replace_position, regex=True)
        try:
            df['Position'] = df['Position'].astype(float)
            df['Avg Price'] = df['Avg Price'].astype(float)
        except ValueError:
            messages.warning(request, "Invalid data in 'Position'/'Avg Price' column, please check the file.")
            return render(request, 'performance/index.html')

        # Format data
        try:
            df = df[['Financial Instrument', 'Position', 'Avg Price']]
            df = df.dropna()
            df['Financial Instrument'] = df['Financial Instrument'].str.split(' ').str[0]
            df['Avg Price'] = df['Avg Price'].round(2)
            df['Last Price'] = df['Financial Instrument'].apply(get_last_close).astype(float)
        except Exception as e:
            logging.warning(f"Error: {e}")
            messages.warning(request, "Something wrong in your file, please check.")
            return render(request, 'performance/index.html')

        # Split into positive and negative
        df = df.sort_values('Position', ascending=True)
        mask = np.where(df['Position'] >= 0, True, False)
        df_positive = df[mask]
        df_negative = df[~mask]

        # Sort by Ticker
        df_positive = df_positive.sort_values('Financial Instrument', ascending=True)
        df_negative = df_negative.sort_values('Financial Instrument', ascending=True)

        # Add mean row
        df_positive['Performance (%)'] = (df['Last Price'] - df['Avg Price']) / df['Avg Price'] * 100
        df_negative['Performance (%)'] = (df['Avg Price'] - df['Last Price']) / df['Avg Price'] * 100
        df_positive['Performance (%)'] = df_positive['Performance (%)'].replace(-100, np.nan)
        df_negative['Performance (%)'] = df_negative['Performance (%)'].replace(100, np.nan)
        df_positive['Performance (%)'] = df_positive['Performance (%)'].round(2)
        df_negative['Performance (%)'] = df_negative['Performance (%)'].round(2)
        mean_positive = round(df_positive['Performance (%)'].mean(), 2)
        mean_negative = round(df_negative['Performance (%)'].mean(), 2)

        context = {
            'portfolio': [
                [df_positive, len(df_positive), mean_positive],
                [df_negative, len(df_negative), mean_negative],
            ],
        }
        return render(request, 'performance/index.html', context)


@login_required
def home(request):
    if request.method == 'get':
        return render(request, 'performance/index.html')
    elif request.method == 'POST':
        return get_portfolio(request)
    else:
        return render(request, 'performance/index.html')


def get_portfolio(request):
    uploaded_file = request.FILES.get('portfolio_file')

    # Empty file
    try:
        df = pd.read_csv(uploaded_file)
    except pd.errors.EmptyDataError:
        messages.warning(request, "The file is empty or not in .csv format.")
        return render(request, 'performance/index.html')

    # Invalid columns
    if not {'Financial Instrument', 'Position', 'Avg Price'}.issubset(df.columns):
        messages.warning(request, "The file must contain 'Financial Instrument', 'Position' and 'Avg Price' columns.")
        return render(request, 'performance/index.html')

    # Invalid data
    replace_position = {'K': 1000, 'M': 1000000, "'": "", ",": ""}
    df['Position'] = df['Position'].replace(replace_position, regex=True)
    try:
        df['Position'] = df['Position'].astype(float)
        df['Avg Price'] = df['Avg Price'].astype(float)
    except ValueError:
        messages.warning(request, "Invalid data in 'Position'/'Avg Price' column, please check the file.")
        return render(request, 'performance/index.html')

    # Format data
    try:
        df = df[['Financial Instrument', 'Position', 'Avg Price']]
        df = df.dropna()
        df['Financial Instrument'] = df['Financial Instrument'].str.split(' ').str[0]
        df['Avg Price'] = df['Avg Price'].round(2)
        df['Last Price'] = df['Financial Instrument'].apply(get_last_close).astype(float)
    except Exception as e:
        logging.warning(f"Error: {e}")
        messages.warning(request, "Something wrong in your file, please check.")
        return render(request, 'performance/index.html')

    # Split into positive and negative
    df = df.sort_values('Position', ascending=True)
    mask = np.where(df['Position'] >= 0, True, False)
    df_positive = df[mask]
    df_negative = df[~mask]

    # Sort by Ticker
    df_positive = df_positive.sort_values('Financial Instrument', ascending=True)
    df_negative = df_negative.sort_values('Financial Instrument', ascending=True)

    # Add mean row
    df_positive['Performance (%)'] = (df['Last Price'] - df['Avg Price']) / df['Avg Price'] * 100
    df_negative['Performance (%)'] = (df['Avg Price'] - df['Last Price']) / df['Avg Price'] * 100
    df_positive['Performance (%)'] = df_positive['Performance (%)'].replace(-100, np.nan)
    df_negative['Performance (%)'] = df_negative['Performance (%)'].replace(100, np.nan)
    df_positive['Performance (%)'] = df_positive['Performance (%)'].round(2)
    df_negative['Performance (%)'] = df_negative['Performance (%)'].round(2)
    mean_positive = round(df_positive['Performance (%)'].mean(), 2)
    mean_negative = round(df_negative['Performance (%)'].mean(), 2)

    context = {
        'portfolio': [
            [df_positive, len(df_positive), mean_positive],
            [df_negative, len(df_negative), mean_negative],
        ],
    }
    return render(request, 'performance/index.html', context)


def get_last_close(ticker: str) -> float:
    today = dt.datetime.today().replace(tzinfo=dt.timezone.utc)
    stock = Stock.objects.filter(ticker=ticker.strip())
    if not stock:
        return 0.0

    stock = stock.first()
    candlesticks = CandleStick.objects.filter(stock=stock, date__gte=today-dt.timedelta(days=30), date__lte=today)
    if not candlesticks:
        return 0.0

    # Candlestick data may too far away from re-balancing date
    candlestick_end_date = candlesticks.last().date
    if candlestick_end_date < today - dt.timedelta(days=10):
        logging.warning(f"[ {ticker} ] Candlestick data is too far away.")
        return 0.0

    value = candlesticks.last().adj_close
    return round(value, 2) if value else 0.0
