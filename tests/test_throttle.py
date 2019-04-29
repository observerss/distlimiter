# coding: utf-8
import time
import random
import threading
import statistics
import multiprocessing
from distlimiter import throttle


@throttle('add0',
          rate_per_second=100,
          method='smooth',
          redis_url='redis://localhost')
def add(a: int, b: int) -> int:
    return a + b


start_times = []


@throttle('add2',
          rate_per_second=100,
          method='smooth',
          redis_url='redis://localhost')
def add2(a: int, b: int) -> int:
    start_times.append(time.time())
    time.sleep(random.random() / 5)
    return a + b


def test_single_throttle():
    assert 2 == add(1, 1)


def test_loop_throttle():
    t1 = time.time()
    for _ in range(11):
        assert 3 == add(1, 2)
    t2 = time.time()
    # 之所以放宽0.1秒是考虑到nose处理的overhead
    assert 12 / 100 > t2 - t1 > 10 / 100, '限速100qps, 但11次连续请求在{:.6f}秒内完成'.format(
        t2 - t1)


def test_multiprocessing_throttle():
    t1 = time.time()
    tasks = []
    for _ in range(11):
        task = multiprocessing.Process(target=add, args=(1, 3), daemon=True)
        task.start()
        tasks.append(task)

    for task in tasks:
        task.join()
    t2 = time.time()
    # 之所以放宽0.4秒是考虑到nose+多进程处理的overhead
    assert 13 / 100 > t2 - t1 > 10 / 100, '限速100qps, 但多进程11次连续请求在{:.6f}秒内完成'.format(
        t2 - t1)


def test_break_between_tasks():
    assert 3 == add(1, 2)
    time.sleep(0.1)
    t1 = time.time()
    assert 3 == add(1, 2)
    t2 = time.time()
    # 要考虑到redis的overhead
    assert t2 - t1 < 0.006


def test_random_work():
    start_times.clear()
    tasks = []
    for _ in range(11):
        task = threading.Thread(target=add2, args=(1, 3), daemon=True)
        task.start()
        tasks.append(task)

    for task in tasks:
        task.join()

    deltas = [
        start_times[i] - start_times[i - 1]
        for i in range(1, len(start_times))
    ]
    mean, std = statistics.mean(deltas), statistics.stdev(deltas)
    assert 0.01 * 0.9 < mean < 0.01 * 1.1, mean
    assert std < 0.005, std


if __name__ == "__main__":
    test_random_work()
    t0 = time.time()
    for _ in range(11):
        add(1, 2)
    print('11次限速100qps的操作耗时', time.time() - t0)
