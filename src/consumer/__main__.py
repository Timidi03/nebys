import asyncio

from src.consumer.app import create_consumer

if __name__ == "__main__":
    asyncio.run(create_consumer().run())
