## To initialize the database
- Go to https://www.nasdaq.com/market-activity/stocks/screener to download the stocks list csv
- Save the csv file to static/stock_list folder
- Run command in terminal
> python manage.py init_db

## To maintain the database, keep the financial data up to date
- Add columns to the models: FinancialReport, BalanceSheet, CashFlow, IncomeStatement (monthly)
- Run the above command 'python manage.py init_db' ( monthly)
# InvestmentWeb
