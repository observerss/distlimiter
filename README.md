# DistLimiter 分布式限流器

distlimiter是一个分布式限流器，基于Redis

## 特性

- 分布式，基于redis
- 支持平滑限流，说好100qps则就是0.01秒执行一次
- 基于redis的lua引擎，超过每秒10w次throttle请求会极大影响redis的常规性能

## 安装

```shell
pip install distlimiter
```

## 使用方法

```python
import time
import random
import threading
from statistics import mean, stdev
from distlimiter import throttle

starttimes = []


@throttle('add0',
          rate_per_second=100,
          method='smooth',
          redis_url='redis://localhost')
def add(a: int, b: int) -> int:
    starttimes.append(time.time())
    time.sleep(random.random() / 5)
    return a + b


tasks = []
for _ in range(11):
    t = threading.Thread(target=add, args=(1, 2), daemon=True)
    t.start()
    tasks.append(t)

for t in tasks:
    t.join()

intervals = [
    starttimes[i] - starttimes[i - 1] for i in range(1, len(starttimes))
]
print(intervals)
print(mean(intervals), stdev(intervals))
# [0.009971857070922852, 0.012664794921875, 0.007295131683349609, 0.01067209243774414, 0.009412765502929688, 0.013530254364013672, 0.0070078372955322266, 0.01360011100769043, 0.005474090576171875, 0.01084280014038086]
# 0.010047173500061036 0.002804029576649581
```

## Why?

分布式部署分布式任务的时候，比如用celery时，经常会发生任务限流不准的情况。

这是因为celery使用的限流方式比较不稳定，会产生大量的波峰波谷，有时对服务器造成了不必要的压力。

所以需要一个稳定平滑的，支持分布式系统的限流器。

## 实现原理

现有的限流算法大部分基于两种模式：令牌桶或者漏桶。无论哪种方式，运用在分布式环境下，都需要有个单独进程不断发放令牌，然后各个任务执行者去抢令牌。

这个模式依赖一个令牌产生器，从来又不够优雅，又不够scalable

distlimiter使用另一种方式，直接把限流管理放在redis里面，用lua脚本来执行。由于lua脚本执行的高效率和原子性，很好地保证了限流调度的有效性，配合throttle装饰器即可直接实现精确限流。