from dotenv import load_dotenv
import logging

# get finnhub api key
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='<< %(levelname)-9s>> %(asctime)s [ %(filename)-10s ] Line:%(lineno)-4d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)