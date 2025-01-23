from calendar import monthrange
from concurrent.futures.thread import ThreadPoolExecutor
import csv
import datetime as dt
from django.contrib import messages
from django.db.models import Q, OuterRef, Subquery, Prefetch
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.context_processors import csrf
from django.views import View
from django.views.decorators.http import require_POST
import functools
import json
import logging
import numpy as np
import pandas as pd
import re
import time
from tqdm import tqdm
from typing import Tuple
# from .models import Stock, FinancialReport, BalanceSheet, CashFlow, CandleStick
from manage_database.models import Stock, IncomeStatement, BalanceSheet, CashFlow, CandleStick


import pdb

market_cap = {
    'Mega (>$200B)': 200_000_000_000,
    'Large ($10B-$200B)': range(10_000_000_000, 200_000_000_001),
    'Medium ($2B-$10B)': range(2_000_000_000, 10_000_000_001),
    'Small ($300M-$2B)': range(300_000_000, 2_000_000_001),
    'Micro ($50M-$300M)': range(50_000_000, 300_000_001),
    'Nano (<$50M)': range(0, 50_000_001),
}
sectors = ['Basic Materials', 'Technology', 'Industrials', 'Health Care', 'Energy',
           'Consumer Discretionary', 'Real Estate', 'Miscellaneous', 'Telecommunications',
           'Consumer Staples', 'Utilities', 'Finance']
sectors.sort()


