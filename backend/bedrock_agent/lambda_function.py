# NOTE: This is a super-MVP code for testing. Still has a lot of gaps to solve/fix. Do not use in prod.

from bedrock_agent.fetch_calendar_events import get_all_calendar_events


def lambda_handler(event, context):
    action_group = event["actionGroup"]
    _function = event["function"]
    parameters = event.get("parameters", [])

    print("PARAMETERS ARE: ", parameters)

    # Extract date from parameters
    date = None
    event_name = None
    for param in parameters:
        if param["name"] == "date":
            date = param["value"]

    all_events_for_user = get_all_calendar_events(
        partition_key="USER#san99tiago@gmail.com",  # TODO: Extract user from input when multi-user support
        sort_key_portion=f"DATE#{date}",
    )
    print("DEBUG, ", all_events_for_user)

    # TODO: Add a more robust search engine/algorithm for matching/finding events
    result_events = []
    for calendar_event in all_events_for_user:
        if calendar_event.get("events"):
            result_events.extend(calendar_event["events"])

    print(f"Events found: {result_events}")

    # Convert the list of events to a string to be able to return it in the response as a string
    result_events_string = "\n-".join(result_events)
    response_body = {"TEXT": {"body": result_events_string}}

    action_response = {
        "actionGroup": action_group,
        "function": _function,
        "functionResponse": {"responseBody": str(response_body)},
    }

    function_response = {
        "response": action_response,
        "messageVersion": event["messageVersion"],
    }
    print("Response: {}".format(function_response))

    return function_response
