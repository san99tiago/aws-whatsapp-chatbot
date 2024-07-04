# External imports
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

# Own imports
from state_machine.__init__ import *  # noqa NOSONAR


logger = Logger(
    service="wpp-chatbot-sm-general",
    log_uncaught_exceptions=True,
    owner="Santiago Garcia Arango",
)


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: dict, context: LambdaContext):
    main_event = {}
    try:
        # Gather custom class and method handlers from input event
        class_name = event.get("params", None).get("class_name")
        method_name = event.get("params", None).get("method_name")
        main_event = event.get("event", {})
        main_event["ExceptionOcurred"] = False
        logger.info("Lambda Main Handler Event")
        logger.info(main_event)

        if class_name is not None and method_name is not None:
            # Dynamically load and initialize the target class at runtime
            target_class = globals()[class_name]
            target_instance = target_class(main_event)
            logger.debug(f"dynamically loaded target_instance: {target_instance}")

            # Dynamically load and execute the method at runtime
            target_method = getattr(target_instance, method_name)
            logger.debug(f"dynamically loaded target_method: {target_method}")
            return target_method()
        else:
            message = "class_name and method_name are not provided in event params"
            logger.info(message)
            return {"Message": message}
    except Exception as e:
        logger.exception(f"Error while executing lambda handler: {e}")
        logger.exception(f"Lambda Initial Event was: {event}")
        logger.exception(f"Lambda Main Event was: {main_event}")
        raise e