class BackTestView(View):
    def __init__(self):
        super().__init__()
        self.long_total = 0
        self.short_total = 0
        self.longshort_annualized = 0

        # Initialize parameter: market cap
        self.market_cap = market_cap

        # # Initialize parameter: fundamental data
        self.financials_data = [separate_words(field.name) for field in IncomeStatement._meta.get_fields() if
                                field.concrete and field.name not in ('id', 'stock', 'date')]
        self.balance_sheet_data = [separate_words(field.name) for field in BalanceSheet._meta.get_fields() if
                                   field.concrete and field.name not in ('id', 'stock', 'date')]
        self.cash_flow_data = [separate_words(field.name) for field in CashFlow._meta.get_fields() if
                               field.concrete and field.name not in ('id', 'stock', 'date')]

        # # Initialize other parameters
        self.ipo_years = [5, 4, 3, 2, 1]
        self.backtest_years = [1.5, 1]
        self.pos_hold = [50, 40, 30, 20, 10]
        self.min_stock_price = [1, 2, 3, 4, 5, 10]
        self.re_balancing_months = [
            'Jan, Apr, Jul, Oct',
            'Feb, May, Aug, Nov',
            'Mar, Jun, Sep, Dec',
        ]
        self.sectors = {k: 0 for k in sectors}

        # Setup html context
        self.html_context = {
            'methods_financial': self.financials_data,
            'methods_balance_sheet': self.balance_sheet_data,
            'methods_cash_flow': self.cash_flow_data,
            'market_cap': self.market_cap.keys(),
            'ipo_years': self.ipo_years,
            'sectors': self.sectors,
            'all_stocks_num': 0,
            'backtest_years': self.backtest_years,
            'pos_hold': self.pos_hold,
            'min_stock_price': self.min_stock_price,
            're_balancing_months': self.re_balancing_months,
        }

    def get(self, request):
        # Default parameters
        self.html_context['selected_market_cap'] = list(self.market_cap.keys())[:-1]
        self.html_context['selected_ipo_years'] = 1
        self.html_context['selected_backtest_years'] = 1.5
        self.html_context['selected_pos_hold'] = 20
        self.html_context['selected_min_stock_price'] = 10
        self.html_context['selected_re_balancing_months'] = self.re_balancing_months[1]
        self.html_context['selected_ranking_method'] = 'Descending'
        self.html_context['csrf_token'] = csrf(request)['csrf_token']

        return render(request, 'long_short/index.html', self.html_context)

    def post(self, request):
        # Get user's parameters
        market_cap = request.POST.getlist('market-cap')
        method = request.POST.get('selected-method').rstrip("+-*/")
        ipo_years = int(request.POST.get('ipo_years'))
        sectors = [s for s in self.sectors if request.POST.get(s)]
        backtest_years = float(request.POST.get('backtest_years'))
        pos_hold = int(request.POST.get('pos_hold'))
        min_stock_price = float(request.POST.get('min_stock_price'))
        re_balancing_months = request.POST.get('re_balancing_months')
        ranking_method = request.POST.get('ranking_method')

        # Add to context
        self.html_context.update({
            'selected_market_cap': market_cap,
            'selected_method': method,
            'selected_ipo_years': ipo_years,
            'selected_sectors': sectors,
            'selected_backtest_years': backtest_years,
            'selected_pos_hold': pos_hold,
            'selected_min_stock_price': min_stock_price,
            'selected_re_balancing_months': re_balancing_months,
            'selected_ranking_method': ranking_method
        })

        # Check input validity
        if not market_cap:
            messages.warning(request, 'Please select Market Cap.')
            return render(request, 'long_short/index.html', self.html_context)
        if not method:
            messages.warning(request, 'Please select Method.')
            return render(request, 'long_short/index.html', self.html_context)
        if method.count('(') != method.count(')'):
            messages.warning(request, 'Your method is in-valid, please check.')
            return render(request, 'long_short/index.html', self.html_context)

        # Start backtesting
        self.html_context['data'] = []

        with ThreadPoolExecutor(max_workers=min(len(sectors), 12)) as executor:
            for sector in sectors:
                executor.submit(self.start_backtest, request, market_cap, ipo_years, sector, method, backtest_years,
                                pos_hold, min_stock_price, re_balancing_months, ranking_method)

        # Sort result by sector
        self.html_context['data'] = sorted(self.html_context['data'], key=lambda d: d['sector'])

        # Update html context
        self.html_context['result'] = True
        self.html_context['long_total'] = round(self.long_total, 2)
        self.html_context['short_total'] = round(self.short_total, 2)
        self.html_context['longshort_total'] = round(self.long_total - self.short_total, 2)
        self.html_context['longshort_annualized'] = round(self.longshort_annualized / len(sectors), 2)

        return render(request, 'long_short/index.html', self.html_context)

    def start_backtest(self, request, market_cap, ipo_years, sector, method, backtest_years, pos_hold, min_stock_price,
                       re_balancing_months, ranking_method):
        # Get US stocks
        df_us_stocks = get_us_stocks(market_cap, ipo_years, sector)
        if len(df_us_stocks) == 0 and not messages.get_messages(request):
            messages.warning(request, 'No stocks found, please adjust your filter.')
            return

        # Get re-balancing dates
        l_re_balancing_dates = get_re_balancing_dates(re_balancing_months, backtest_years)

        # Get result by method chose
        results = get_result_from_method(method, df_us_stocks, min_stock_price, l_re_balancing_dates,
                                         self.financials_data, self.balance_sheet_data, self.cash_flow_data)

        # Ranking and split results
        result_subset = ranking(results, ranking_method, min_stock_price)

        # Get performance for each re-balancing date
        df_top, df_bottom = get_performance(result_subset, pos_hold)
        if df_top.empty or df_bottom.empty:
            messages.warning(request, f"No financial data available for {sector}, please adjust your filter.")
            return

        # Add average performance to the top stocks, and bottom stocks
        get_average_performance(df_top)
        get_average_performance(df_bottom)

        # Calculate total performance for long and short stocks
        long_total = df_top.iloc[-1].sum(skipna=True)
        short_total = df_bottom.iloc[-1].sum(skipna=True)

        # Format dataframe
        for df in (df_top, df_bottom):
            df.rename(columns={'Performance': 'Perf(%)'}, inplace=True)
            df.replace(np.nan, "", inplace=True)

        # Round to 3 decimals
        df_top = df_top.map(lambda x: round(x, 3) if isinstance(x, (int, float)) else x)
        df_bottom = df_bottom.map(lambda x: round(x, 3) if isinstance(x, (int, float)) else x)

        # Rename column names from 'result-%b %y' to '%m/%y-%m/%y'
        rename_cols = {}
        for col in df_top.columns:
            if 'result-' in col:
                from_date = extract_date_suffix(col)
                to_month = from_date.month + 2
                if to_month > 12:
                    to_date = from_date.replace(year=from_date.year + 1, month=to_month - 12)
                else:
                    to_date = from_date.replace(month=to_month)
                rename_cols[col] = f'{from_date.strftime("%m/%y")} - {to_date.strftime("%m/%y")}'
        df_top.rename(columns=rename_cols, inplace=True)
        df_bottom.rename(columns=rename_cols, inplace=True)

        # Change unit (billion/ million/ thousand)
        def divide_columns(df, divisor, column_contains):
            # Select columns that match the pattern
            cols = df.columns[df.columns.str.contains(column_contains)]

            # Divide the selected columns by the divisor
            df[cols] = df[cols].map(
                lambda x: round(x / divisor, 3) if isinstance(x, (int, float)) and not np.isnan(x) else x
            )

            return df

        if len(df_top) > 1:
            max_value = max(pd.to_numeric(df_top.loc[0], errors='coerce').dropna())
            min_value = min(pd.to_numeric(df_bottom.loc[0], errors='coerce').dropna())

        # Set html context
        long_annualized = df_top.loc['Average'].apply(pd.to_numeric, errors='coerce').mean()
        short_annualized = df_bottom.loc['Average'].apply(pd.to_numeric, errors='coerce').mean()
        longshort_annualized = round((long_annualized - short_annualized) / 2 * 4, 2)
        self.long_total += long_total
        self.short_total += short_total
        self.longshort_annualized += longshort_annualized
        d = {
            'sector': sector,
            'df_top': df_top,
            'df_bottom': df_bottom,
            'long_total': round(long_total, 2),
            'short_total': round(short_total, 2),
            'longshort_total': round(long_total - short_total, 2),
            'longshort_annualized': longshort_annualized,
        }
        self.html_context['data'].append(d)


