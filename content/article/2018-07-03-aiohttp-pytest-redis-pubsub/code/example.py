import aioredis

ADDRESS = ('localhost', 6379)
CHANNEL = 'subscribechannel'
KEY = 'testkey'


async def start_redis(loop):
    return await aioredis.create_redis(ADDRESS, loop=loop)


async def stop_redis(redis):
    redis.close()
    await redis.wait_closed()


async def store_id(redis, id):
    if await redis.sadd(KEY, id):
        await redis.publish(CHANNEL, id)
        return True
    return False
