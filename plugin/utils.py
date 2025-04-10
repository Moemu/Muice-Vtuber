import inspect
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from .typing import ASYNC_FUNCTION_CALL_FUNC, SYNC_FUNCTION_CALL_FUNC


def path_to_module_name(module_path: Path) -> str:
    """
    获取模块包名的方法
    """
    try:
        rel_path = module_path.resolve().relative_to(Path.cwd().resolve())
        return ".".join(rel_path.parts)
    except ValueError:
        # fallback: 从实际路径生成 module name（比如 muicebot.builtin_plugins.xxx）
        parts = module_path.resolve().parts
        if "muicebot" in parts:  # 这里假设 site-packages 中实际路径包含 'muicebot'，可以动态查找
            index = parts.index("muicebot")
            return ".".join(parts[index:])
        else:
            return module_path.stem  # fallback 最底线：用文件名作为模块名（不一定能 import 成功）


def is_coroutine_callable(call: Callable[..., Any]) -> bool:
    """
    检查 call 是否是一个 callable 协程函数
    """
    if inspect.isroutine(call):
        return inspect.iscoroutinefunction(call)
    if inspect.isclass(call):
        return False
    func_ = getattr(call, "__call__", None)
    return inspect.iscoroutinefunction(func_)


def async_wrap(func: SYNC_FUNCTION_CALL_FUNC) -> ASYNC_FUNCTION_CALL_FUNC:
    """
    装饰器，将同步函数包装为异步函数
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper
