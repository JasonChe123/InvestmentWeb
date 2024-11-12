# from django.shortcuts import render
# from django.views import View
# from dotenv import load_dotenv
# import finnhub
# import json
# import os
# import pandas as pd
# import requests
# import yfinance as yf
#
#
# # get finnhub api key
# load_dotenv()
#
#
# class DashboardView(View):
#     def get(self, request):
#         return render(request, 'long_short/index.html')
#
#
# class BackTestView(View):
#     def get(self, request):
#         context = {}
#
#         # get us stocks
#         us_stocks = get_us_stocks()
#         us_stocks = us_stocks
#
#         # get ebit/total_assets
#         us_stocks['ebit/total_assets'] = us_stocks['Symbol'].apply(fetch_ebit_over_assets)
#
#         # sort data by ebit/assets
#         us_stocks.sort_values(by='ebit/total_assets', ascending=False, inplace=True)
#
#         print(us_stocks.head(10)[['Symbol', 'ebit/total_assets']])
#         print()
#         print(us_stocks.tail(10)[['Symbol', 'ebit/total_assets']])
#
#         return render(request, 'long_short/backtest.html', context)
#
#
# def fetch_ebit_over_assets(symbol: str) -> float:
#     try:
#         # fetch financial data
#         stock = yf.Ticker(symbol)
#         financials = stock.financials
#         balance_sheet = stock.balance_sheet
#
#         # get latest ebit and total assets
#         ebit = financials.at['EBIT', financials.columns[0]]
#         total_assets = balance_sheet.at['Total Assets', balance_sheet.columns[0]]
#
#         return ebit/total_assets
#
#     except Exception as e:
#         print(f"Failed to fetch data for {symbol}: {e}")
#
#     return 0
#
#
# def get_us_stocks() -> pd.DataFrame:
#     # read csv file
#     stock_list_folder = os.path.join(os.path.dirname(__file__), '..', 'static', 'stock_list')
#     stock_list_files = os.listdir(stock_list_folder)
#     data = pd.DataFrame()
#     for f in stock_list_files:
#         data = pd.concat([data, pd.read_csv(os.path.join(stock_list_folder, f))])
#
#     data.reset_index(inplace=True, drop=True)
#     return data
