
import logging
import colorlog
from colorlog.escape_codes import escape_codes


class CustomFormatter(logging.Formatter):

    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'
    
    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.class_color_map = {
            "EvalClient": self.blue,
            "GameEngine": self.red,
            "RelayServer": self.yellow,
            "MqttClient": self.grey

        }
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }
        
    def format(self, record):
        class_name = record.name.split(".")[-1]
        color = self.class_color_map.get(class_name)
        log_fmt = color + self.fmt + self.reset
        formatter = logging.Formatter(log_fmt)
        # return f"\n----------------------------------\n\n{formatter.format(record)}\n\n----------------------------------\n"
        return formatter.format(record)

class CustomLogger:
    def __init__(self, logger_name, custom_color="white"):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        fmt = '\n----------------------------------\n\n%(name)s | %(module)s.%(funcName)s:%(lineno)s \n\n%(message)s\n\n----------------------------------\n'

        handler = logging.StreamHandler()
        file_handler = logging.FileHandler("ext_comm.log")
        handler.setFormatter(CustomFormatter(fmt))
        file_handler.setFormatter(logging.Formatter(fmt))
        
        self.logger.addHandler(handler)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger