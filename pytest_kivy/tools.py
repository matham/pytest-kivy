"""Tools
========


"""

__all__ = ('exhaust', )


async def exhaust(async_it):
    """Iterates through all the elements of the iterator until done.
    It does nothing with the elements.
    """
    async for _ in async_it:
        pass
