import webbrowser
from common.make_log import setup_logger

logger = setup_logger(__name__)

def open_web(URL):
    webbrowser.open(URL)