def separate_words(string: str) -> str:
    """
    To separate words, e.g. from 'ResearchAndDevelopment' to 'Research And Development'
    """
    return re.sub(r"(?<![A-Z])(?=[A-Z])", " ", string).strip()


def get_us_stocks(market_cap_filter: list = [], min_ipo_years: int = 0,
                  sector_filter: str | list = None) -> pd.DataFrame:
    """
    Return us stocks based on selected market cap, min ipo years, and sectors.
    """
    market_cap_str = list(market_cap.keys())
    market_cap_value = list(market_cap.values())

    # Get selected market cap
    mega = market_cap_str[0] in market_cap_filter
    large = market_cap_str[1] in market_cap_filter
    medium = market_cap_str[2] in market_cap_filter
    small = market_cap_str[3] in market_cap_filter
    micro = market_cap_str[4] in market_cap_filter
    nano = market_cap_str[5] in market_cap_filter

    # Setup query
    mega_q = Q(market_cap__gte=market_cap_value[0]) if mega else Q()
    large_q = Q(market_cap__range=[market_cap_value[1][0], market_cap_value[1][-1]]) if large else Q()
    medium_q = Q(market_cap__range=[market_cap_value[2][0], market_cap_value[2][-1]]) if medium else Q()
    small_q = Q(market_cap__range=[market_cap_value[3][0], market_cap_value[3][-1]]) if small else Q()
    micro_q = Q(market_cap__range=[market_cap_value[4][0], market_cap_value[4][-1]]) if micro else Q()
    nano_q = Q(market_cap__range=[market_cap_value[5][0], market_cap_value[5][-1]]) if nano else Q()
    if sector_filter:
        if isinstance(sector_filter, str):
            sector_q = Q(sector=sector_filter)
        elif isinstance(sector_filter, list):
            sector_q = Q(sector__in=sector_filter)
        else:
            sector_q = Q()
    else:
        sector_q = Q()

    # Query database
    results = Stock.objects.filter(
        # todo: to be reviewed
        # (mega_q | large_q | medium_q | small_q | micro_q | nano_q),
        sector_q,
        ipo_year__lte=dt.datetime.today().year - min_ipo_years,
        ticker__regex=r'^[a-zA-Z]{1,4}$',
    )

    # Convert to dataframe
    results = pd.DataFrame(results.values())
    results.rename(columns={'ticker': 'Ticker'}, inplace=True)

    return results


