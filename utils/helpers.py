import asyncio
import random
import config

async def random_delay(min_sec=config.ACTION_DELAY_MIN, max_sec=config.ACTION_DELAY_MAX):
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)
