
import logging
import colorlog
from colorlog.escape_codes import escape_codes


class CustomFormatter(logging.Formatter):
    # def __init__(self, *args, **kwargs):
    #     self.class_color_map = {
    #         "EvalClient": "red",  # Custom color for ExampleClass
    #         "GameEngine": "blue",  # Custom color for AnotherClass
    #         "RelayServer": "yellow",

    #     }
    #     super().__init__(*args, **kwargs)

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
            "EvalClient": self.blue,  # Custom color for ExampleClass
            "GameEngine": self.red,  # Custom color for AnotherClass
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
        return f"\n----------------------------------\n\n{formatter.format(record)}\n\n----------------------------------\n"

    # def format(self, record):
    #     # Get the class name from the logger name (this assumes the logger's name is the class name)
    #     class_name = record.name.split(".")[-1]
    #     print(class_name)
    #     # Set default color to white if class name is not in the map
    #     color = self.class_color_map.get(class_name, "white")
    #     print(color)
    #     #print(record.log_color)

    #     # Set the log color based on class name
    #     record.log_color = color
        
    #     log_msg = super().format(record)
    #     print(log_msg)
    #     return f"\n-----------------\n{log_msg}\n-----------------\n"


class CustomLogger:
    def __init__(self, logger_name, custom_color="white"):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        fmt = '%(name)s | %(module)s.%(funcName)s:%(lineno)s \n\n%(message)s'

        # Create a handler for the console (stdout)
        handler = logging.StreamHandler()
        handler.setFormatter(CustomFormatter(fmt))

        # # Custom color formatter that changes color based on the class name
        # formatter = ClassColorFormatter(
        #     "{log_color} {asctime} - {name} - {levelname} - [{module}.{funcName}:{lineno}] - {message}{reset}",
        #     datefmt="%Y-%m-%d %H:%M:%S",
        #     style="{",
        # )


        # handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def get_logger(self):
        return self.logger