import os
import re
import subprocess
from sys import stdout
from typing import Any

import simplejson as json
from argh import CommandError, arg, dispatch_command, wrap_errors
from deepmerge import always_merger
from gql import Client as GqlClient
from gql import gql
from gql.transport.requests import RequestsHTTPTransport
from pycognito.utils import RequestsSrpAuth

from .data_sources import factory as data_source_factory
from .objects import (
    APPS,
    KMS_KEYS,
    MANAGED_NODE_TYPES,
    MESSAGE_TYPES,
    NODES,
    TerraformObject,
    encode_terraform,
)
from .resources import factory as resource_factory, Resource

DEFAULT_APPSYNC_ENDPOINT = "https://api-prod.us-east-1.echo.stream/graphql"


def main():
    dispatch_command(terrafy)


"""
@wrap_errors(
    errors=[Exception], processor=lambda exc_info: f"\033[91m{exc_info}\033[00m"
)
"""


@arg(
    "--appsync-endpoint",
    help=f"The ApiUser's AppSync Endpoint. Defaults to {DEFAULT_APPSYNC_ENDPOINT}. Environment variable - ECHOSTREAM_APPSYNC_ENDPOINT",
)
@arg(
    "--client-id",
    help="The ApiUser's AWS Cognito Client Id. Environment variable - ECHOSTREAM_CLIENT_ID",
)
@arg(
    "--password",
    help="The ApiUser's password. Environment variable - ECHOSTREAM_PASSWORD",
)
@arg(
    "--tenant",
    help="The EchoStream Tenant to terrafy. Environment variable - ECHOSTREAM_TENANT",
)
@arg(
    "--terraform",
    help="The path to the Terraform executable.",
)
@arg(
    "--user-pool-id",
    help="The ApiUser's AWS Cognito User Pool Id. Environment variable - ECHOSTREAM_USER_POOL_ID",
)
@arg(
    "--username",
    help="The ApiUser's username. Environment variable - ECHOSTREAM_USERNAME",
)
def terrafy(
    appsync_endpoint: str = None,
    client_id: str = None,
    password: str = None,
    tenant: str = None,
    terraform: str = "terraform",
    user_pool_id: str = None,
    username: str = None,
) -> None:
    """Introspects the provided EchoStream Tenant and create a Terraform module and statefile using the created module.

    All file creation is done in the current directory.

    Requires Terraform (>= 1.3.5) to be installed and available in the PATH."""
    appsync_endpoint = (
        appsync_endpoint
        or os.environ.get("ECHOSTREAM_APPSYNC_ENDPOINT")
        or DEFAULT_APPSYNC_ENDPOINT
    )
    if not (client_id := client_id or os.environ.get("ECHOSTREAM_CLIENT_ID")):
        raise CommandError(
            "You must either provide --client_id or ECHOSTREAM_CLIENT_ID"
        )
    if not (password := password or os.environ.get("ECHOSTREAM_PASSWORD")):
        raise CommandError("You must provide either --password or ECHOSTREAM_PASSWORD")
    if not (tenant := tenant or os.environ.get("ECHOSTREAM_TENANT")):
        raise CommandError("You must provide either --tenant or ECHOSTREAM_TENANT")
    if not (user_pool_id := user_pool_id or os.environ.get("ECHOSTREAM_USER_POOL_ID")):
        raise CommandError(
            "You must provide either --user-pool-id or ECHOSTREAM_USER_POOL_ID"
        )
    if not (username := username or os.environ.get("ECHOSTREAM_USERNAME")):
        raise CommandError("You must provide either --username or ECHOSTREAM_USERNAME")

    version_check = subprocess.run([terraform, "--version"], capture_output=True)
    if version_check.returncode != 0:
        raise RuntimeError(version_check.stderr.decode())
    if not (
        (
            m := re.match(
                r"^Terraform v([0-9]\.[0-9]\.[0-9]).*$",
                version_check.stdout.decode().split("\n")[0],
            )
        )
        and m.group(1) >= "1.3.5"
    ):
        raise RuntimeError(
            f"{terraform} does not point to a Terraform executable"
            if not m
            else f"Terraform version must be >= 1.3.5, found {m.group(1)}"
        )

    __print_cyan(f"Logging user {username} in to Tenant {tenant}")
    gql_client = GqlClient(
        fetch_schema_from_transport=True,
        transport=RequestsHTTPTransport(
            auth=RequestsSrpAuth(
                client_id=client_id,
                http_header_prefix="",
                password=password,
                user_pool_id=user_pool_id,
                username=username,
            ),
            url=appsync_endpoint,
        ),
    )
    __print_green("Login successful!")

    __print_cyan(f"Terrafying EchoStream Tenant {tenant}")

    terraform_objects: list[TerraformObject] = list()
    for getter in (
        __process_main,
        __process_tenant_and_tenant_users,
        __process_api_users,
        __process_message_types,
        __process_functions,
        __process_managed_node_types,
        __process_kms_keys,
        __process_apps,
        __process_nodes_and_edges,
    ):
        stdout.write("\033[93m.\033[00m")
        stdout.flush()
        terraform_objects.extend(getter(gql_client, tenant))
    stdout.write("\n")

    __print_cyan("Initializing terraform")
    subprocess.run([terraform, "init"], capture_output=True, check=True)
    __print_green("Terraform initialized!")

    if os.path.exists("terraform.tfstate"):
        __print_yellow("WARNING: terraform.tfstate already exists, clearing all outputs and resources!")
        with open("terraform.tfstate", "rt") as f:
            tfstate = json.load(f)
        tfstate["outputs"] = {}
        tfstate["resources"] = []
        with open("terraform.tfstate", "wt") as f:
            json.dump(tfstate, f, indent=2)

    __print_cyan("Importing EchoStream resources")
    env = dict(
        os.environ,
        ECHOSTREAM_APPSYNC_ENDPOINT=appsync_endpoint,
        ECHOSTREAM_CLIENT_ID=client_id,
        ECHOSTREAM_PASSWORD=password,
        ECHOSTREAM_TENANT=tenant,
        ECHOSTREAM_USERNAME=username,
        ECHOSTREAM_USER_POOL_ID=user_pool_id,
    )
    for obj in terraform_objects:
        if isinstance(obj, Resource):
            try:
                subprocess.run(
                    [terraform, "import", obj.address, obj.identity],
                    capture_output=True,
                    check=True,
                    env=env,
                )
            except subprocess.CalledProcessError as cpe:
                raise Exception(
                    f"Error importing {obj.address}\n{cpe.stdout}\n{cpe.stderr}"
                )
            stdout.write("\033[93m.\033[00m")
            stdout.flush()
    stdout.write("\n")
    __print_green("EchoStream resources imported!")
    os.remove("terraform.tfstate.backup")
    __print_cyan("Confirming that infrastructure matches configuration")
    plan_check = subprocess.run([terraform, "plan"], capture_output=True, check=True)
    if not re.search(r"No changes.", plan_check.stdout.decode(), flags=re.MULTILINE):
        __print_yellow(
            f"WARNING: Tenant {tenant} infrastructure does not match the configuration. Plan output below:"
        )
        stdout.write("\n")
        print(plan_check.stdout.decode())

    __print_green(f"EchoStream Tenant {tenant} Terrafy'd!!!")


