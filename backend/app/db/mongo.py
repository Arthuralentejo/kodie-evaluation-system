from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings
from app.core.logger import build_log_message, get_logger

logger = get_logger("kodie.db.mongo")


class MongoClientSingleton:
    _instance: "MongoClientSingleton | None" = None

    def __new__(cls) -> "MongoClientSingleton":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance

    def get_client(self) -> AsyncIOMotorClient:
        if self._client is None:
            logger.info(
                build_log_message(
                    "mongo_client_initializing",
                    mongo_db_name=settings.mongo_db_name,
                )
            )
            self._client = AsyncIOMotorClient(settings.mongo_uri)
            logger.info(build_log_message("mongo_client_initialized", mongo_db_name=settings.mongo_db_name))
        return self._client

    def get_db(self) -> AsyncIOMotorDatabase:
        return self.get_client()[settings.mongo_db_name]

    async def ping_db(self) -> None:
        logger.debug(build_log_message("mongo_ping_started", mongo_db_name=settings.mongo_db_name))
        await self.get_db().command("ping")
        logger.debug(build_log_message("mongo_ping_completed", mongo_db_name=settings.mongo_db_name))

    async def close_client(self) -> None:
        if self._client is not None:
            logger.info(build_log_message("mongo_client_closing", mongo_db_name=settings.mongo_db_name))
            self._client.close()
            self._client = None
            logger.info(build_log_message("mongo_client_closed", mongo_db_name=settings.mongo_db_name))


mongo_client_singleton = MongoClientSingleton()


def get_client() -> AsyncIOMotorClient:
    return mongo_client_singleton.get_client()


def get_db() -> AsyncIOMotorDatabase:
    return mongo_client_singleton.get_db()


async def ping_db() -> None:
    await mongo_client_singleton.ping_db()


async def close_client() -> None:
    await mongo_client_singleton.close_client()
