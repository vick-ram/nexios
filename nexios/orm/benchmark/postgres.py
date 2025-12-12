import time
import statistics
import threading
import psycopg
from psycopg_pool import ConnectionPool as PsycopgPool
import matplotlib.pyplot as plt
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import numpy as np
from typing import Dict

# Disable verbose logging for clean benchmark output
logging.getLogger().setLevel(logging.ERROR)

class ConnectionPoolBenchmark:
    """Comprehensive benchmark suite for connection pools"""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.results = {}
    
    def benchmark_psycopg3_pool(self, min_size: int, max_size: int, operations: int, concurrency: int):
        """Benchmark psycopg3's built-in connection pool"""
        print(f"Testing psycopg3 pool: {min_size}-{max_size} connections, {operations} ops, {concurrency} threads")
        
        pool = PsycopgPool(
            self.dsn,
            min_size=min_size,
            max_size=max_size,
            timeout=10.0
        )
        
        times = []
        errors = 0
        
        def worker(worker_id: int):
            worker_times = []
            for i in range(operations // concurrency):
                start_time = time.perf_counter()
                try:
                    with pool.connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT 1")  # Small sleep to simulate work
                            cur.fetchone()
                    worker_times.append(time.perf_counter() - start_time)
                except Exception as e:
                    nonlocal errors
                    errors += 1
            return worker_times
        
        # Run benchmark
        start_total = time.perf_counter()
        futures = []
        try:
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                exec = [executor.submit(worker, i) for i in range(concurrency)]
                futures.extend(exec)
                # futures = [executor.submit(worker, i) for i in range(concurrency)]
                for future in as_completed(futures, timeout=60.0):
                    times.extend(future.result())
        except TimeoutError as e:
            print(f"  WARNING: Benchmark timed out after 60 seconds: {e}")
            # Collect whatever results we have
            for future in futures:
                if future.done():
                    try:
                        times.extend(future.result())
                    except Exception:
                        pass

        end_total = time.perf_counter()
        
        pool.close()
        
        total_time = end_total - start_total
        ops_per_sec = operations / total_time
        
        self.results['psycopg3'] = {
            'total_time': total_time,
            'operations_per_second': ops_per_sec,
            'avg_latency_ms': statistics.mean(times) * 1000,
            'p95_latency_ms': np.percentile(times, 95) * 1000 if times else 0,
            'errors': errors,
            'min_size': min_size,
            'max_size': max_size
        }
        
        print(f"  Results: {ops_per_sec:.1f} ops/sec, {statistics.mean(times)*1000:.1f}ms avg latency")
        return self.results['psycopg3']

    
    def benchmark_custom_pool(self, min_size: int, max_size: int, operations: int, concurrency: int):
        """Benchmark your custom connection pool"""
        print(f"Testing custom pool: {min_size}-{max_size} connections, {operations} ops, {concurrency} threads")
        
        from nexios.orm.pool.base import PoolConfig
        from nexios.orm.pool.connection_pool import  ConnectionPool
        
        config = PoolConfig(
            min_size=min_size,
            max_size=max_size,
            connection_timeout=10.0,
            health_check_interval=300,
            max_lifetime=3600,
            idle_timeout=1800
        )
        
        def create_conn():
            from nexios.orm.dbapi.postgres.psycopg_ import PsycopgConnection
            conn = psycopg.connect(self.dsn)
            return PsycopgConnection(conn)
        
        pool = ConnectionPool(create_conn, config)

        time.sleep(1)  # Allow pool to initialize
        
        times = []
        errors = 0
        
        def worker(worker_id: int):
            worker_times = []
            for i in range(operations // concurrency):
                start_time = time.perf_counter()
                try:
                    with pool.connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT 1")
                        cur.fetchone()
                    worker_times.append(time.perf_counter() - start_time)
                except Exception as e:
                    nonlocal errors
                    errors += 1
            return worker_times
        
        # Run benchmark
        start_total = time.perf_counter()
        futures_custom = []
        try:
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                exec_ = [executor.submit(worker, i) for i in range(concurrency)]
                futures_custom.extend(exec_)
                # futures_custom = [executor.submit(worker, i) for i in range(concurrency)]
                for future in as_completed(futures_custom):
                    times.extend(future.result())
        except TimeoutError as e:
            print(f"  WARNING: Benchmark timed out after 60 seconds: {e}")
            # Collect whatever results we have
            for future in futures_custom:
                if future.done():
                    try:
                        times.extend(future.result())
                    except:
                        pass

        end_total = time.perf_counter()
        
        pool.close()
        
        total_time = end_total - start_total
        ops_per_sec = operations / total_time
        
        self.results['custom'] = {
            'total_time': total_time,
            'operations_per_second': ops_per_sec,
            'avg_latency_ms': statistics.mean(times) * 1000,
            'p95_latency_ms': np.percentile(times, 95) * 1000 if times else 0,
            'errors': errors,
            'min_size': min_size,
            'max_size': max_size
        }
        
        print(f"  Results: {ops_per_sec:.1f} ops/sec, {statistics.mean(times)*1000:.1f}ms avg latency")
        return self.results['custom']

    def benchmark_under_load(self, pool_type: str, duration: int = 60):
        """Benchmark under sustained load with varying concurrency"""
        print(f"Testing {pool_type} pool under sustained load for {duration}s")
        
        if pool_type == 'psycopg3':
            pool = PsycopgPool(self.dsn, min_size=5, max_size=20, timeout=30.0)
        else:
            from nexios.orm.pool.base import PoolConfig
            from nexios.orm.pool.connection_pool import  ConnectionPool
            from nexios.orm.dbapi.postgres.psycopg_ import PsycopgConnection
            config = PoolConfig(min_size=5, max_size=20)
            conn = psycopg.connect(self.dsn)

            pool = ConnectionPool(lambda: PsycopgConnection(conn), config)
        
        metrics = {
            'throughput': [],
            'latency': [],
            'active_connections': [],
            'timestamp': []
        }
        
        stop_event = threading.Event()
        
        def monitor_worker():
            while not stop_event.is_set():
                if hasattr(pool, 'get_stats'):
                    stats = pool.get_stats() # type: ignore
                    metrics['active_connections'].append(stats.get('in_use_connections', 0))
                time.sleep(1)
        
        def load_worker(worker_id: int):
            worker_ops = 0
            worker_times = []
            
            while not stop_event.is_set():
                start_time = time.perf_counter()
                try:
                    if pool_type == 'psycopg3':
                        with pool.connection() as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT 1")
                            cur.fetchone()
                    else:
                        with pool.connection() as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT 1")
                            cur.fetchone()
                    
                    worker_times.append(time.perf_counter() - start_time)
                    worker_ops += 1
                    
                except Exception:
                    pass
            
            return worker_ops, worker_times
        
        # Start monitoring
        monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
        monitor_thread.start()
        
        # Ramp up load
        concurrency_levels = [10, 25, 50, 75, 100, 50, 25]  # Varying load
        current_concurrency = 0
        
        start_time = time.perf_counter()
        workers = []
        
        for target_concurrency in concurrency_levels:
            phase_duration = duration // len(concurrency_levels)
            phase_end = time.perf_counter() + phase_duration
            
            # Adjust concurrency
            if target_concurrency > current_concurrency:
                # Add workers
                for i in range(current_concurrency, target_concurrency):
                    t = threading.Thread(target=load_worker, args=(i,), daemon=True)
                    t.start()
                    workers.append(t)
            else:
                # Let natural completion reduce workers
                workers = workers[:target_concurrency]
            
            current_concurrency = target_concurrency
            
            # Collect metrics during this phase
            while time.perf_counter() < phase_end:
                time.sleep(1)
                if hasattr(pool, 'get_stats'):
                    stats = pool.get_stats() # type: ignore
                    metrics['throughput'].append(stats.get('current_throughput', 0))
                    metrics['latency'].append(stats.get('avg_operation_time', 0) * 1000)
                    metrics['timestamp'].append(time.perf_counter() - start_time)
        
        stop_event.set()
        
        if pool_type == 'psycopg3':
            pool.close()
        else:
            pool.close()
        
        return metrics

    def compare_pools(self, scenarios: Dict[str, Dict[str, int]]):
        """Compare both pools across different scenarios"""
        comparison_results = {}
        
        for scenario_name, params in scenarios.items():
            print(f"\n=== Scenario: {scenario_name} ===")
            print(f"Parameters: {params}")
            
            psycopg_result = self.benchmark_psycopg3_pool(**params)
            custom_result = self.benchmark_custom_pool(**params)
            
            comparison = {
                'psycopg3': psycopg_result,
                'custom': custom_result,
                'custom_vs_psycopg3': {
                    'throughput_ratio': custom_result['operations_per_second'] / psycopg_result['operations_per_second'],
                    'latency_ratio': custom_result['avg_latency_ms'] / psycopg_result['avg_latency_ms'],
                    'advantage': 'custom' if custom_result['operations_per_second'] > psycopg_result['operations_per_second'] else 'psycopg3'
                }
            }
            
            comparison_results[scenario_name] = comparison
            
            print(f"Winner: {comparison['custom_vs_psycopg3']['advantage']}")
            print(f"Throughput ratio: {comparison['custom_vs_psycopg3']['throughput_ratio']:.2f}x")
        
        return comparison_results

    def plot_results(self, comparison_results):
        """Plot comparison results"""
        scenarios = list(comparison_results.keys())
        psycopg_throughput = [comparison_results[s]['psycopg3']['operations_per_second'] for s in scenarios]
        custom_throughput = [comparison_results[s]['custom']['operations_per_second'] for s in scenarios]
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Throughput comparison
        x = range(len(scenarios))
        width = 0.35
        ax1.bar([i - width/2 for i in x], psycopg_throughput, width, label='psycopg3', alpha=0.7)
        ax1.bar([i + width/2 for i in x], custom_throughput, width, label='Custom', alpha=0.7)
        ax1.set_xlabel('Scenario')
        ax1.set_ylabel('Operations/sec')
        ax1.set_title('Throughput Comparison')
        ax1.set_xticks(x)
        ax1.set_xticklabels(scenarios, rotation=45)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Latency comparison
        psycopg_latency = [comparison_results[s]['psycopg3']['avg_latency_ms'] for s in scenarios]
        custom_latency = [comparison_results[s]['custom']['avg_latency_ms'] for s in scenarios]
        
        ax2.bar([i - width/2 for i in x], psycopg_latency, width, label='psycopg3', alpha=0.7)
        ax2.bar([i + width/2 for i in x], custom_latency, width, label='Custom', alpha=0.7)
        ax2.set_xlabel('Scenario')
        ax2.set_ylabel('Average Latency (ms)')
        ax2.set_title('Latency Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels(scenarios, rotation=45)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Performance ratio
        ratios = [comparison_results[s]['custom_vs_psycopg3']['throughput_ratio'] for s in scenarios]
        ax3.bar(x, ratios, color=['green' if r > 1 else 'red' for r in ratios], alpha=0.7)
        ax3.axhline(y=1, color='black', linestyle='--', alpha=0.5)
        ax3.set_xlabel('Scenario')
        ax3.set_ylabel('Custom/psycopg3 Throughput Ratio')
        ax3.set_title('Performance Ratio (>1 = Custom is better)')
        ax3.set_xticks(x)
        ax3.set_xticklabels(scenarios, rotation=45)
        ax3.grid(True, alpha=0.3)
        
        # Error comparison
        psycopg_errors = [comparison_results[s]['psycopg3']['errors'] for s in scenarios]
        custom_errors = [comparison_results[s]['custom']['errors'] for s in scenarios]
        
        ax4.bar([i - width/2 for i in x], psycopg_errors, width, label='psycopg3', alpha=0.7)
        ax4.bar([i + width/2 for i in x], custom_errors, width, label='Custom', alpha=0.7)
        ax4.set_xlabel('Scenario')
        ax4.set_ylabel('Errors')
        ax4.set_title('Error Comparison')
        ax4.set_xticks(x)
        ax4.set_xticklabels(scenarios, rotation=45)
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('pool_comparison.png', dpi=300, bbox_inches='tight')
        plt.show()

    def generate_report(self, comparison_results):
        """Generate a detailed comparison report"""
        report = []
        report.append("Connection Pool Benchmark Report")
        report.append("=" * 50)
        
        for scenario, results in comparison_results.items():
            report.append(f"\nScenario: {scenario}")
            report.append("-" * 30)
            
            custom = results['custom']
            psycopg = results['psycopg3']
            comparison = results['custom_vs_psycopg3']
            
            report.append(f"psycopg3: {psycopg['operations_per_second']:.1f} ops/sec, {psycopg['avg_latency_ms']:.1f}ms latency")
            report.append(f"Custom:   {custom['operations_per_second']:.1f} ops/sec, {custom['avg_latency_ms']:.1f}ms latency")
            report.append(f"Ratio:    {comparison['throughput_ratio']:.2f}x throughput, {comparison['latency_ratio']:.2f}x latency")
            report.append(f"Winner:   {comparison['advantage'].upper()}")
        
        # Overall summary
        custom_wins = sum(1 for r in comparison_results.values() 
                         if r['custom_vs_psycopg3']['advantage'] == 'custom')
        total_scenarios = len(comparison_results)
        
        report.append(f"\nOverall Summary:")
        report.append(f"Custom pool won {custom_wins}/{total_scenarios} scenarios")
        
        return "\n".join(report)