def __print_cyan(value: str) -> None:
    print(f"\033[96m{value}\033[00m")


def __print_green(value: str) -> None:
    print(f"\033[92m{value}\033[00m")


def __print_yellow(value: str) -> None:
    print(f"\033[93m{value}\033[00m")


def __process_api_users(gql_client: GqlClient, tenant: str) -> list[TerraformObject]:
    query = gql(
        """
        query listApiUsers($tenant: String!, $exclusiveStartKey: AWSJSON) {
            ListApiUsers(tenant: $tenant, exclusiveStartKey: $exclusiveStartKey) {
                echos {
                    __typename
                    description
                    role
                    username
                }
                lastEvaluatedKey
            }
        }
        """
    )

    def list_api_users(exclusive_start_key: Any = None) -> list[TerraformObject]:
        with gql_client as session:
            result = session.execute(
                query,
                variable_values=dict(
                    tenant=tenant, exclusiveStartKey=exclusive_start_key
                ),
            )["ListApiUsers"]
        objs = [resource_factory(data) for data in result["echos"]]
        return (
            objs + list_api_users(exclusive_start_key)
            if (exclusive_start_key := result.get("lastEvaluatedKey"))
            else objs
        )

    api_users = list_api_users()
    api_users_json = dict()
    for api_user in api_users:
        api_users_json = always_merger.merge(api_users_json, api_user.encode())
    with open("api-users.tf.json", "wt") as tf_json:
        json.dump(default=encode_terraform, fp=tf_json, indent=2, obj=api_users_json)
    return api_users


