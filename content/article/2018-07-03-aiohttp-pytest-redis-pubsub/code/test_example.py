import pytest
import uuid

from example import CHANNEL, start_redis, stop_redis, store_id


@pytest.fixture()
def redis(loop):
    redis = loop.run_until_complete(start_redis(loop))
    yield redis
    loop.run_until_complete(stop_redis(redis))


@pytest.fixture()
def listen(loop):
    # Setup: open a Redis connection and SUBSCRIBE to a channel

    redis = loop.run_until_complete(start_redis(loop))
    sub = loop.run_until_complete(redis.subscribe(CHANNEL))

    # Define the fixture callable

    async def wrapper(on_message_received):
        await sub.wait_message()
        msg = await sub.get()
        return await on_message_received(msg)
    yield wrapper

    # Teardown: close the connection to redis

    loop.run_until_complete(stop_redis(redis))


async def test_store_id(redis):
    id = str(uuid.uuid4())
    assert await store_id(redis, id)
