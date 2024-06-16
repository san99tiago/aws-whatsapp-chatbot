import aws_cdk as cdk


def add_tags_to_app(
    app: cdk.App, main_resources_name: str, deployment_environment: str
) -> None:
    """
    Function to add custom tags to app in a centralized fashion.

    :param app: (aws_cdk.App) to apply tags to.
    :param main_resources_name: (str) the main solution name being deployed.
    :param deployment_environment: (str) value of the tag "environment".
    """

    app_tags = cdk.Tags.of(app)
    app_tags.add("MainResourcesName", main_resources_name)
    app_tags.add("Environment", deployment_environment)

    # Add tags from CDK context
    context_tags = app.node.try_get_context("tags")
    for key in context_tags:
        app_tags.add(key, context_tags[key])
