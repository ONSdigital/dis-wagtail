import boto3


def create_rds_client(aws_region: str):
    return boto3.client("rds", region_name=aws_region)
