## Install psycopg2 to connect to the postgres database
> pip install psycopg2-binary

## Maintain the database, keep the financial data up to date
- Run 'python manage.py update_db --update_candlesticks' after us stock trading hour everyday
- Run 'python manage.py update_db --update_reports' after us stocks trading hour on 1st of every month
