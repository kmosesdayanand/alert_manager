import os
import logging
from logging.config import fileConfig
import configparser
_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
_BIN_DIR = os.path.dirname(_LIB_DIR)
_APP_DIR = os.path.dirname(_BIN_DIR)

def setupLogger(logger='alert_manager'):

	# logger
	fileName = 'alert_manager.log'
	if logger != 'alert_manager':
		fileName = 'alert_manager_%s.log' % logger
		logger = 'alert_manager_%s' % logger

	# Get loglevel from config file
	local = os.path.join(_APP_DIR, "local", "alert_manager.conf")
	default = os.path.join(_APP_DIR, "default", "alert_manager.conf")

	config = configparser.ConfigParser()

	try:
		config.read(local)
		rootLevel = config.get('logging', 'rootLevel')
	except:
		config.read(default)
		rootLevel = config.get('logging', 'rootLevel')

	try:
		logLevel = config.get('logging', 'logger.{}'.format(logger))
	except:
		logLevel = rootLevel

	# Setup logger
	log = logging.getLogger(logger)
	lf = os.path.join(os.environ.get('SPLUNK_HOME'), "var", "log", "splunk", fileName)
	fh = logging.handlers.RotatingFileHandler(lf, maxBytes=25000000, backupCount=5)
	formatter = logging.Formatter('%(asctime)s %(levelname)-6s pid="%(process)s" logger="%(name)s" message="%(message)s" (%(filename)s:%(lineno)s)', datefmt="%Y-%m-%d %H:%M:%S %Z")
	fh.setFormatter(formatter)
	log.addHandler(fh)
	level = logging.getLevelName(logLevel)
	log.setLevel(level)

	return log
