# coding: utf-8
""" Redis中的Lua脚本 """
import hashlib
from textwrap import dedent


def get_throttle_script() -> dict:
    """ 用于真正限流的lua脚本 
    
    docs: https://redis.io/commands/eval

    EVAL script numkeys key [key ...] arg [arg ...]
    """
    script = dedent("""
        local function time1m(t)
            return t[1] * 1000000 + t[2]
        end

        local tskey = "distlimiter_microsecond_" .. KEYS[1]
        local timestamp = redis.call('GET', tskey)
        local rate_per_second = ARGV[1]
        local interval = 1000000 / rate_per_second
        local curr_timestamp, next_timestamp

        curr_timestamp = time1m(redis.call('TIME'))
        if (not timestamp) then
            -- 还未有上次执行内容, 直接放行
            next_timestamp = curr_timestamp
        else
            -- 已经有上次执行时间了
            if (timestamp + interval < curr_timestamp) then
                -- 如果是很久以前限速的
                next_timestamp = curr_timestamp
            else
                -- 如果当前无法立刻执行的，排一下队
                next_timestamp = timestamp + interval
            end
        end
        redis.call('SET', tskey, next_timestamp)
        return next_timestamp - curr_timestamp
    """)
    sha1 = hashlib.sha1(script.encode('utf-8')).hexdigest()
    return dict(script=script, sha1=sha1)