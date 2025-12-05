import os
import subprocess
import tarfile
import uuid
from datetime import datetime
from typing import Optional, Union
from pathlib import Path

import google.auth
import yaml
from google.api_core import client_options, operation
from google.cloud import storage
from google.cloud.devtools import cloudbuild_v1
from google.cloud.devtools.cloudbuild_v1.types import Source, StorageSource, Build, BuildOperationMetadata # Added BuildOperationMetadata, Build
from google.protobuf import duration_pb2
from yaml.loader import FullLoader
from google.cloud.aiplatform import utils

# CLOUD_BUILD_FILEPATH should be relative to the context (repo root)
CLOUD_BUILD_CONFIG_PATH = "cloudbuild.yaml"
SERVICE_BASE_PATH = "cloudbuild.googleapis.com"

def download_file(bucket_name: str, blob_name: str, destination_file: str) -> str:
    """Copies a remote GCS file to a local path"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(destination_file)

    return destination_file


def upload_file(
    local_file_path: str,
    remote_file_path: str,
) -> str:
    """Copies a local file to a GCS path"""
    bucket_name, blob_name = utils.extract_bucket_and_prefix_from_gcs_path(
        remote_file_path
    )
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_file_path)

    return remote_file_path


def archive_code_and_upload(
    source_dir: Path, staging_bucket: str, project_id: str
) -> str:
    """Archives source code and uploads it to a GCS bucket."""
    unique_id = uuid.uuid4()
    source_archived_file = f"source_archive_{unique_id}.tar.gz"
    local_archive_path = source_dir / source_archived_file

    print(f"    [utils] Archiving source from {source_dir}...")
    # Get all files in the directory recursively, filtering ignored ones
    all_files = []
    for root, dirs, files in os.walk(source_dir):
        # Sort for determinism
        dirs.sort()
        files.sort()

        # Filter ignored directories/files (similar to _calculate_source_hash)
        dirs[:] = [
            d for d in dirs
            if d not in (".git", "__pycache__", ".ipynb_checkpoints", "node_modules")
        ]

        for file in files:
            if file in (".DS_Store", "package-lock.json", "npm-debug.log") or file.endswith(".pyc"):
                continue
            all_files.append(Path(root) / file)
    
    print(f"    [utils] Found {len(all_files)} files to archive.")
    
    # Create tar.gz archive
    with tarfile.open(local_archive_path, "w:gz") as tar:
        for file_path in all_files:
            tar.add(file_path, arcname=file_path.relative_to(source_dir))
    
    archive_size = local_archive_path.stat().st_size / (1024 * 1024)
    print(f"    [utils] Archive created: {local_archive_path} ({archive_size:.2f} MB)")

    # Upload archive to GCS bucket
    destination_blob_path = f"source_archives/{project_id}/{source_archived_file}"
    remote_file_path = f"gs://{staging_bucket}/{destination_blob_path}"
    
    print(f"    [utils] Uploading to {remote_file_path}...")
    upload_file(local_file_path=str(local_archive_path), remote_file_path=remote_file_path)
    print(f"    [utils] Upload complete.")

    # Clean up local archive
    local_archive_path.unlink(missing_ok=True)

    return remote_file_path


def build_and_push_docker_images(
    project_id: str,
    staging_bucket: str,
    repo_root: Path,
    timeout_in_seconds: int = 1200, # 20 minutes
) -> Build:
    """Builds and pushes Docker images using the Cloud Build API."""
    # Load build steps from YAML
    print(f"    [utils] Loading Cloud Build config from {repo_root / CLOUD_BUILD_CONFIG_PATH}...")
    cloudbuild_config = yaml.load(open(repo_root / CLOUD_BUILD_CONFIG_PATH), Loader=FullLoader)

    # Authorize the client with Google defaults
    credentials, _ = google.auth.default()

    client = cloudbuild_v1.services.cloud_build.CloudBuildClient(
        credentials=credentials
    )

    # Upload source to GCS (Cloud Build will fetch it from there)
    # We are uploading the whole repo root as context.
    # The cloudbuild.yaml uses paths relative to this root.
    print(f"    [utils] Preparing source archive...")
    source_archive_gcs_uri = archive_code_and_upload(repo_root, staging_bucket, project_id)
    
    (source_archived_file_gcs_bucket, source_archived_file_gcs_object,) = (
        utils.extract_bucket_and_prefix_from_gcs_path(source_archive_gcs_uri)
    )

    build = cloudbuild_v1.Build()
    build.source = Source(
        storage_source=StorageSource(
            bucket=source_archived_file_gcs_bucket,
            object_=source_archived_file_gcs_object,
        )
    )
    build.steps = cloudbuild_config["steps"]
    if "images" in cloudbuild_config:
        build.images = cloudbuild_config["images"]
    
    # Pass project_id as a substitution for the YAML
    # build.substitutions = {"PROJECT_ID": project_id}

    build.timeout = duration_pb2.Duration(seconds=timeout_in_seconds)
    build.queue_ttl = duration_pb2.Duration(seconds=timeout_in_seconds)

    print(f"    [utils] Submitting Cloud Build job for project {project_id}...")
    operation = client.create_build(project_id=project_id, build=build)
    print(f"    [utils] Build submitted. Operation ID: {operation.operation.name}")

    # Block and wait for the result
    operation_result = operation.result(timeout=timeout_in_seconds)
    print(f"    [utils] Cloud Build operation completed.")
    
    return operation_result
