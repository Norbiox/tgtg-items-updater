#!/usr/env/bin python
import json

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from loguru import logger
from pydantic import BaseSettings, Field, FilePath
from tgtg import TgtgAPIError, TgtgClient


class Settings(BaseSettings):
    log_file: str = Field("tgtg_items_updater.log", env="LOG_FILE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class KafkaSettings(Settings):
    bootstrap_servers: str = Field("broker:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    trigger_topic: str = Field("trigger", env="KAFKA_TRIGGER_TOPIC")
    output_topic: str = Field("output", env="KAFKA_OUTPUT_TOPIC")
    timeout: int = Field(10, env="KAFKA_TIMEOUT")


class TgtgQueryParams(BaseSettings):
    latitude: float
    longitude: float
    radius: int
    favorites_only: bool


class TgtgCredentials(BaseSettings):
    access_token: str
    refresh_token: str
    user_id: str


class TgtgSettings(Settings):
    credentials_file: FilePath = Field("credentials.json", env="TGTG_CREDENTIALS_FILE")
    query_params_file: FilePath = Field("query_params.json", env="TGTG_QUERY_PARAMS_FILE")

    @property
    def credentials(self) -> TgtgCredentials:
        with open(tgtg_settings.credentials_file) as f:
            return TgtgCredentials(**json.loads(f.read())).dict()

    @property
    def query_params(self) -> TgtgQueryParams:
        with open(tgtg_settings.query_params_file) as f:
            return TgtgQueryParams(**json.loads(f.read())).dict()


if __name__ == "__main__":
    settings = Settings()
    logger.add(settings.log_file, rotation="00:00")

    # setup Kafka connectors
    kafka_settings = KafkaSettings()
    logger.info("Setting up kafka connection...")
    kafka_consumer = KafkaConsumer(
        kafka_settings.trigger_topic,
        bootstrap_servers=kafka_settings.bootstrap_servers,
    )
    kafka_producer = KafkaProducer(bootstrap_servers=kafka_settings.bootstrap_servers)

    # setup TooGoodToGo client
    logger.info("Setting up TGTG client...")
    tgtg_settings = TgtgSettings()

    logger.info("Waiting for ticks...")
    for msg in kafka_consumer:
        logger.debug("Ticked!")

        # fetch items from TooGoodToGo
        logger.info("Fetching items from TGTG...")
        try:
            items = TgtgClient(**tgtg_settings.credentials).get_items(**tgtg_settings.query_params)
        except TgtgAPIError | KeyError:
            logger.exception(record_metadata)
            continue

        # send items to Kafka
        logger.info("Sending fetched items to kafka...")
        future = kafka_producer.send(
            kafka_settings.output_topic,
            json.dumps(items, indent=4).encode("utf-8"),
        )
        try:
            record_metadata = future.get(timeout=kafka_settings.timeout)
        except KafkaError:
            logger.exception(record_metadata)
        else:
            logger.info("Items has been sent")