def get_re_balancing_dates(re_balancing_months: str, backtest_years: float = 1) -> list:
    # Convert string to a list: 'Jan, Apr, Jul, Nov' -> ['Jan', ' Apr', ' Jul', ' Nov']
    re_balancing_months = re_balancing_months.split(',')

    # Convert string to int: ['Jan', ' Apr', ' Jul', ' Nov'] -> [1, 4, 7, 11]
    for i, d in enumerate(re_balancing_months):
        re_balancing_months[i] = dt.datetime.strptime(d.strip(), '%b').month

    # Get first re-balancing date: (today minus backtest_year)
    backtest_from = dt.datetime.now() - dt.timedelta(days=365 * backtest_years)

    # Define backtest_from
    if backtest_from.month > re_balancing_months[-1]:
        backtest_from = backtest_from.replace(month=re_balancing_months[-1], day=1).date()
    else:
        for month in re_balancing_months:
            if backtest_from.month <= month:
                backtest_from = backtest_from.replace(month=month, day=1).date()
                break

    # Re-order re-balancing month. E.g. if re-balancing month is November, the selected months will be [2, 5, 8, 11], then change the order to [11, 2, 5, 8]
    new_re_balancing_months = []
    for i, v in enumerate(re_balancing_months):
        if backtest_from.month == v:
            new_re_balancing_months = re_balancing_months[i:] + re_balancing_months[:i]
            break

    # Get a list of re-balancing date
    re_balancing_dates = []
    finished = False
    while backtest_from.year <= dt.datetime.now().year and not finished:
        for m in new_re_balancing_months:
            if backtest_from > dt.date.today():
                finished = True
                break
            re_balancing_dates.append(backtest_from.replace(month=m))
            if m == re_balancing_months[-1]:
                backtest_from = backtest_from.replace(year=backtest_from.year + 1)

    return re_balancing_dates


