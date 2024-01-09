

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
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'formatter': 'default',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'filename': '/var/log/stratux_companion.log',
            'maxBytes': 1024 * 1024,  # 1 mb
            'backupCount': 0
        },
    },
    'loggers': {
        'stratux_companion': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'ERROR'
    },
}
