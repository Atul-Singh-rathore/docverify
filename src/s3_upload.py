import os
import io


def upload_to_s3(file_bytes: bytes, filename: str) -> str | None:
    """
    Uploads a document to AWS S3 and returns the public URL.
    Returns None if AWS credentials / bucket are not configured
    (so the app still works locally without S3).
    """
    bucket = os.getenv("AWS_S3_BUCKET", "").strip()
    region = os.getenv("AWS_REGION", "ap-south-1").strip()

    if not bucket:
        # S3 not configured — skip upload silently
        return None

    try:
        import boto3
        s3 = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        s3_key = f"docverify/uploads/{filename}"
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=io.BytesIO(file_bytes),
            ContentType="application/octet-stream",
        )

        url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
        return url

    except ImportError:
        return None  # boto3 not installed
    except Exception as e:
        print(f"[S3 Upload Warning] {e}")
        return None