def __process_apps(gql_client: GqlClient, tenant: str) -> list[TerraformObject]:
    query = gql(
        """
        query listApps($tenant: String!, $exclusiveStartKey: AWSJSON) {
            ListApps(tenant: $tenant, exclusiveStartKey: $exclusiveStartKey) {
                echos {
                    __typename
                    description
                    name
                    ... on CrossAccountApp {
                        account
                        config
                        tableAccess
                    }
                    ... on CrossTenantReceivingApp {
                        sendingTenant
                    }
                    ... on CrossTenantSendingApp {
                        receivingApp
                        receivingTenant
                    }
                    ... on ExternalApp {
                        config
                        tableAccess
                    }
                    ... on ManagedApp {
                        config
                        tableAccess
                    }
                }
                lastEvaluatedKey
            }
        }
        """
    )

    def list_apps(exclusive_start_key: Any = None) -> list[TerraformObject]:
        with gql_client as session:
            result = session.execute(
                query,
                variable_values=dict(
                    tenant=tenant, exclusiveStartKey=exclusive_start_key
                ),
            )["ListApps"]
        objs = [resource_factory(data) for data in result["echos"]]
        return (
            objs + list_apps(exclusive_start_key)
            if (exclusive_start_key := result.get("lastEvaluatedKey"))
            else objs
        )

    apps = list_apps()
    apps_json = dict()
    for app in apps:
        apps_json = always_merger.merge(apps_json, app.encode())
    with open("apps.tf.json", "wt") as tf_json:
        json.dump(default=encode_terraform, fp=tf_json, indent=2, obj=apps_json)
    return apps


def __process_functions(gql_client: GqlClient, tenant: str) -> list[TerraformObject]:
    query = gql(
        """
        query listFunctions($tenant: String!, $exclusiveStartKey: AWSJSON) {
            ListFunctions(tenant: $tenant, exclusiveStartKey: $exclusiveStartKey) {
                echos {
                    __typename
                    code
                    description
                    name
                    readme
                    requirements
                    system
                    ... on BitmapperFunction {
                        argumentMessageType {
                            name
                        }
                    }
                    ... on ProcessorFunction {
                        argumentMessageType {
                            name
                        }
                        returnMessageType {
                            name
                        }
                    }
                }
                lastEvaluatedKey
            }
        }
        """
    )

    def list_functions(exclusive_start_key: Any = None) -> list[TerraformObject]:
        with gql_client as session:
            result = session.execute(
                query,
                variable_values=dict(
                    tenant=tenant, exclusiveStartKey=exclusive_start_key
                ),
            )["ListFunctions"]
        objs = [
            data_source_factory(data) if data.get("system") else resource_factory(data)
            for data in result["echos"]
        ]
        return (
            objs + list_functions(exclusive_start_key)
            if (exclusive_start_key := result.get("lastEvaluatedKey"))
            else objs
        )

    functions = list_functions()
    functions_json = dict()
    for func in functions:
        functions_json = always_merger.merge(functions_json, func.encode())
    with open("functions.tf.json", "wt") as tf_json:
        json.dump(default=encode_terraform, fp=tf_json, indent=2, obj=functions_json)
    return functions


def __process_kms_keys(gql_client: GqlClient, tenant: str) -> list[TerraformObject]:
    query = gql(
        """
        query listKmsKeys($tenant: String!, $exclusiveStartKey: AWSJSON) {
            ListKmsKeys(tenant: $tenant, exclusiveStartKey: $exclusiveStartKey) {
                echos {
                    __typename
                    description
                    name
                }
                lastEvaluatedKey
            }
        }
        """
    )

    def list_kms_keys(exclusive_start_key: Any = None) -> list[TerraformObject]:
        with gql_client as session:
            result = session.execute(
                query,
                variable_values=dict(
                    tenant=tenant, exclusiveStartKey=exclusive_start_key
                ),
            )["ListKmsKeys"]
        objs = [resource_factory(data) for data in result["echos"]]
        return (
            objs + list_kms_keys(exclusive_start_key)
            if (exclusive_start_key := result.get("lastEvaluatedKey"))
            else objs
        )

    kms_keys = list_kms_keys()
    kms_keys_json = dict()
    for kms_key in kms_keys:
        kms_keys_json = always_merger.merge(kms_keys_json, kms_key.encode())
    with open("kms-keys.tf.json", "wt") as tf_json:
        json.dump(default=encode_terraform, fp=tf_json, indent=2, obj=kms_keys_json)
    return kms_keys


