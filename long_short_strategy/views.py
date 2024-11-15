import calendar
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import datetime as dt
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from django.views import View
import logging
from multiprocessing import cpu_count
import numpy as np
import pandas as pd
import pytz
import re
from typing import Tuple
import yfinance as yf
from .models import Stock, FinancialReport, BalanceSheet, CashFlow, IncomeStatement, CandleStick

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
    # ipo_years = [5, 4, 3, 2, 1]
    # market_cap = dict()
    # for s, v in zip(market_cap_str, market_cap_value):
    #     market_cap[s] = v
    # methods = [
    #     'Basic EPS',
    # ]
    # sectors = ['Basic Materials', 'Technology', 'Industrials', 'Health Care', 'Energy', 'Consumer Discretionary',
    #            'Real Estate', 'Miscellaneous', 'Telecommunications', 'Consumer Staples', 'Utilities', 'Finance']
    # sectors.sort()
    # backtest_years = [1.5, 1]
    # pos_hold = [50, 40, 30, 20, 10]
    # re_balancing_months = [
    #     'Jan, Apr, Jul, Oct',
    #     'Feb, May, Aug, Nov',
    #     'Mar, Jun, Sep, Dec',
    # ]
    # html_context = {'market_cap': market_cap.keys(),
    #                 'ipo_years': ipo_years,
    #                 'methods': methods,
    #                 'sectors': sectors,
    #                 'backtest_years': backtest_years,
    #                 'pos_hold': pos_hold,
    #                 }
    # candle_stick_data = {}

    def __init__(self):
        super().__init__()
        self.ipo_years = [5, 4, 3, 2, 1]
        self.market_cap = dict()
        for s, v in zip(market_cap_str, market_cap_value):
            self.market_cap[s] = v
        self.methods = [
            'Basic EPS',
        ]
        self.sectors = ['Basic Materials', 'Technology', 'Industrials', 'Health Care', 'Energy',
                        'Consumer Discretionary',
                        'Real Estate', 'Miscellaneous', 'Telecommunications', 'Consumer Staples', 'Utilities',
                        'Finance']
        self.sectors.sort()
        self.backtest_years = [1.5, 1]
        self.pos_hold = [50, 40, 30, 20, 10]
        self.re_balancing_months = [
            'Jan, Apr, Jul, Oct',
            'Feb, May, Aug, Nov',
            'Mar, Jun, Sep, Dec',
        ]
        self.html_context = {'market_cap': self.market_cap.keys(),
                             'ipo_years': self.ipo_years,
                             'methods': self.methods,
                             'sectors': self.sectors,
                             'backtest_years': self.backtest_years,
                             'pos_hold': self.pos_hold,
                             }
        self.candle_stick_data = {}

    def get(self, request):
        self.html_context['selected_market_cap'] = list(self.market_cap.keys())[:3]
        self.html_context['selected_ipo_years'] = 1
        self.html_context['selected_sector'] = 'Energy'
        self.html_context['selected_method'] = 'EPS'
        self.html_context['selected_backtest_years'] = 1.5
        self.html_context['selected_pos_hold'] = 30

        return render(request, 'long_short/backtest.html', self.html_context)

    def post(self, request):
        # Get user's parameters
        market_cap = request.POST.getlist('market_cap')
        ipo_years = int(request.POST.get('ipo_years'))
        method = request.POST.get('method')
        sector = request.POST.get('sectors')
        backtest_years = float(request.POST.get('backtest_years'))
        pos_hold = int(request.POST.get('pos_hold'))

        # Add to context
        self.html_context['selected_market_cap'] = market_cap
        self.html_context['selected_ipo_years'] = ipo_years
        self.html_context['selected_method'] = method
        self.html_context['selected_sectors'] = sector
        self.html_context['selected_backtest_years'] = backtest_years
        self.html_context['selected_pos_hold'] = pos_hold

        # Check input validity
        if not market_cap:
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
        merged_results = us_stocks.copy()
        for date in re_balancing_dates:
            # Add result columns to us_stocks dataframe
            result = fetch_data_by_method(date, us_stocks.copy(), method)
            result = result[['Ticker', result.columns[-1]]]
            merged_results = pd.merge(merged_results, result, on='Ticker', how='left')

        # Ranking and split dataframe by result columns
        result_subset = {}
        result_cols = [col for col in merged_results.columns if col.startswith(f'{method}-')]
        for col in result_cols:
            result_subset[col] = merged_results[['Ticker', col]].sort_values(by=col, ascending=False)
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


        # Set up multiprocessing for fetching data
        num_cpus = min(cpu_count(), len(re_balancing_dates))

        with ProcessPoolExecutor(max_workers=num_cpus) as outer_executor:
            futures = [
                outer_executor.submit(fetch_data_by_method, date, us_stocks.copy(), method)
                for date in re_balancing_dates
            ]
            # Get result
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # Combined_results
        merged_results = us_stocks.copy()

        for result in results:
            result = result[['Ticker', result.columns[-1]]]
            merged_results = pd.merge(merged_results,
                                      result[
                                          ['Ticker', result.columns[-1]]
                                      ],
                                      on='Ticker',
                                      how='left')

        # Re-order dataframe columns by re-balancing date
        merged_results = reorder_dataframe_columns(merged_results, method)

        # Ranking and split dataframe by result columns
        result_subset = {}
        result_cols = [col for col in merged_results.columns if col.startswith(f'{method}-')]
        for col in result_cols:
            result_subset[col] = merged_results[['Ticker', col]].sort_values(by=col, ascending=False)
            result_subset[col].dropna(inplace=True, subset=[col])

        # Get performance for every re-balancing date
        from_months = list(result_subset.keys())
        to_months = list(result_subset.keys())[1:] + [
            f'{method}-{dt.date.strftime(dt.date.today(), "%b %y")}'
        ]

        for from_month, to_month in zip(from_months, to_months):
            # Initialize performance column
            result_subset[from_month]['Performance'] = np.nan

            # Formatting for start_date and end_date
            start_date = dt.datetime.strftime(extract_date_suffix(from_month), '%Y-%m-%d')
            end_date = dt.datetime.strftime(extract_date_suffix(to_month), '%Y-%m-%d')
            if start_date == end_date:
                end_date = dt.datetime.strftime(dt.date.today(), '%Y-%m-%d')

            # Get top and bottom stocks
            if len(result_subset[from_month]) < pos_hold * 2:
                # logging.warning(f"Not enough stocks for {from_month}-{to_month}, please adjust your filter!")
                # return render(request, 'long_short/backtest.html', html_context)
                pass

            half_rows_num = min(pos_hold, len(result_subset[from_month]) // 2)
            df = pd.concat(
                [result_subset[from_month].head(half_rows_num), result_subset[from_month].tail(half_rows_num)])

            # Get performance changed for symbols
            for i, row in df.iterrows():
                if not isinstance(self.candle_stick_data.get(row['Ticker']), pd.DataFrame):
                    download_start_date = dt.date.today() - dt.timedelta(days=365 * max(self.backtest_years) + 30)
                    data = yf.download(row['Ticker'], download_start_date)
                    data.loc[pd.to_datetime(dt.datetime.today(), utc=True)] = np.nan
                    data = data.resample('D').last().ffill()
                    self.candle_stick_data[row['Ticker']] = data

                df.at[i, 'Performance'] = fetch_percent_changed(self.candle_stick_data.get(row['Ticker']), start_date,
                                                                end_date)

            result_subset[from_month] = df

        # Re-name columns to: 'from start_date to end_date'
        for from_month, to_month in zip(from_months, to_months):
            if isinstance(to_month, str):
                to_str = f'{from_month.replace(method + "-", "")} to {to_month.replace(method + "-", "")}'
            else:
                to_str = f'{from_month.replace(method + "-", "")} to {dt.date.strftime(to_month, "%Y-%m-%d")}'
            result_subset[from_month].rename(columns={from_month: to_str, }, inplace=True)

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


def fetch_earning_per_share(symbol: str, request_date: dt.date) -> float | None:
    stock = Stock.objects.get(ticker=symbol)
    if not stock:
        return 0.0

    try:
        report = FinancialReport.objects.get(stock=stock, date=request_date)
    except Exception as e:
        return 0.0

    return report.BasicEPS if report.BasicEPS else 0.0


def fetch_ebit_over_assets(symbol: str, request_date: dt.date) -> float | None:
    stock = Stock.objects.get(ticker=symbol)
    financials = FinancialReport.objects.get(stock=stock, date=request_date)
    balance_sheets = BalanceSheet.objects.get(stock=stock, date=request_date)
    ebit = financials.EBIT
    total_assets = balance_sheets.TotalAssets

    return round(ebit / total_assets, 2) if ebit and total_assets else 0

    financial = getattr(financials, dt.datetime.strftime(request_date, '%b%y'))
    balance_sheet = getattr(balance_sheets, dt.datetime.strftime(request_date, '%b%y'))
    if financial and balance_sheet:
        ebit = financial.get('EBIT', 0)
        total_assets = balance_sheet.get('Total Assets', 0)
        return round(ebit / total_assets, 2) if ebit and total_assets else 0
    else:
        return 0


def fetch_operating_cash_flow(symbol: str, request_date: dt.date) -> float | None:
    stock = Stock.objects.get(symbol=symbol)
    reports = CashFlow.objects.get(symbol=stock)
    report = getattr(reports, dt.datetime.strftime(request_date, '%b%y'))
    if report:
        op_cash_flow = report.get('Operating Cash Flow', 0)
        return round(op_cash_flow / 1_000_000, 1) if op_cash_flow else 0
    else:
        return 0


def fetch_investing_cash_flow(symbol: str, request_date: dt.date) -> float | None:
    stock = Stock.objects.get(symbol=symbol)
    reports = CashFlow.objects.get(symbol=stock)
    report = getattr(reports, dt.datetime.strftime(request_date, '%b%y'))
    if report:
        i_cash_flow = report.get('Investing Cash Flow', 0)
        return round(i_cash_flow / 1_000_000, 1) if i_cash_flow else 0
    else:
        return 0


def fetch_financing_cash_flow(symbol: str, request_date: dt.date) -> float | None:
    stock = Stock.objects.get(symbol=symbol)
    reports = CashFlow.objects.get(symbol=stock)
    report = getattr(reports, dt.datetime.strftime(request_date, '%b%y'))
    if report:
        f_cash_flow = report.get('Financing Cash Flow', 0)
        return round(f_cash_flow / 1_000_000, 1) if f_cash_flow else 0
    else:
        return 0


def fetch_free_cash_flow(symbol: str, request_date: dt.date) -> float | None:
    stock = Stock.objects.get(symbol=symbol)
    reports = CashFlow.objects.get(symbol=stock)
    report = getattr(reports, dt.datetime.strftime(request_date, '%b%y'))
    if report:
        free_cash_flow = report.get('Free Cash Flow', 0)
        return round(free_cash_flow / 1_000_000, 1) if free_cash_flow else 0
    else:
        return 0


def fetch_assets_over_liabilities(symbol: str, request_date: dt.date) -> float | None:
    stock = Stock.objects.get(symbol=symbol)
    reports = BalanceSheet.objects.get(symbol=stock)
    report = getattr(reports, dt.datetime.strftime(request_date, '%b%y'))
    if report:
        assets = report.get('Total Assets', 0)
        lia = report.get('Total Liabilities Net Minority Interest', 0)
        if assets and lia:
            return round(assets / lia, 2)
        return 0
    else:
        return 0


def fetch_repurchase_of_capital(symbol: str, request_date: dt.date) -> float | None:
    stock = Stock.objects.get(symbol=symbol)
    reports = CashFlow.objects.get(symbol=stock)
    report = getattr(reports, dt.datetime.strftime(request_date, '%b%y'))
    if report:
        re_purchase = report.get('Repurchase Of Capital Stock', 0)
        return round(re_purchase / 1_000_000, 1) if re_purchase else 0
    else:
        return 0


def fetch_data_by_method(date: dt.date, us_stocks: pd.DataFrame, method: str) -> pd.DataFrame:
    """
    Get data for stocks by method.
    :param date: Re-balancing date.
    :param us_stocks: Stocks info dataframe.
    :param method: Method of ranking. E.g.(Earning per share, Ebit/assets...)
    :return: Result
    """
    # Initialize result in column
    col_name = f'{method}-{dt.datetime.strftime(date, "%b %y")}'
    us_stocks[col_name] = np.nan

    # Get report date. E.g. if date is 2021-02-01, then the report date is 2020-12-31
    if date.month - 2 < 1:
        request_report_date = date.replace(year=date.year - 1, month=12 + (date.month - 2))
    else:
        request_report_date = date.replace(month=date.month - 2)

    # Set last day of month
    last_day = calendar.monthrange(request_report_date.year, request_report_date.month)[1]
    request_report_date = request_report_date.replace(day=last_day)

    for ticker in us_stocks['Ticker']:
        # Get stock
        stock = Stock.objects.get(ticker=ticker)
        if not stock:
            continue

        # Get reoprt
        report = FinancialReport.objects.filter(stock=stock, date=request_report_date)
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
        us_stocks.loc[us_stocks['Ticker'] == ticker, col_name] = float(getattr(report, method.replace(' ', '')))

    # Filter out zero and NaN
    us_stocks = us_stocks[
        (us_stocks[col_name] != 0) &
        (us_stocks[col_name].notna())
        ]

    return us_stocks

    # Select ranking method
    with ThreadPoolExecutor(max_workers=10) as executor:
        if method == 'EPS':
            func = fetch_earning_per_share
        elif method == 'EBIT/Assets':
            func = fetch_ebit_over_assets
        elif method == 'Operating Cash Flow (M)':
            func = fetch_operating_cash_flow
        elif method == 'Investing Cash Flow (M)':
            func = fetch_investing_cash_flow
        elif method == 'Financing Cash Flow (M)':
            func = fetch_financing_cash_flow
        elif method == 'Free Cash Flow (M)':
            func = fetch_free_cash_flow
        elif method == 'Assets/Liabilities':
            func = fetch_assets_over_liabilities
        elif method == 'Repurchase of Capital Stock (M)':
            func = fetch_repurchase_of_capital
        else:
            raise ValueError(f'Invalid method: {method}')

        # Setup executor
        future_data = {
            executor.submit(func, symbol, request_date=request_report_date):
                symbol for symbol in us_stocks['Ticker']
        }

        # Get result
        for future in as_completed(future_data):
            symbol = future_data[future]
            if future.exception():
                logging.warning("Future's exception: ", future.exception())
            else:
                us_stocks.loc[us_stocks['Ticker'] == symbol, col_name] = float(future.result())

    # Filter out zero and NaN
    us_stocks_filtered = us_stocks[
        (us_stocks[col_name] != 0) &
        (us_stocks[col_name].notna())
        ]

    return us_stocks_filtered


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
