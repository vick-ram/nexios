from psycopg_pool import ConnectionPool as PsycopgPool
import psycopg

def quick_test():
    """Quick test to verify both pools work"""
    dsn = "postgresql://vickram:Vickram9038@localhost:5432/p_orm"
    
    # Test psycopg3 pool
    print("Testing psycopg3 pool...")
    with PsycopgPool(dsn, min_size=2, max_size=5) as psy_pool:
        with psy_pool.connection() as psy_conn:
            with psy_conn.cursor() as psy_cur:
                psy_cur.execute("SELECT 1")
                result = psy_cur.fetchone()
                print(f"psycopg3 pool works: {result}")
    
    # Test custom pool
    print("Testing custom pool...")
    from nexios.orm.backends.pool.base import PoolConfig
    from nexios.orm.backends.pool.connection_pool import ConnectionPool
    from nexios.orm.backends.dbapi.postgres.psycopg_ import PsycopgConnection
    
    config = PoolConfig(min_size=2, max_size=5)

    pool = ConnectionPool(
        lambda: PsycopgConnection(psycopg.connect(dsn)),
        config
    )

    import time
    time.sleep(0.5)
    
    print("Getting connection from custom pool...")
    with pool.connection() as conn:
        print("Got connection, creating cursor...")
        cur = conn.cursor()
        print("Executing query...")
        cur.execute("SELECT 1")
        result = cur.fetchone()
        print(f"Custom pool works: {result}")
    
    pool.close()
    print("Both pools working correctly!")

# Run quick test first
quick_test()