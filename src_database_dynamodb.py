"""
SkillForge AI — DynamoDB Client
Async wrapper around boto3 DynamoDB for learner profiles, sessions, and learning paths.
"""

import logging
from decimal import Decimal
from typing import Any, Optional

import aioboto3
from botocore.exceptions import ClientError

from src.config import settings

logger = logging.getLogger(__name__)


def _convert_floats(obj: Any) -> Any:
    """Convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_floats(i) for i in obj]
    return obj


def _convert_decimals(obj: Any) -> Any:
    """Convert DynamoDB Decimals back to float/int for application use."""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 != 0 else int(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimals(i) for i in obj]
    return obj


class DynamoDBClient:
    """
    Async DynamoDB client for SkillForge data persistence.

    Tables:
    - skillforge-users: Learner profiles, journey state, coaching history
    - skillforge-sessions: Active and historical coaching session data
    - skillforge-learning-paths: Personalized learning paths and progress
    """

    def __init__(self):
        self.session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region,
        )

    async def ensure_tables_exist(self) -> None:
        """Create DynamoDB tables if they don't exist (dev/test environments)."""
        tables_config = [
            {
                "TableName": settings.dynamodb_table_users,
                "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "user_id", "AttributeType": "S"}
                ],
                "BillingMode": "PAY_PER_REQUEST",
            },
            {
                "TableName": settings.dynamodb_table_sessions,
                "KeySchema": [
                    {"AttributeName": "session_id", "KeyType": "HASH"},
                    {"AttributeName": "user_id", "KeyType": "RANGE"},
                ],
                "AttributeDefinitions": [
                    {"AttributeName": "session_id", "AttributeType": "S"},
                    {"AttributeName": "user_id", "AttributeType": "S"},
                ],
                "BillingMode": "PAY_PER_REQUEST",
            },
            {
                "TableName": settings.dynamodb_table_learning_paths,
                "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                "AttributeDefinitions": [
                    {"AttributeName": "user_id", "AttributeType": "S"}
                ],
                "BillingMode": "PAY_PER_REQUEST",
            },
        ]

        async with self.session.resource("dynamodb") as dynamodb:
            for config in tables_config:
                try:
                    table = await dynamodb.create_table(**config)
                    await table.wait_until_exists()
                    logger.info(f"Created DynamoDB table: {config['TableName']}")
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ResourceInUseException":
                        logger.debug(f"Table already exists: {config['TableName']}")
                    else:
                        raise

    async def get_item(self, table: str, key: dict) -> Optional[dict]:
        """Retrieve a single item from a DynamoDB table."""
        async with self.session.resource("dynamodb") as dynamodb:
            tbl = await dynamodb.Table(table)
            response = await tbl.get_item(Key=key)
            item = response.get("Item")
            return _convert_decimals(item) if item else None

    async def put_item(self, table: str, item: dict) -> None:
        """Write an item to a DynamoDB table."""
        async with self.session.resource("dynamodb") as dynamodb:
            tbl = await dynamodb.Table(table)
            await tbl.put_item(Item=_convert_floats(item))

    async def update_item(
        self,
        table: str,
        key: dict,
        updates: dict,
    ) -> Optional[dict]:
        """Update specific fields of an existing DynamoDB item."""
        update_expression = "SET " + ", ".join(
            f"#{k} = :{k}" for k in updates.keys()
        )
        expression_attr_names = {f"#{k}": k for k in updates.keys()}
        expression_attr_values = {
            f":{k}": _convert_floats(v) for k, v in updates.items()
        }

        async with self.session.resource("dynamodb") as dynamodb:
            tbl = await dynamodb.Table(table)
            response = await tbl.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attr_names,
                ExpressionAttributeValues=expression_attr_values,
                ReturnValues="ALL_NEW",
            )
            item = response.get("Attributes")
            return _convert_decimals(item) if item else None

    async def delete_item(self, table: str, key: dict) -> None:
        """Delete an item from a DynamoDB table."""
        async with self.session.resource("dynamodb") as dynamodb:
            tbl = await dynamodb.Table(table)
            await tbl.delete_item(Key=key)

    async def query_items(
        self,
        table: str,
        key_condition: str,
        expression_values: dict,
        expression_names: Optional[dict] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Query items from a DynamoDB table."""
        kwargs = {
            "KeyConditionExpression": key_condition,
            "ExpressionAttributeValues": _convert_floats(expression_values),
            "Limit": limit,
        }
        if expression_names:
            kwargs["ExpressionAttributeNames"] = expression_names

        async with self.session.resource("dynamodb") as dynamodb:
            tbl = await dynamodb.Table(table)
            response = await tbl.query(**kwargs)
            return [_convert_decimals(item) for item in response.get("Items", [])]