def get_result_from_method(formula: str,
                           us_stocks: pd.DataFrame,
                           min_stock_price: float,
                           re_balancing_dates: list,
                           financials_data: list,  # ['Basic EPS', 'EPS', ...]
                           balance_sheet_data: list,
                           cash_flow_data: list) -> pd.DataFrame:
    # Extract data names from method
    datas = re.findall(r'\w+(?:\s+\w+)*', formula)
    datas = [data.replace(' ', '').strip() for data in datas]

    # Format data names - E.g. from 'Basic EPS' to 'BasicEPS'
    financials_data = [data.replace(' ', '').strip() for data in financials_data]
    balance_sheet_data = [data.replace(' ', '').strip() for data in balance_sheet_data]
    cash_flow_data = [data.replace(' ', '').strip() for data in cash_flow_data]
    formula = formula.replace(' ', '').strip()

    # Initialize results
    result = us_stocks[['Ticker']].copy()

    # # Loop through re-balancing dates
    stock_list = result['Ticker'].tolist()
    for date in re_balancing_dates:
        # Filter with the stock price lower than min_stock_price within 30 days
        date_ = dt.datetime.combine(date, dt.datetime.min.time()).replace(tzinfo=dt.timezone.utc)
        df_candlesticks = pd.DataFrame(
            list(CandleStick.objects.filter(
                stock__ticker__in=stock_list,
                date__lt=date_,
                date__gt=date_ - dt.timedelta(days=30),
                adj_close__gte=min_stock_price,
            ).values())
        )
        valid_stocks_id = set(df_candlesticks['stock_id'])

        # Get report date (3 months before the re-balancing date e.g. if re-balancing date: 1 Nov, then report dates: 30 Sep, 31 Aug, 31 Jul)
        report_dates = []
        for month_ago in reversed(range(2, 5)):
            report_month = date.month - month_ago
            if report_month < 1:
                report_year = date.year - 1
                report_month = 12 + report_month
                last_day = monthrange(report_year, report_month)[-1]
                report_date = date.replace(year=report_year, month=report_month, day=last_day)
            else:
                last_day = monthrange(date.year, report_month)[-1]
                report_date = date.replace(month=report_month, day=last_day)
            report_dates.append(report_date)

        # Loop through data points
        for data in datas:
            # Create dataframe for financial reports
            if data in [f.name for f in IncomeStatement._meta.get_fields()]:
                reports = pd.DataFrame(
                    IncomeStatement.objects.filter(
                        stock__id__in=valid_stocks_id,
                        date__in=report_dates
                    ).order_by('date')
                    .values('stock__ticker', data))
            elif data in [f.name for f in BalanceSheet._meta.get_fields()]:
                reports = pd.DataFrame(
                    BalanceSheet.objects.filter(
                        stock__id__in=valid_stocks_id,
                        date__in=report_dates
                    ).order_by('date')
                    .values('stock__ticker', data))
            elif data in [f.name for f in CashFlow._meta.get_fields()]:
                reports = pd.DataFrame(
                    CashFlow.objects.filter(
                        stock__id__in=valid_stocks_id,
                        date__in=report_dates
                    ).order_by('date')
                    .values('stock__ticker', data))
            else:
                logging.warning(f"Unknown method: {data}")
                continue

            # Update data
            reports = reports.rename(columns={'stock__ticker': 'Ticker'})
            result = result.merge(reports, how='left', on='Ticker')

        # Calculate result
        result_col_name = f'result-{dt.date.strftime(date, "%b %y")}'
        result = apply_formula(result, formula, result_col_name)
        result = result.infer_objects(copy=False).replace([np.inf, -np.inf], np.nan)

        # Delete data columns
        result.drop(columns=datas, inplace=True)

    return result


def apply_formula(df: pd.DataFrame, formula: str, result_col_name: str) -> pd.DataFrame:
    # Replace columns names
    for col in df.columns:
        formula = formula.replace(col, f'df["{col}"]')

    # Evaluate
    df[result_col_name] = eval(formula)

    return df


@require_POST
def search_method(request):
    """
    Search the method in Income Statement, Balance Sheet and Cash Flow, and return to the front-end.
    :param request: Request
    :return: {result: [method1, method2, ...]}
    """
    search_str = json.loads(request.body).get('search_text')
    if search_str.strip() == '':
        return JsonResponse({'result': []})

    fields_financials = [separate_words(field.name) for field in IncomeStatement._meta.get_fields() if
                         field.concrete and field.name not in ('id', 'stock', 'date')]
    fields_balancesheet = [separate_words(field.name) for field in BalanceSheet._meta.get_fields() if
                           field.concrete and field.name not in ('id', 'stock', 'date')]
    fields_cashflow = [separate_words(field.name) for field in CashFlow._meta.get_fields() if
                       field.concrete and field.name not in ('id', 'stock', 'date')]
    all_fields = fields_financials + fields_balancesheet + fields_cashflow
    results = [method for method in all_fields if search_str.lower() in method.lower()]

    return JsonResponse({'result': results})


