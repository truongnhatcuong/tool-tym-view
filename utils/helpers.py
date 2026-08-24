import asyncio
import random

async def random_delay(min_sec=1, max_sec=3):
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)
