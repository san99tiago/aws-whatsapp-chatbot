# NOTE: This is a super-MVP code for testing. Still has a lot of gaps to solve/fix. Do not use in prod.
# TODO: Refactor solution to a standalone router for all Action Groups

from bedrock_agent.dynamodb_helper import query_dynamodb_pk_sk


def action_group_fetch_calendar_events(parameters):
    # Extract date from parameters
    date = None
    for param in parameters:
        if param["name"] == "date":
            date = param["value"]

    all_events_for_user = query_dynamodb_pk_sk(
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
    return result_events


def action_group_fetch_todos():
    all_todos_for_user = query_dynamodb_pk_sk(
        partition_key="USER#san99tiago@gmail.com",  # TODO: Extract user from input when multi-user support
        sort_key_portion="TODO#",
    )
    print("DEBUG, ", all_todos_for_user)

    # TODO: Add a more robust search engine/algorithm for matching/finding events
    result_todos = []
    for todo in all_todos_for_user:
        if todo.get("todo_details"):
            result_todos.append(todo["todo_details"])

    print(f"TODOs found: {result_todos}")
    return result_todos


def action_group_fetch_contacts():
    all_contacts_for_user = query_dynamodb_pk_sk(
        partition_key="USER#san99tiago@gmail.com",  # TODO: Extract user from input when multi-user support
        sort_key_portion="CONTACT#",
    )
    print("DEBUG, ", all_contacts_for_user)

    # TODO: Add a more robust search engine/algorithm for matching/finding events
    result_contacts = []
    for contact in all_contacts_for_user:
        if contact.get("contact_details"):
            result_contacts.append(contact["contact_details"])

    print(f"Contacts found: {result_contacts}")
    return result_contacts


def lambda_handler(event, context):
    action_group = event["actionGroup"]
    _function = event["function"]
    parameters = event.get("parameters", [])

    print("PARAMETERS ARE: ", parameters)
    print("ACTION GROUP IS: ", action_group)

    # TODO: enhance this If-Statement approach to a dynamic one...
    if action_group == "FetchCalendarEvents":
        results = action_group_fetch_calendar_events(parameters)
    elif action_group == "FetchTODOs":
        results = action_group_fetch_todos()
    elif action_group == "FetchContacts":
        results = action_group_fetch_contacts()
    else:
        raise ValueError(f"Action Group <{action_group}> not supported.")

    # Convert the list of events to a string to be able to return it in the response as a string
    results_string = "\n-".join(results)
    response_body = {"TEXT": {"body": results_string}}

    action_response = {
        "actionGroup": action_group,
        "function": _function,
        "functionResponse": {"responseBody": response_body},
    }

    function_response = {
        "response": action_response,
        "messageVersion": event["messageVersion"],
    }
    print("Response: {}".format(function_response))

    return function_response