@require_POST
def update_stock_numbers(request):
    # Get params from frontend
    data = json.loads(request.body)
    selected_market_cap = data.get('market_cap')
    selected_sectors = data.get('sectors')
    if 'All' in selected_sectors:
        selected_sectors.remove('All')

    # Get US stocks
    stocks = get_us_stocks(market_cap_filter=selected_market_cap, sector_filter=selected_sectors)

    result = {}

    # Update stocks by sector
    for sector in sectors:
        result[sector] = len(stocks[stocks['sector'] == sector])
    result['All'] = sum(result.values())

    # todo: to be reviewed
    # # Update stocks by market cap
    # for mc in market_cap:
    #     if 'Mega' in mc:
    #         result[mc] = len(stocks[stocks['market_cap'] >= market_cap[mc]])
    #     else:
    #         result[mc] = len(stocks[
    #                              (stocks['market_cap'] >= market_cap[mc][0]) &
    #                              (stocks['market_cap'] < market_cap[mc][-1])
    #                              ])

    return JsonResponse({'result': result})


def ranking(results: pd.DataFrame, ranking_method: str, min_stock_price: float) -> dict:
    result_subset = {}
    result_cols = [col for col in results.columns if col.startswith('result')]
    ascending = True if ranking_method == 'Ascending' else False
    for col in result_cols:
        result = results[['Ticker', col]].dropna()
        result = result[result[col] != 0]
        result_subset[col] = result[['Ticker', col]].sort_values(by=col, ascending=ascending)

    return result_subset


