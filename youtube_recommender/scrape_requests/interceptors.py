import logging

from grpc_interceptor import ServerInterceptor

logger = logging.getLogger(__name__)


class ErrorLogger(ServerInterceptor):
    def intercept(self, method, request, context, method_name):
        try:
            return method(request, context)
        except Exception as e:
            self.log_error(e)
            raise

    def log_error(self, e: Exception) -> None:
        logger.error(f"{e=!r}")
        # todo: send log to Kibana, Sentry, ..
