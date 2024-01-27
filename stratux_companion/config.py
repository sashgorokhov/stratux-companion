from pathlib import Path

ROOT_DIR: Path = Path(__file__).parent.parent
SETTINGS_FILE = ROOT_DIR / 'settings.json'


LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'short': {
            'format': '%(levelname)s: %(message)s',
        },
        'jsonl': {
            'format': '%(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'formatter': 'short',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'default',
            'filename': ROOT_DIR / 'stratux_companion.log',
            'backupCount': 5
        },
        'traffic': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'jsonl',
            'filename': ROOT_DIR / 'traffic.jsonl',
            'when': 'midnight',
            'backupCount': 5
        },
        'errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'default',
            'filename': ROOT_DIR / 'stratux_companion.errors.log',
            'when': 'midnight',
            'backupCount': 2
        },
    },
    'loggers': {
        'stratux_companion': {
            'handlers': ['errors', 'file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'stratux_companion.traffic': {
            'handlers': ['traffic'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'ERROR'
    },
}