def get_performance(result_subset: dict, pos_hold: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # Setup from_month
    next_month = f"result-{dt.date.strftime(dt.date.today() + dt.timedelta(days=30), '%b %y')}"
    l_from_months = list(result_subset.keys())
    l_to_months = l_from_months[1:] + [next_month]

    # Get all tickers
    tickers = [ticker['Ticker'].tolist() for ticker in result_subset.values()]
    stock_list = []
    for list_ in tickers:
        stock_list += list_

    # Create candlestick dataframe for the tickers
    df_candlesticks = pd.DataFrame(
        list(CandleStick.objects.filter(
            stock__ticker__in=set(stock_list),
            date__gte=extract_date_suffix(l_from_months[0]).replace(tzinfo=dt.timezone.utc),
            date__lte=extract_date_suffix(l_to_months[-1]).replace(tzinfo=dt.timezone.utc),
        ).values('stock__ticker', 'date', 'open', 'adj_close'))
    )
    df_candlesticks = df_candlesticks.rename(columns={'stock__ticker': 'ticker'})

    # Loop through the re-balancing months
    for from_month, to_month in tqdm(zip(l_from_months, l_to_months), desc="Updating quarterly performance..."):
        # Initialize performance
        df = result_subset[from_month]
        df['Performance'] = np.nan

        # Format start_date and end_date: result-May 23 -> 2023-05-01
        start_date = extract_date_suffix(from_month).replace(tzinfo=dt.timezone.utc)
        end_date = extract_date_suffix(to_month).replace(tzinfo=dt.timezone.utc)

        # In case of today == from_month
        if start_date == end_date:
            end_date = dt.datetime.today().replace(tzinfo=dt.timezone.utc)

        # Extract top and bottom stocks
        half_rows_num = min(pos_hold, len(df) // 2)
        df = pd.concat([df.head(half_rows_num), df.tail(half_rows_num)])

        # Get performance change for each symbol
        for i, row in df.iterrows():
            # Check if candlesticks data exists
            if not row['Ticker'] in set(df_candlesticks['ticker'].tolist()):
                logging.warning(f"No candlesticks data for ticker {row['Ticker']}")
                continue

            # Check if candlesticks data is too far away from re-balancing date
            candles = df_candlesticks[
                (df_candlesticks['ticker'] == row['Ticker']) &
                (df_candlesticks['date'] >= start_date) &
                (df_candlesticks['date'] < end_date)
                ]
            if candles.head(1)['date'].tolist()[0] > start_date + dt.timedelta(days=10):
                logging.warning(
                    f"Start date of candlestick for ticker {row['Ticker']} > 10 days from re-balancing date, skip this ticker.")
                continue
            if candles.tail(1)['date'].tolist()[0] < end_date - dt.timedelta(days=10) and to_month != l_to_months[-1]:
                logging.warning(
                    f"End date of candlestick for ticker {row['Ticker']} < 10 days from end of re-balancing date, skip this ticker.")
                continue

            # Calculate performance
            try:
                price_from = float(candles['open'].iloc[0])
                price_to = float(candles['adj_close'].iloc[-1])
                df.at[i, 'Performance'] = round((price_to / price_from - 1) * 100, 2)
            except Exception as e:
                logging.warning(f"Ticker: {row['Ticker']}: Error getting price: {str(e)}")
                df.at[i, 'Performance'] = np.nan

        # Add result to subset
        result_subset[from_month] = df

    # Combine results
    df_top = pd.DataFrame()
    df_bottom = pd.DataFrame()
    for key, result in result_subset.items():
        half_rows_num = min(pos_hold, len(result) // 2)

        # Add top stocks
        df_top_new = result.head(half_rows_num)
        df_top_new.reset_index(inplace=True, drop=True)
        df_top.reset_index(inplace=True, drop=True)
        df_top = pd.concat([df_top, df_top_new], axis=1)

        # Add bottom stocks
        df_bottom_new = result.tail(half_rows_num)
        df_bottom_new.reset_index(inplace=True, drop=True)
        df_bottom.reset_index(inplace=True, drop=True)
        df_bottom = pd.concat([df_bottom, df_bottom_new], axis=1)

    return df_top, df_bottom


def get_average_performance(df: pd.DataFrame):
    # Save original columns first, then deal with duplicate columns
    original_cols = df.columns.copy()

    # Rename all columns
    df.columns = [f'col_{i}' for i in range(len(df.columns))]

    # Add mean row
    mean_row = df.select_dtypes(include=[np.number]).mean()
    df.loc['Average'] = round(mean_row, 2)

    # Restore original columns
    df.columns = original_cols

    # Remove values in the mean row except all performance columns
    non_performance_cols = [col for col in df.columns if col != 'Performance' and col != 'Ticker']
    df.loc['Average', non_performance_cols] = np.nan


def extract_date_suffix(date_str: str) -> dt.datetime | None:
    date_pattern = re.compile(r'-(\w+ \d{2})$')
    match = date_pattern.search(date_str)

    return dt.datetime.strptime(match.group(1), '%b %y') if match else None


def export_csv(request):
    # Get existing portfolio
    file = None
    if request.FILES.get('file'):
        file = request.FILES['file']
    try:
        df_portfolio = pd.read_csv(file)

        # Replace the position to 0 if there is Exit Price
        if 'Exit Price' in df_portfolio.columns:
            df_portfolio.loc[df_portfolio['Exit Price'].notna(), 'Position'] = 0

        df_portfolio = df_portfolio[['Financial Instrument', 'Position']]
        df_portfolio['Financial Instrument'] = df_portfolio['Financial Instrument'].str.split(' ').str[0]
        replace_position = {
            'K': 1000,
            'M': 1000000,
            "'": "",
            ",": ""
        }
        df_portfolio['Position'] = df_portfolio['Position'].replace(np.nan, 0)
        df_portfolio['Position'] = df_portfolio['Position'].replace(replace_position, regex=True).astype(int)
        df_portfolio.rename(columns={'Financial Instrument': 'Ticker', 'Position': 'Existing Position'}, inplace=True)
    except Exception as e:
        logging.warning(f"Error: {e}")
        df_portfolio = pd.DataFrame(columns=['Ticker', 'Existing Position'])

    # Get top and bottom stocks from backtest results
    data = json.loads(request.POST['table_data'])

    # Convert to dataframe for top stocks
    amount = abs(int(request.POST['amount']))
    df_top_stocks = convert_backtest_table_to_dataframe(data['long_table'], amount)
    df_bottom_stocks = convert_backtest_table_to_dataframe(data['short_table'], amount)
    df_bottom_stocks['Expected Position'] = -df_bottom_stocks['Expected Position']

    # Calculate execute position (to close the unnecessary positions from existing positions)
    df_execute = pd.concat([df_top_stocks, df_bottom_stocks], ignore_index=True)
    df_execute = pd.merge(df_execute, df_portfolio, on='Ticker', how='outer')
    df_execute['Existing Position'] = df_execute['Existing Position'].infer_objects(copy=False).fillna(0)
    df_execute['Expected Position'] = df_execute['Expected Position'].infer_objects(copy=False).fillna(0)
    df_execute['Execute Position'] = df_execute['Expected Position'].astype(float) - df_execute['Existing Position']
    df_execute['Execute Position'] = df_execute['Execute Position'].round(2)
    df_execute = df_execute[['Ticker', 'Execute Position']]
    df_execute = df_execute[df_execute['Execute Position'] != 0]

    # Create basket trader dataframe
    basket_trader_cols = ['Action', 'Quantity', 'Symbol', 'SecType', 'Exchange', 'Currency', 'TimeInForce',
                          'OrderType', 'BasketTag', 'Account', 'OrderRef', 'LmtPrice', 'UsePriceMgmtAlgo', 'OutsideRth']
    basket_tag = 'LONG/SHORT'
    df_basket_trader = pd.DataFrame(columns=basket_trader_cols)
    df_basket_trader['Symbol'] = df_execute['Ticker']
    df_basket_trader['Quantity'] = df_execute['Execute Position']
    df_basket_trader['Action'] = np.where(df_basket_trader['Quantity'] >= 0, 'BUY', 'SELL')
    df_basket_trader['SecType'] = 'STK'
    df_basket_trader['Exchange'] = 'SMART/NASDAQ/NYSE/ARCA'
    df_basket_trader['Currency'] = 'USD'
    df_basket_trader['TimeInForce'] = 'OPG'
    df_basket_trader['OrderType'] = 'MKT'
    df_basket_trader['BasketTag'] = basket_tag
    df_basket_trader['Account'] = ''
    df_basket_trader['OrderRef'] = basket_tag
    df_basket_trader['LmtPrice'] = 0
    df_basket_trader['UsePriceMgmtAlgo'] = 'TRUE'
    df_basket_trader['OutsideRth'] = 'FALSE'

    # Write csv response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="basket_trader.csv"'
    writer = csv.writer(response)
    writer.writerow(basket_trader_cols)
    for index, row in df_basket_trader.iterrows():
        writer.writerow(row.tolist())

    return response


def convert_backtest_table_to_dataframe(tables: list, amount: int) -> pd.DataFrame:
    # loop through the first table and the second level of columns
    columns = []
    for col in tables[0][1]:
        # Replace the column 'Value' to the first level of columns of the first table (date string)
        columns.append(col) if col != 'Value' else columns.append(tables[0][0].pop(0))

    # Append to dataframe
    df = pd.DataFrame(columns=columns)
    for table in tables:
        # Exclude the first 2 rows, they are column names
        df = pd.concat([df, pd.DataFrame(columns=columns, data=table[2:])])

    # Extract the last 3 columns (the latest re-balancing period)
    df = df.iloc[:, -3:]

    # Remove empty rows
    df = df[df['Ticker'] != '']

    # Assign amount for each stock
    df['Amount(USD)'] = amount // 2 // len(df)

    # Get previous adj_close for each stock
    re_balancing_date_str = df.columns[1].split(' ')[0]
    re_balancing_date = dt.datetime.strptime(re_balancing_date_str, '%m/%y').replace(tzinfo=dt.timezone.utc)
    df['Previous Adj Close'] = df['Ticker'].map(
        lambda ticker: get_previous_close(ticker, re_balancing_date)
    )

    # Assign position for each stock
    df['Expected Position'] = df['Amount(USD)'] / df['Previous Adj Close']

    return df


def get_previous_close(ticker: str, date: dt.datetime) -> float:
    if not ticker:
        return 0

    stock = Stock.objects.get(ticker=ticker)
    if not stock:
        return 0

    candlestick = CandleStick.objects.filter(stock=stock, date__lt=date.replace(tzinfo=dt.timezone.utc))
    return candlestick.last().adj_close