def __process_main(gql_client: GqlClient, tenant: str) -> list[TerraformObject]:
    main_json = dict(
        terraform=dict(
            required_providers=dict(
                echostream=dict(source="Echo-Stream/echostream", version=">=0.0.6")
            ),
            required_version=">=1.3.5",
        ),
    )
    with open("main.tf.json", "wt") as tf_json:
        json.dump(default=encode_terraform, fp=tf_json, indent=2, obj=main_json)
    provider_json = dict(
        provider=dict(echostream=dict()),
    )
    with open("provider.tf.json", "wt") as tf_json:
        json.dump(default=encode_terraform, fp=tf_json, indent=2, obj=provider_json)
    return list()


def __process_managed_node_types(
    gql_client: GqlClient, tenant: str
) -> list[TerraformObject]:
    query = gql(
        """
        query listManagedNodeTypes($tenant: String!, $exclusiveStartKey: AWSJSON) {
            ListManagedNodeTypes(tenant: $tenant, exclusiveStartKey: $exclusiveStartKey) {
                echos {
                    __typename
                    configTemplate
                    description
                    imageUri
                    mountRequirements {
                        description
                        source
                        target
                    }
                    name
                    portRequirements {
                        containerPort
                        description
                        protocol
                    }
                    readme
                    receiveMessageType {
                        name
                    }
                    sendMessageType {
                        name
                    }
                    system
                }
                lastEvaluatedKey
            }
        }
        """
    )

    def list_managed_node_types(
        exclusive_start_key: Any = None,
    ) -> list[TerraformObject]:
        with gql_client as session:
            result = session.execute(
                query,
                variable_values=dict(
                    tenant=tenant, exclusiveStartKey=exclusive_start_key
                ),
            )["ListManagedNodeTypes"]
        objs = [
            data_source_factory(data) if data.get("system") else resource_factory(data)
            for data in result["echos"]
        ]
        return (
            objs + list_managed_node_types(exclusive_start_key)
            if (exclusive_start_key := result.get("lastEvaluatedKey"))
            else objs
        )

    managed_node_types = list_managed_node_types()
    managed_node_types_json = dict()
    for managed_node_type in managed_node_types:
        managed_node_types_json = always_merger.merge(
            managed_node_types_json, managed_node_type.encode()
        )
    with open("managed-node-types.tf.json", "wt") as tf_json:
        json.dump(
            default=encode_terraform, fp=tf_json, indent=2, obj=managed_node_types_json
        )
    return managed_node_types


def __process_message_types(
    gql_client: GqlClient, tenant: str
) -> list[TerraformObject]:
    query = gql(
        """
        query listMessageTypes($tenant: String!, $exclusiveStartKey: AWSJSON) {
            ListMessageTypes(tenant: $tenant, exclusiveStartKey: $exclusiveStartKey) {
                echos {
                    __typename
                    auditor
                    bitmapperTemplate
                    description
                    name
                    processorTemplate
                    readme
                    requirements
                    sampleMessage
                    system
                }
                lastEvaluatedKey
            }
        }
        """
    )

    def list_message_types(exclusive_start_key: Any = None) -> list[TerraformObject]:
        with gql_client as session:
            result = session.execute(
                query,
                variable_values=dict(
                    tenant=tenant, exclusiveStartKey=exclusive_start_key
                ),
            )["ListMessageTypes"]
        objs = [
            data_source_factory(data) if data.get("system") else resource_factory(data)
            for data in result["echos"]
        ]
        return (
            objs + list_message_types(exclusive_start_key)
            if (exclusive_start_key := result.get("lastEvaluatedKey"))
            else objs
        )

    message_types = list_message_types()
    message_types_json = dict()
    for message_type in message_types:
        message_types_json = always_merger.merge(
            message_types_json, message_type.encode()
        )
    with open("message-types.tf.json", "wt") as tf_json:
        json.dump(
            default=encode_terraform, fp=tf_json, indent=2, obj=message_types_json
        )
    return message_types


