import time


def timed_function(f):
    def new_func(*args, **kwargs):
        t = time.ticks_us()
        result = f(*args, **kwargs)
        delta = time.ticks_diff(time.ticks_us(), t)
        print(f"Function {f.__name__} Time = {delta/1000:.3f}ms")
        return result

    return new_func
