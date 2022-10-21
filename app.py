#!/usr/env/bin python
import asyncio
import json
import time
from typing import cast

import aiokafka
import kafkaesk
from loguru import logger
from pydantic import BaseModel, BaseSettings, Field, FilePath
from tgtg import TgtgAPIError, TgtgClient


class TgtgCredentials(BaseSettings):
    access_token: str
    refresh_token: str
    user_id: str


class Settings(BaseSettings):
    log_file: str = Field("tgtg_items_updater.log", env="LOG_FILE")
    kafka_topic_prefix: str = Field("tgtg_notifier.", env="KAFKA_TOPIC_PREFIX")
    kafka_bootstrap_servers: str = Field("broker:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    tgtg_credentials_file: FilePath = Field("credentials.json", env="TGTG_CREDENTIALS_FILE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def tgtg_credentials(self) -> TgtgCredentials:
        with open(self.tgtg_credentials_file) as f:
            return TgtgCredentials(**json.loads(f.read())).dict()


class MyApp(kafkaesk.Application):
    """
    Custom kafkaesk application - because `auto_offset_reset` setting is hardcoded
    to 'earliest' in original one and cannot be overwritten.
    """

    def consumer_factory(self, group_id: str) -> aiokafka.AIOKafkaConsumer:
        consumer = super().consumer_factory(self, group_id)
        consumer._auto_offset_reset = "latest"
        return consumer


settings = Settings()
logger.add(settings.log_file, rotation="00:00")

app = kafkaesk.Application(
    kafka_servers=settings.kafka_bootstrap_servers,
    topic_prefix=settings.kafka_topic_prefix,
)


@app.schema("Trigger", version=1, retention=24 * 60 * 60)
class TriggerMessage(BaseSettings):
    latitude: float
    longitude: float
    radius: int
    favorites_only: bool


@app.schema("FetchedItems", version=1, retention=7 * 24 * 60 * 60)
class FetchedItems(BaseModel):
    trigger_message: TriggerMessage
    checked_at: float  # timestamp
    items: list[dict]


@app.subscribe("trigger", "tgtg")
async def get_items_from_tgtg(data: TriggerMessage, subscriber):
    logger.info("Triggered!")

    try:
        checked_at = time.time()
        logger.info("Fetching items from TGTG...")
        items = TgtgClient(**settings.tgtg_credentials).get_items(
            latitude=data.latitude,
            longitude=data.longitude,
            radius=data.radius,
            favorites_only=data.favorites_only,
        )
    except TgtgAPIError | KeyError:
        logger.exception()
        return

    # send items to Kafka
    logger.info("Sending fetched items to kafka...")
    message = FetchedItems(trigger_message=data, checked_at=checked_at, items=items)
    await app.publish("fetched_items", data=message)
    logger.info("Items has been sent")


if __name__ == "__main__":
    kafkaesk.run(app)
