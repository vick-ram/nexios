import asyncio

import aiosqlite


async def test_aiosqlite_connection() -> None:
    conn = await aiosqlite.connect(":memory:")
    cursor = await conn.cursor()
    try:
        # Test if connection exists
        await cursor.execute("SELECT 1")
        print("Connected")
    except Exception as err:
        print(f"Error occurred during test: {err}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_aiosqlite_connection())