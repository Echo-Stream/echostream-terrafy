# echostream-terrafy

EchoStream provides a graphical way to design, build and update processing an integration
networks in real time. 

However, there are teams that wish to manage all resources (EchoStream and others, such as 
Azure or AWS) in Infrastructure as Code (IaC). If you have designed alarge network of 
processing resource in EchoStream, the ideal solution would be to introspect and extract
those resources into Terraform scripts.

`echostream-terrafy` is the tool that does this, creating:

- A set of Terraform scripts in HCL JSON format that exactly matches the current state
of your Tenant. These may be used as-is or may be converted into a module for use in
a larger Terraform script.
- A `terraform.tfstate` file that has all of the resources in the Terraform scripts imported.

## Installation
`echostream-terrafy` is a Python package that provides an executable. To install it:

1. Install [Python](https://www.python.org/downloads/) >= 3.9 for your device.
2. Install [Terraform](https://developer.hashicorp.com/terraform/downloads?ajs_aid=5c90e8ca-c3b8-428a-a881-e7ec9cedebc8&product_intent=terraform) >= 1.3.5 for your device.
    > Warning - if you do not install Terraform to a location in your PATH, make note of the installation location!
3. Create a Python virtual environment for the `echostream-terrafy` installation. This is an optional step, but it prevents Python package mismatch issues and is best practice.
    ```shell
    python -m venv echostream-terrafy
    ```
4. Activate the virtual environment and install `echostream-terrafy` into it.
    ```shell
    source echostream-terrafy/bin/activate
    pip install echostream-terrafy
    ```
    > Note - to deactivate the virtual environment, simply type `deactivate` at the command prompt.

## Usage

In your EchoStream Tenant, create an [ApiUser](https://docs.echo.stream/docs/api-users) with the admin role.

Make note of the following in your ApiUser's credentials:
- GraphQL Appsync Endpoint
- Client Id
- Username
- Password
- User Pool Id

You may execute `echostream-terrafy` using either environment variables, command-line parameters, or a combination of both. If a parameter is present in both the environment and on the command line, the command line takes precedence.

All output from `echostream-terrafy` executions will be written to the current working directory, with existing files (including the `terraform.tfstate` file) being overwritten.

> Note- it is recommended that you create a directory for the output of `echostream-terrafy` and execute it within that directory.

> Warning - if you did not install `terraform` into your PATH, you must let `echostream-terrafy` know where to find it. This may be accomplished by specifying the `--terraform` command-line parameter with the full path to the `terraform` executable.

### Executing with environment variables
```shell
source echostream-terrafy/bin/activate
export ECHOSTREAM_APPSYNC_ENDPOINT=<api_user_appsync_endpoint>
export ECHOSTREAM_CLIENT_ID=<api_user_client_id>
export ECHOSTREAM_PASSWORD=<api_user_password>
export ECHOSTREAM_TENANT=<my_tenant_name>
export ECHOSTREAM_USER_POOL_ID=<api_user_user_pool_id>
export ECHOSTREAM_USERNAME=<api_user_username>
echostream-terrafy
deactivate
```

### Executing using command-line variables
```shell
source echostream-terrafy/bin/activate
echostream-terrafy \
    --appsync-endpoint <api_user_appsync_endpoint> \
    --client-id <api_user_client_id> \
    --password <api_user_password> \
    --tenant <my_tenant_name> \
    --user-pool-id <api_user_user_pool_id> \
    --username <api_user_username>
deactivate
```

## Output
`echostream-terrafy` will generate the following files.

| Filename | Content |
| --- | --- |
| api-users.tf.json | The ApiUser resources |
| apps.tf.json | The App resources |
| functions.tf.json | The Function data sources and resources |
| kms-keys.tf.json | The KmsKey resources (except the Tenant default KmsKey) |
| main.tf.json | The `terraform` block |
| managed-node-types.tf.json | The ManagedNodeType data sources and resources  |
| message-types.tf.json | The MessageType data sources and resources  |
| nodes.tf.json | The Node data sources and resources  |
| provider.tf.json | The `provider` block |
| tenant-users.tf.json | The TenantUser resources |
| tenant.json | The Tenant resource |
| terraform.tfstate | The current state, imported |

### Using the output as-is
You may use the output from `echostream-terrafy` as-is to manage your Tenant.

Simply make any changes that you wish to it and run `terraform plan` or `terraform apply`.

> Warning - rerunning `echostream-terrafy` after you have made manual changes will result in those changes being overwritten!

### Using the output as a Terraform [module](https://developer.hashicorp.com/terraform/language/modules)
1. Copy all of the `.tf.json` files to another folder.
2. Remove `provider.tf.json`. The provider should be passed in by the module caller.
3. Add a `variables.tf` file and variablize any input (e.g. - configs) that you wish to be modifiable by module users.
4. Add an `outputs.tf` file and output any information that needs to be accessed by module users.
5. Register the module with a public/private Terraform registry or include it in a `modules` directory (either directly or as a `git` submodule) in another Terraform project.

### Upload the output to Terraform Cloud or Terraform Enterprise
Please see Terraform [Cloud](https://developer.hashicorp.com/terraform/cloud-docs/migrate)/[Enterprise](https://developer.hashicorp.com/terraform/enterprise/migrate) documentation for how to migrate a local terraform workspace to those products.
