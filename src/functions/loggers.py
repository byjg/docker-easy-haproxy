import logging

from .functions import Functions

logger_init = logging.getLogger(Functions.INIT_LOG)
logger_haproxy = logging.getLogger(Functions.HAPROXY_LOG)
logger_easyhaproxy = logging.getLogger(Functions.EASYHAPROXY_LOG)
logger_certbot = logging.getLogger(Functions.CERTBOT_LOG)

Functions.setup_log(logger_init)
Functions.setup_log(logger_haproxy)
Functions.setup_log(logger_easyhaproxy)
Functions.setup_log(logger_certbot)