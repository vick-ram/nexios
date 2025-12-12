from nexios.orm.benchmark.mysql import MySQLConnectionPoolBenchmark

def run_benchmarks():
    """Run comprehensive benchmarks
    - MySQL connector only supports a maximum of 32 connections,
    Scenario from high concurrency will throw an exception
    """
    
    kwargs = {
        'host': '127.0.0.1',
        'user': 'vickram',
        'password': 'Vickram9038',
        'database': 'test_db'
    }
    
    benchmark = MySQLConnectionPoolBenchmark(**kwargs)
    
    # Define test scenarios
    scenarios = {
        'low_concurrency': {
            'min_size': 2, 'max_size': 10, 'operations': 1000, 'concurrency': 5
        },
        'high_concurrency': {
            'min_size': 5, 'max_size': 50, 'operations': 5000, 'concurrency': 50
        },
        'burst_load': {
            'min_size': 2, 'max_size': 20, 'operations': 2000, 'concurrency': 100
        },
        'sustained_load': {
            'min_size': 10, 'max_size': 30, 'operations': 10000, 'concurrency': 25
        },
        'overload': {
            'min_size': 5, 'max_size': 15, 'operations': 5000, 'concurrency': 100
        }
    }
    
    print("Starting Connection Pool Benchmark...")
    print("This will compare mysql.connetor's built-in pool vs your custom pool")
    print("=" * 60)
    
    # Run comparisons
    results = benchmark.compare_pools(scenarios)
    
    # Generate report
    report = benchmark.generate_report(results)
    print("\n" + report)
    
    # Plot results
    benchmark.plot_results(results)
    
    # Test under sustained load
    print("\nTesting under sustained variable load...")
    psycopg_metrics = benchmark.benchmark_under_load('mysql', duration=30)
    custom_metrics = benchmark.benchmark_under_load('custom', duration=30)

    print("\nSustained Load Metrics (mysql connector pool):", psycopg_metrics)
    print("Sustained Load Metrics (custom pool):", custom_metrics)
    
    return results

if __name__ == "__main__":
    results = run_benchmarks()