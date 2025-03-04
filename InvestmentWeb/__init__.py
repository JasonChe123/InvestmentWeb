from dotenv import load_dotenv
import logging


load_dotenv(override=True)

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='<< %(levelname)-9s>> %(asctime)s [ %(filename)-10s ] Line:%(lineno)-4d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
