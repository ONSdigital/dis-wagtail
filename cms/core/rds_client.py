from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from mypy_boto3_rds import RDSClient


def create_rds_client(aws_region: str) -> RDSClient:
    return boto3.client("rds", region_name=aws_region)
