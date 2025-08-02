import logging
from google.cloud import vmmigration_v1
from google.api_core import exceptions
from google.cloud import secretmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)

def add_aws_source(project_id: str, location: str, source_id: str, aws_region: str, access_key_id_secret: str, secret_access_key_secret: str):
    """
    Adds a new migration source for an AWS source.

    Args:
        project_id: Google Cloud project ID.
        location: Google Cloud region for the source.
        source_id: The name for the new source.
        aws_region: The AWS region for the source VMs.
        access_key_id_secret: The resource name of the Secret Manager secret for the AWS access key ID.
            e.g. projects/your-gcp-project-id/secrets/aws-access-key-id/versions/latest
        secret_access_key_secret: The resource name of the Secret Manager secret for the AWS secret access key.
            e.g. projects/your-gcp-project-id/secrets/aws-secret-access-key/versions/latest
    """
    # Create a client
    client = vmmigration_v1.VmMigrationClient()
    secret_client = secretmanager.SecretManagerServiceClient()

    # It is recommended to use Secret Manager to store your credentials.
    # See: https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets
    try:
        access_key_id = secret_client.access_secret_version(name=access_key_id_secret).payload.data.decode("UTF-8")
        secret_access_key = secret_client.access_secret_version(name=secret_access_key_secret).payload.data.decode("UTF-8")
    except exceptions.NotFound as e:
        logging.error(f"Could not find a secret. Make sure your secrets exist and you have permissions. Secret name: {e}")
        raise

    aws_source_details = vmmigration_v1.AwsSourceDetails(
        aws_region=aws_region,
        access_key_creds=vmmigration_v1.AccessKeyCredentials(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key
        ),
    )

    source = vmmigration_v1.Source(
        aws=aws_source_details,
        description=f"AWS source for {aws_region}"
    )

    # Prepare the request
    request = vmmigration_v1.CreateSourceRequest(
        parent=f"projects/{project_id}/locations/{location}",
        source_id=source_id,
        source=source,
    )

    # Make the request
    logging.info(f"Creating AWS source '{source_id}' in project '{project_id}' location '{location}'...")
    try:
        operation = client.create_source(request=request)

        logging.info("Waiting for operation to complete...")
        response = operation.result()

        logging.info(f"Source created successfully: {response.name}")
        return response
    except exceptions.AlreadyExists:
        logging.warning(f"Source '{source_id}' already exists in {location}. No action taken.")
        source_path = client.source_path(project_id, location, source_id)
        return client.get_source(name=source_path)
    except Exception as e:
        logging.error(f"Failed to create source: {e}", exc_info=True)
        raise

def main():
    """Main function to demonstrate adding an AWS source."""
    # TODO: Replace with your actual project and source details.
    project_id = 'sandbox-dev-dbg'
    location = 'us-central1'
    source_id = 'test'
    aws_region = 'ca-central-1'

    # TODO: Replace with your Secret Manager secret resource names.
    # You should have stored your AWS credentials in Secret Manager.
    access_key_id_secret_name = f"projects/{project_id}/secrets/aws-access-key-id/versions/latest"
    secret_access_key_secret_name = f"projects/{project_id}/secrets/aws-secret-access-key/versions/latest"

    add_aws_source(project_id, location, source_id, aws_region, access_key_id_secret_name, secret_access_key_secret_name)

if __name__ == "__main__":
    main()
