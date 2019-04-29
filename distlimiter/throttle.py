# coding: utf-8
""" 限速器 """
import time
import redis
import logging
import functools
from .lua import get_throttle_script

logger = logging.getLogger('distlimiter')


class Throttler:
    """ 限速器 """

    def __init__(self, redis_url: str, key: str):
        self._redis_url = redis_url
        self._key = key
        self._client = redis.Redis.from_url(redis_url)
        self._delay = self.estimate_delay()

    def throttle(self, rate_per_second: float):
        raise RuntimeError('应该在子类中继承实现这个方法')

    def estimate_delay(self, num_rounds: int = 10):
        """ 估算redis和本机之间的网络延迟 """
        # 先建立连接
        self._client.ping()

        t1 = time.time()
        for _ in range(num_rounds):
            self._client.ping()
        t2 = time.time()
        return (t2 - t1) / num_rounds


class SmoothThrottler(Throttler):
    """ 平滑的限速器 
    
    限速100/s == 每隔0.01秒做一个任务
    """

    def throttle(self, rate_per_second: float):
        script_info = get_throttle_script()
        try:
            us_to_sleep = self._client.evalsha(script_info['sha1'], 1,
                                               self._key, rate_per_second)
        except redis.exceptions.NoScriptError:
            sha1 = self._client.script_load(script_info['script'])
            us_to_sleep = self._client.evalsha(sha1, 1, self._key,
                                               rate_per_second)

        # 需要减掉和redis通信所花的网络延迟
        second_to_sleep = us_to_sleep / 1000000. - self._delay
        if second_to_sleep > 0:
            logger.debug('触发限速, 等待{:.6f}秒'.format(second_to_sleep))
            time.sleep(second_to_sleep)


def throttle(key: str,
             rate_per_second: float,
             method: str = 'smooth',
             redis_url: str = 'redis://localhost:6379/0'):
    """ 按key以rate_per_second的要求来平滑限速
    
    :param key: 限速的key
    :param rate_per_second: 每秒钟限速个数
    :param method: 限速方式, 目前可以用 'smooth'
    :param redis_url: redis://[:password@]host[:port][/database]
    """
    throttler_class = {'smooth': SmoothThrottler}.get(method)
    if not throttler_class:
        raise NotImplementedError('限速方式{}未定义'.format(method))
    throttler = throttler_class(redis_url=redis_url, key=key)

    def outer(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            throttler.throttle(rate_per_second=rate_per_second)
            return func(*args, **kwargs)

        return inner

    return outer
