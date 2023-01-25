import boto3


def s3_put(
    filename,
    data,
    bucket,
    region_name=None,
    endpoint_url=None,
    aws_access_key=None,
    aws_secret_access_key=None,
):
    # Create S3 client
    s3 = boto3.resource(
        "s3",
        region_name=region_name,
        use_ssl=True,
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_access_key,
    )

    obj = s3.Object(bucket, filename)
    obj.put(Body=data, StorageClass="ONEZONE_IA")