def __process_nodes_and_edges(
    gql_client: GqlClient, tenant: str
) -> list[TerraformObject]:
    query = gql(
        """
        query listNodes($tenant: String!, $exclusiveStartKey: AWSJSON) {
            ListNodes(tenant: $tenant, exclusiveStartKey: $exclusiveStartKey) {
                echos {
                    __typename
                    description
                    name
                    ... on AlertEmitterNode {
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on AppChangeReceiverNode {
                        app {
                            name
                        }
                    }
                    ... on AppChangeRouterNode {
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on AuditEmitterNode {
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on BitmapRouterNode {
                        config
                        inlineBitmapper
                        loggingLevel
                        managedBitmapper {
                            name
                        }
                        receiveMessageType {
                            name
                        }
                        requirements
                        routeTable
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on ChangeEmitterNode {
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on CrossTenantReceivingNode {
                        app {
                            name
                        }
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                        sendMessageType {
                            name
                        }
                    }
                    ... on CrossTenantSendingNode {
                        app {
                            name
                        }
                        config
                        inlineProcessor
                        loggingLevel
                        managedProcessor {
                            name
                        }
                        receiveMessageType {
                            name
                        }
                        requirements
                        sendMessageType {
                            name
                        }
                        sequentialProcessing
                    }
                    ... on DeadLetterEmitterNode {
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on ExternalNode {
                        app {
                            __typename
                            ... on CrossAccountApp {
                                name
                            }
                            ... on ExternalApp {
                                name
                            }
                        }
                        config
                        receiveMessageType {
                            name
                        }
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                        sendMessageType {
                            name
                        }
                    }
                    ... on FilesDotComWebhookNode {
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on LoadBalancerNode {
                        receiveMessageType {
                            name
                        }
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on LogEmitterNode {
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on ManagedNode {
                        app {
                            name
                        }
                        config
                        loggingLevel
                        managedNodeType {
                            name
                        }
                        mounts {
                            description
                            source
                            target
                        }
                        ports {
                            containerPort
                            hostAddress
                            hostPort
                            protocol
                        }
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on ProcessorNode {
                        config
                        inlineProcessor
                        loggingLevel
                        managedProcessor {
                            name
                        }
                        receiveMessageType {
                            name
                        }
                        requirements
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                        sendMessageType {
                            name
                        }
                        sequentialProcessing
                    }
                    ... on TimerNode {
                        scheduleExpression
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                    }
                    ... on WebhookNode {
                        config
                        inlineApiAuthenticator
                        loggingLevel
                        managedApiAuthenticator {
                            name
                        }
                        requirements
                        sendEdges {
                            __typename
                            description
                            kmsKey {
                                name
                            }
                            maxReceiveCount
                            source {
                                name
                            }
                            target {
                                name
                            }
                        }
                        sendMessageType {
                            name
                        }
                    }
                }
                lastEvaluatedKey
            }
        }
        """
    )

    def list_nodes(exclusive_start_key: Any = None) -> list[TerraformObject]:
        with gql_client as session:
            result = session.execute(
                query,
                variable_values=dict(
                    tenant=tenant, exclusiveStartKey=exclusive_start_key
                ),
            )["ListNodes"]
        objs = [
            data_source_factory(data) or resource_factory(data)
            for data in result["echos"]
        ]
        return (
            objs + list_nodes(exclusive_start_key)
            if (exclusive_start_key := result.get("lastEvaluatedKey"))
            else objs
        )

    nodes = list_nodes()
    nodes_json = dict()
    edges: list[TerraformObject] = list()
    edges_json = dict()
    for node in nodes:
        nodes_json = always_merger.merge(nodes_json, node.encode())
        for data in node.get("sendEdges", []):
            edge = resource_factory(data)
            edges.append(edge)
            edges_json = always_merger.merge(edges_json, edge.encode())
    with open("nodes.tf.json", "wt") as tf_json:
        json.dump(default=encode_terraform, fp=tf_json, indent=2, obj=nodes_json)
    with open("edges.tf.json", "wt") as tf_json:
        json.dump(default=encode_terraform, fp=tf_json, indent=2, obj=edges_json)
    return nodes + edges


def __process_tenant_and_tenant_users(
    gql_client: GqlClient, tenant: str
) -> list[TerraformObject]:
    query = gql(
        """
        query getTenant($tenant: String!) {
            GetTenant(tenant: $tenant) {
                __typename
                config
                description
                users {
                    __typename
                    email
                    role
                    status
                }
            }
        }
        """
    )
    with gql_client as session:
        data = session.execute(query, variable_values=dict(tenant=tenant))["GetTenant"]
    tenant_resource = resource_factory(data)
    with open("tenant.tf.json", "wt") as tf_json:
        json.dump(
            default=encode_terraform, fp=tf_json, indent=2, obj=tenant_resource.encode()
        )
    tenant_users: list[TerraformObject] = list()
    for data in list(data.get("users", [])):
        tenant_users.append(resource_factory(data))
    tenant_users_json = dict()
    for tenant_user in tenant_users:
        tenant_users_json = always_merger.merge(tenant_users_json, tenant_user.encode())
    with open("tenant-users.tf.json", "wt") as tf_json:
        json.dump(default=encode_terraform, fp=tf_json, indent=2, obj=tenant_users_json)
    return [tenant_resource] + tenant_users
