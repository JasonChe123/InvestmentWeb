import calendar
import datetime as dt
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from django.views import View
import logging
import numpy as np
import pandas as pd
import re
from typing import Type
from .models import Stock, FinancialReport, BalanceSheet, CashFlow, CandleStick

market_cap_str = ['Mega (>$200B)',
                  'Large ($10B-$200B)',
                  'Medium ($2B-$10B)',
                  'Small ($300M-$2B)',
                  'Micro ($50M-$300M)',
                  'Nano (<$50M)',
                  ]
market_cap_value = [200_000_000_000,
                    range(10_000_000_000, 20_000_000_001),
                    range(2_000_000_000, 10_000_000_001),
                    range(300_000_000, 2_000_000_001),
                    range(50_000_000, 300_000_001),
                    range(0, 50_000_001),
                    ]


class DashboardView(View):
    def get(self, request):
        return render(request, 'long_short/index.html')


class BackTestView(View):
    def __init__(self):
        super().__init__()

        # Setup market
        self.market_cap = {}
        for s, v in zip(market_cap_str, market_cap_value):
            self.market_cap[s] = v

        # Setup methods
        self.methods_financial = [separate_words(field.name) for field in FinancialReport._meta.get_fields() if
                                  field.concrete and field.name not in ('id', 'stock', 'date')]
        self.methods_balance_sheet = [separate_words(field.name) for field in BalanceSheet._meta.get_fields() if
                                      field.concrete and field.name not in ('id', 'stock', 'date')]
        self.methods_cash_flow = [separate_words(field.name) for field in CashFlow._meta.get_fields() if
                                  field.concrete and field.name not in ('id', 'stock', 'date')]

        # Setup other parameters
        self.ipo_years = [5, 4, 3, 2, 1]
        self.sectors = ['Basic Materials', 'Technology', 'Industrials', 'Health Care', 'Energy',
                        'Consumer Discretionary', 'Real Estate', 'Miscellaneous', 'Telecommunications',
                        'Consumer Staples', 'Utilities', 'Finance']
        self.sectors.sort()
        self.backtest_years = [1.5, 1]
        self.pos_hold = [50, 40, 30, 20, 10]
        self.re_balancing_months = [
            'Jan, Apr, Jul, Oct',
            'Feb, May, Aug, Nov',
            'Mar, Jun, Sep, Dec',
        ]

        # Setup html context
        self.html_context = {
            'methods_financial': self.methods_financial,
            'methods_balance_sheet': self.methods_balance_sheet,
            'methods_cash_flow': self.methods_cash_flow,
            'market_cap': self.market_cap.keys(),
            'ipo_years': self.ipo_years,
            'sectors': self.sectors,
            'backtest_years': self.backtest_years,
            'pos_hold': self.pos_hold,
        }

        self.candle_stick_data = {}

    def get(self, request):
        self.html_context['selected_market_cap'] = list(self.market_cap.keys())[:3]
        self.html_context['selected_ipo_years'] = 1
        self.html_context['selected_backtest_years'] = 1.5
        self.html_context['selected_pos_hold'] = 30
        self.html_context['selected_ranking_method'] = 'Descending'

        return render(request, 'long_short/backtest.html', self.html_context)

    def post(self, request):
        # Get user's parameters
        market_cap = request.POST.getlist('market_cap')
        method = request.POST.get('selected_method').rstrip("+-*/")
        ipo_years = int(request.POST.get('ipo_years'))
        sector = request.POST.get('sectors')
        backtest_years = float(request.POST.get('backtest_years'))
        pos_hold = int(request.POST.get('pos_hold'))
        ranking_method = request.POST.get('ranking_method')

        # Add to context
        self.html_context['selected_market_cap'] = market_cap
        self.html_context['selected_method'] = method
        self.html_context['selected_ipo_years'] = ipo_years
        self.html_context['selected_sectors'] = sector
        self.html_context['selected_backtest_years'] = backtest_years
        self.html_context['selected_pos_hold'] = pos_hold
        self.html_context['selected_ranking_method'] = ranking_method

        # Check input validity
        if not market_cap or not method:
            messages.warning(request, 'No stocks found, please adjust your filter.')
            return render(request, 'long_short/backtest.html', self.html_context)

        # Get US stocks dataframe
        us_stocks = get_us_stocks(market_cap, ipo_years, [sector, ])
        if len(us_stocks) == 0:
            messages.warning(request, 'No stocks found, please adjust your filter.')
            return render(request, 'long_short/backtest.html', self.html_context)

        # Get re-balancing dates
        re_balancing_dates = get_re_balancing_dates(self.re_balancing_months[1], backtest_years)

        # Get result by method chose
        results = get_result_from_method(
            method, us_stocks, re_balancing_dates,
            self.methods_financial, self.methods_balance_sheet, self.methods_cash_flow
        )

        return render(request, 'long_short/backtest.html', self.html_context)

        merged_results = us_stocks.copy()
        if method in self.methods_financial:
            report_table = FinancialReport
        elif method in self.methods_balance_sheet:
            report_table = BalanceSheet
        elif method in self.methods_cash_flow:
            report_table = CashFlow
        else:
            messages.warning(request, "Unknown method.")
        for date in re_balancing_dates:
            # Add result columns to us_stocks dataframe
            result = fetch_data_by_method(date, us_stocks.copy(), method, report_table)
            result = result[['Ticker', result.columns[-1]]]
            merged_results = pd.merge(merged_results, result, on='Ticker', how='left')

        # Ranking and split dataframe by result columns
        result_subset = {}
        result_cols = [col for col in merged_results.columns if col.startswith(f'{method}-')]
        for col in result_cols:
            if ranking_method == 'Descending':
                result_subset[col] = merged_results[['Ticker', col]].sort_values(by=col, ascending=False)
            else:
                result_subset[col] = merged_results[['Ticker', col]].sort_values(by=col, ascending=True)
            # result_subset[col] = merged_results[['Ticker', col]].sort_values(by=col, ascending=False)
            result_subset[col].dropna(inplace=True, subset=[col])

        # Get performance for every re-balancing date
        from_months = list(result_subset.keys())
        to_months = list(result_subset.keys())[1:] + [
            f'{method}-{dt.date.strftime(dt.date.today(), "%b %y")}'
        ]
        for from_month, to_month in zip(from_months, to_months):
            # Initialize performance column
            df = result_subset[from_month]
            df['Performance'] = np.nan

            # Formatting for start_date and end_date: {method}-May 23 -> 2023-05-01
            start_date = extract_date_suffix(from_month).replace(tzinfo=dt.timezone.utc)
            end_date = extract_date_suffix(to_month).replace(tzinfo=dt.timezone.utc)
            if start_date == end_date:
                end_date = dt.datetime.today().replace(tzinfo=dt.timezone.utc)

            # Extract top and bottom stocks
            half_rows_num = min(pos_hold, len(df) // 2)
            df = pd.concat([df.head(half_rows_num), df.tail(half_rows_num)])

            # Get performance changed for symbols
            for i, row in df.iterrows():
                stock = Stock.objects.get(ticker=row['Ticker'])
                candlesticks = CandleStick.objects.filter(stock=stock, date__gte=start_date, date__lt=end_date)

                # Check if candlestick data exists
                if not candlesticks:
                    continue

                # Check if candlestick data is too far away from re-balancing date
                candlestick_start_date = candlesticks.first().date
                candlestick_end_date = candlesticks.last().date
                if candlestick_start_date > candlestick_start_date + dt.timedelta(days=30) or \
                        candlestick_end_date < end_date - dt.timedelta(days=30):
                    logging.warning(f"Candlestick data is too far away: {row['Ticker']}")
                    continue

                # Calculate performance
                from_price = float(candlesticks.first().open)
                to_price = float(candlesticks.last().close)
                df.at[i, 'Performance'] = round((to_price / from_price - 1) * 100, 2)

            # Rename column and add result to subset
            period_str = f'{from_month.replace(method + "-", "")} to {to_month.replace(method + "-", "")}'
            df.rename(columns={from_month: period_str, }, inplace=True)
            result_subset[from_month] = df

        # Combine results
        df_top = pd.DataFrame()
        df_bottom = pd.DataFrame()
        for key, df in result_subset.items():
            df.dropna(inplace=True)
            half_rows_num = min(pos_hold, len(df) // 2)

            # Add top stocks
            new_top = df.head(half_rows_num)
            new_top.reset_index(inplace=True, drop=True)
            df_top.reset_index(inplace=True, drop=True)
            df_top = pd.concat([df_top, new_top], axis=1)

            # Add bottom stocks
            new_bottom = df.tail(half_rows_num)
            new_bottom.reset_index(inplace=True, drop=True)
            df_bottom.reset_index(inplace=True, drop=True)
            df_bottom = pd.concat([df_bottom, new_bottom], axis=1)
        if df_top.empty and df_bottom.empty:
            messages.warning(request, 'No financial data available, please adjust your filter.')

        # It will add mean performance: set it individually because it has same column name 'Performance' for multiple columns
        long_total_performance = round(add_mean_row(df_top), 2)
        short_total_performance = round(add_mean_row(df_bottom), 2)

        # Set html context
        df_top.rename(columns={'Performance': 'Perf(%)'}, inplace=True)
        df_bottom.rename(columns={'Performance': 'Perf(%)'}, inplace=True)
        df_top.replace(np.nan, "", inplace=True)
        df_bottom.replace(np.nan, "", inplace=True)

        self.html_context['df_top'] = df_top
        self.html_context['df_bottom'] = df_bottom
        self.html_context['long_total'] = long_total_performance
        self.html_context['short_total'] = short_total_performance

        return render(request, 'long_short/backtest.html', self.html_context)


def separate_words(string: str) -> str:
    """
    To separate words, e.g. from 'ResearchAndDevelopment' to 'Research And Development'
    """
    return re.sub(r"(?<![A-Z])(?=[A-Z])", " ", string).strip()


def get_us_stocks(market_cap: list, min_ipo_years: int, sectors: list) -> pd.DataFrame:
    # Get selected market cap
    mega = market_cap_str[0] in market_cap
    large = market_cap_str[1] in market_cap
    medium = market_cap_str[2] in market_cap
    small = market_cap_str[3] in market_cap
    micro = market_cap_str[4] in market_cap
    nano = market_cap_str[5] in market_cap

    # Define query
    mega_q = Q(market_cap__gte=market_cap_value[0]) if mega else Q()
    large_q = Q(market_cap__range=[market_cap_value[1][0], market_cap_value[1][-1]]) if large else Q()
    medium_q = Q(market_cap__range=[market_cap_value[2][0], market_cap_value[2][-1]]) if medium else Q()
    small_q = Q(market_cap__range=[market_cap_value[3][0], market_cap_value[3][-1]]) if small else Q()
    micro_q = Q(market_cap__range=[market_cap_value[4][0], market_cap_value[4][-1]]) if micro else Q()
    nano_q = Q(market_cap__range=[market_cap_value[5][0], market_cap_value[5][-1]]) if nano else Q()

    # Query database
    results = Stock.objects.filter(
        (mega_q | large_q | medium_q | small_q | micro_q | nano_q),
        ipo_year__lte=dt.datetime.today().year - min_ipo_years,
        sector__in=sectors
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
    while backtest_from.year <= dt.datetime.now().year:
        for m in new_re_balancing_months:
            if backtest_from > dt.date.today():
                break
            re_balancing_dates.append(backtest_from.replace(month=m))
            if m == re_balancing_months[-1]:
                backtest_from = backtest_from.replace(year=backtest_from.year + 1)

    return re_balancing_dates


def get_result_from_method(method: str,
                           us_stocks: pd.DataFrame,
                           re_balancing_dates: list,
                           methods_financial: Type[FinancialReport],
                           methods_balance_sheet: Type[BalanceSheet],
                           methods_cash_flow: Type[CashFlow]) -> pd.DataFrame:
    # Extract the method names
    method_names = re.findall(r'\w+(?:\s+\w+)*', method)

    # Get the value of each method todo: to be continue...
    print()
    print("method_name: ", method_names)
    print()


def fetch_data_by_method(date: dt.date, us_stocks: pd.DataFrame, method: str,
                         report_table: Type[FinancialReport | BalanceSheet | CashFlow]) -> pd.DataFrame:
    # Initialize result in column
    col_name = f'{method}-{dt.datetime.strftime(date, "%b %y")}'
    us_stocks[col_name] = np.nan

    # Get report date. E.g. if date is 2021-02-01, then the report date is 2020-12-31 (2 months earlier)
    if date.month - 2 < 1:
        request_report_date = date.replace(year=date.year - 1, month=12 + (date.month - 2))
    else:
        request_report_date = date.replace(month=date.month - 2)

    # Set last day of month
    last_day = calendar.monthrange(request_report_date.year, request_report_date.month)[1]
    request_report_date = request_report_date.replace(day=last_day)

    # Get data for all stocks
    for ticker in us_stocks['Ticker']:
        # Get stock
        stock = Stock.objects.get(ticker=ticker)
        if not stock:
            continue

        # Get reoprt
        report = report_table.objects.filter(stock=stock, date=request_report_date)
        if not report:
            continue
        if len(report) > 1:
            logging.warning(f"Multiple reports for {ticker} on {request_report_date}! Please check.")
            continue
        report = report[0]

        # Get data by method
        if not getattr(report, method.replace(' ', '')):
            continue

        # Update value
        value = float(getattr(report, method.replace(' ', '')))
        if method not in ('Basic EPS', 'Diluted EPS'):
            value /= 1_000_000
        us_stocks.loc[us_stocks['Ticker'] == ticker, col_name] = round(value, 2)

    # Filter out zero and NaN
    us_stocks = us_stocks[
        (us_stocks[col_name] != 0) &
        (us_stocks[col_name].notna())
        ]

    return us_stocks


def fetch_percent_changed(df: pd.DataFrame, start_date: str, end_date: str) -> float | None:
    try:
        first_open = df.loc[start_date]['Open'].iloc[0]
        last_close = df.loc[end_date]['Adj Close'].iloc[-1]
    except KeyError:
        # Not enough data for start date, probably not listed yet
        return 0

    return round((last_close / first_open - 1) * 100, 2)


def extract_date_suffix(date_str: str) -> dt.datetime | None:
    date_pattern = re.compile(r'-(\w+ \d{2})$')
    match = date_pattern.search(date_str)
    return dt.datetime.strptime(match.group(1), '%b %y') if match else None
    # return pd.to_datetime(match.group(1), format='%b %y') if match else None


def reorder_dataframe_columns(df: pd.DataFrame, method: str) -> pd.DataFrame:
    """
    Reorder dataframe columns by date.
    :param df: Target dataframe.
    :param method: Method name to identify the target columns.
    :return: None
    """
    # Identify columns
    cols = [col for col in df.columns if col.startswith(f'{method}-')]

    # Sort columns
    cols.sort(key=extract_date_suffix)
    other_cols = [col for col in df.columns if col not in cols]
    df = df.reindex(columns=other_cols + cols)
    df.sort_values(by='Ticker', inplace=True)
    df.reset_index(inplace=True, drop=True)

    return df


def add_mean_row(df: pd.DataFrame) -> float:
    mean_performance = df['Performance'].mean().tolist()
    df.reset_index(inplace=True, drop=True)
    df.loc[len(df)] = ''
    total = 0
    for i, col in enumerate(df.columns):
        if col == 'Performance':
            mean = round(mean_performance.pop(0), 2)
            if np.isnan(mean):
                mean = 0
            df.iat[df.index[-1], i] = mean
            total += mean

    return total
