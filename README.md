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
from distlimiter import throttle

@throttle('add0', rate_per_second=100, method='smooth', redis_url='redis://localhost')
def add(a: int, b: int) -> int:
    return a + b


t1 = time.time()
for _ in range(11):
    assert 3 == add(1, 2)
t2 = time.time()

# 放宽0.2秒，要给redis初始连接一点时间
assert 12 / 100 > t2 - t1 > 10 / 100, '限速100qps, 但11次连续请求在{:.6f}秒内完成'.format(t2 - t1)
```

## Why?

分布式部署分布式任务的时候，比如用celery时，经常会发生任务限流不准的情况。

这是因为celery使用的限流方式比较不稳定，会产生大量的波峰波谷，有时对服务器造成了不必要的压力。

所以需要一个稳定平滑的，支持分布式系统的限流器。

## 实现原理

现有的限流算法大部分基于两种模式：令牌桶或者漏桶。无论哪种方式，运用在分布式环境下，都需要有个单独进程不断发放令牌，然后各个任务执行者去抢令牌。

这个模式依赖一个令牌产生器，从来又不够优雅，又不够scalable

distlimiter使用另一种方式，直接把限流管理放在redis里面，用lua脚本来执行。由于lua脚本执行的高效率和原子性，很好地保证了限流调度的有效性，配合throttle装饰器即可直接实现精确限流。