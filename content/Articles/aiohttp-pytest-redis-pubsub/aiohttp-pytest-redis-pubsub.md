Title: Testing Redis PUB/SUB in Python / aiohttp with pytest
Slug: aiohttp-pytest-redis-pubsub
Date: 2018-07-03 09:00
Tags: python, redis, aiohttp, pytest
Lang: en
Abstract: Send a callback as a fixture and be done with it
Tweet: Testing #Redis PUB/SUB in #Python / #aiohttp with #pytest

Recently I had to write [Python](https://python.org) unit tests for the [Redis PUB/SUB mechanism](https://redis.io/topics/pubsub). Backend code is written around the [async](https://docs.python.org/3/library/asyncio.html) web framework [aiohttp](https://aiohttp.readthedocs.io/en/stable/index.html) and tests are ran with [pytest](https://docs.pytest.org/en/latest/). I was looking for a way to keep test code as compact as possible to make it easy to read while hiding the piping (database connection, async loop manipulation, etc). I also wanted to be able to send a command to Redis and read a resulting message from a PUB topic.

## Handling Redis connection in a fixture

Let's say we want to test the following function `store_id`:

``` python
async def store_id(redis, id):
  return await redis.sadd(KEY, id)
```

Ideally the testing code should not have to deal with opening / closing a connection to a Redis engine:

- it makes it easier to replace the redis object by a mock
- it keep the test case readable and focused on actual testing and nothing else


This is how the test case should look like:

``` python
async def test_store_id(redis):
    id = uuid.UUID4()
    assert await store_id(redis, id)
```

If you are not familiar with pytest, the `redis` argument here is actually a [testing fixture](https://docs.pytest.org/en/latest/fixture.html): this value is computed each time a test / module / session (depending of the [scope](https://docs.pytest.org/en/latest/fixture.html#scope-sharing-a-fixture-instance-across-tests-in-a-class-module-or-session] of the fixture)) is ran and injected into each test function. The [aiohttp plugin for pytest](https://pypi.org/project/pytest-aiohttp/) defines a few fixtures. Here `loop` (giving access to the current async execution loop) is particularly useful to setup a new Redis connection: `aioredis.create_redis` is async and will run in the default loop if not specified. However, the fixture function is already running within a loop (not necessarily the default one, we don't know about the implementation details of pytest): `create_redis` will raise an exception if not passed the current loop.

A very nice feature of pytest fixtures is [the ability of expressing teardown](https://docs.pytest.org/en/latest/fixture.html#fixture-finalization-executing-teardown-code) code in a simple way: if the function `yield` a value (instead of simply returning it), all the remaining code will be executed at the end of the fixture scope. This is especially convenient to ensure database connections are cleanly closed.

This is what the test module looks like:

``` python
import aioredis
import pytest


async def start_redis(loop):
    return await aioredis.create_redis(loop=loop)


async def stop_redis(redis):
    redis.close()
    await redis.wait_closed()


@pytest.fixture()
def redis(loop):
    redis = loop.run_until_complete(start_redis(loop))
    yield redis
    loop.run_until_complete(stop_redis(redis))


async def test_store_id(redis):
    id = uuid.uuid4()
    assert await store_id(redis, id)
```

## Testing PUB/SUB

Now let's say that `store_id` publishes the newly stored ID through a PUB/SUB channel:

``` python
async def store_id(redis, id):
    if await redis.sadd(KEY, id):
        await redis.publish(CHANNEL, id)
    return False
```

We want to test if the ID is properly published, but still hide the implementation details around connection setup / teardown. A neat way of achieving this is to have a fixture returning a callable (a closure in our case, but if could be class with a `__call__` method), hiding all the piping code. The callable will take another callable as an argument, to be executed when a message is received.

``` python
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
```

Note that we need to open another connection dedicated to SUBSCRIBE to Redis messages: the same connection cannot be used both to emit commands to Redis and listen to PUB/SUB.

From Redis [doc](https://redis.io/topics/pubsub):

> A client subscribed to one or more channels should not issue commands, although it can subscribe and unsubscribe to and from other channels. The replies to subscription and unsubscription operations are sent in the form of messages, so that the client can just read a coherent stream of messages where the first element indicates the type of message. The commands that are allowed in the context of a subscribed client are SUBSCRIBE, PSUBSCRIBE, UNSUBSCRIBE, PUNSUBSCRIBE, PING and QUIT.

Now the test case just has to define a function that will be executed when a message is received. Result of the tested function and the SUBSCRIBE callbacks are simultaneously awaited with [`asyncio.gather`](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather).

``` python
async def test_store_id(redis, listen):
  id = uuid.UUID4()

  def on_message_received(msg):
    assert msg == str(id)

  results = await asyncio.gather(
    listen(on_message_received),
    store_id(redis, id)
  )
  assert results[1] # Checking the return value for store_id
```

Full code for this example is available [here](https://github.com/charlesfleche/charlesfleche.net/content/Articles/aiohttp-pytest-redis-pubsub/code).
