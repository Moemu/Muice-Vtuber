from typing import Tuple, List
import tasks
from tasks import BaseTask
import random,asyncio
from threading import Thread
import logging

logger = logging.getLogger("Muice.queue")

class AsyncQueueThread(Thread):
    def __init__(self, pretreat_queue: "PretreatQueue"):
        super().__init__(daemon=True)
        self.pretreat_queue = pretreat_queue

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.pretreat_queue.run_forever())


class PretreatQueue:
    """
    预处理队列
    """
    def __init__(self ,first_run=True) -> None:
        self._queue = asyncio.PriorityQueue(maxsize=7)
        self.post_queue = PostProcessQueue()

        self.DECAY_FACTOR = 0.5
        """每事件衰减因子（每轮处理后添加多少优先数）"""
        self.MAX_PRIORITY = 15
        """最大优先数限制，等于或大于此优先数的任务将被丢弃"""

        self.is_running = False
        self.idle_time = 0
        self.first_run = first_run

    async def _queue_get(self) -> Tuple[float, BaseTask]:
        return await self._queue.get()
    
    async def _queue_put(self, priority:float, task: BaseTask):
        await self._queue.put((priority, task))

    def _merge_tasks(self, queue_items:List[Tuple[float, BaseTask]]) -> List[Tuple[float, BaseTask]]:
        """
        合并队列中来自相同用户的任务

        请注意: tasks必须是已按时间顺序排序的
        """
        if len(queue_items) < 2:
            return queue_items

        merged_tasks:List[Tuple[float, BaseTask]] = [queue_items[0]]

        for prioritiy, task in queue_items[1:]:
            last_priority, last_task = merged_tasks[-1]
            if task.data.userid == last_task.data.userid:
                # 合并到上一个任务中（顺序保证前小于后）
                merged_task = last_task + task
                merged_tasks[-1] = (last_priority, merged_task)
                logger.debug(f"合并任务 {last_task} + {task}")
            else:
                # 不同用户，直接加入列表
                merged_tasks.append((prioritiy, task))

        return merged_tasks

    async def _process_queue(self) -> List[Tuple[float, BaseTask]]:
        """
        获取队列内容并过滤优先级超过阈值的任务
        """
        # current_time = time.time()
        queue_items:List[Tuple[float, BaseTask]] = []
        
        while not self._queue.empty():
            priority, task = await self._queue_get()
            # priority += self.DECAY_FACTOR

            # 动态优先级过滤
            if priority >= self.MAX_PRIORITY:
                logger.warning(f"任务 {task} 被过滤(动态优先级={priority:.1f})")
                continue

            queue_items.append((priority, task))

        queue_items = self._merge_tasks(queue_items)
        
        return queue_items

    def get_priority_snapshot(self):
        """
        观察目前的队列情况
        """
        snapshot = list(self._queue._queue)  # type:ignore
        logger.debug([(item[0], item[1]) for item in snapshot])
    
    async def _get_a_leisure_task(self):
        """
        尝试发布一个空闲任务
        """
        self.idle_time += 0.5
        if self.idle_time >= 50 and random.random() < 0.05:
            # 5% 概率决定任务类型
            if random.random() < 0.05:
                logger.info('发布一个读屏任务...')
                await self.__create_a_read_screen_task()
            else:
                logger.info('发布一个闲时任务...')
                await self.__create_a_leisure_task()

            self.idle_time = 0  # 重置空闲时间

    async def __run(self):
        """任务处理主循环"""
        self.is_running = True

        while self.is_running:
            await asyncio.sleep(0.5)

            # 当主处理队列已满时，应继续等待
            if self.post_queue.is_queue_full:
                continue

            # 当队列为空时，尝试生成闲时任务
            if self._queue.empty():
                await self._get_a_leisure_task()
                continue

            # 动态优先级算法
            # 1. 取出所有任务，计算动态优先级并过滤优先数较大的任务
            if not (items := await self._process_queue()):
                continue

            # 2. 按动态优先级排序
            items.sort(key=lambda x: (x[0], x[1]))

            # 3. 处理最高优先级任务
            priority, task = items[0]

            try:
                logger.info(f"执行任务: {task} (动态优先级={priority})")
                await task.pretreatment()
                await self.post_queue.put(priority, task)
                await asyncio.sleep(3)  # CD 缓冲
            except Exception as e:
                logger.error(f"任务执行失败: {e}", exc_info=True)

            # 4. 将剩余任务重新入队（保持原始格式）
            for item in items[1:]:
                await self._queue_put(item[0], item[1])

            self.idle_time = 0

    async def run_forever(self):
        """主运行循环（提供给线程运行）"""
        self.is_running = True
        await self.post_queue.start_async()  # 改为 await 启动
        await self.__run()

    async def put(self, priority: int, task: BaseTask):
        """入队方法"""
        if not self._queue.full():
            await self._queue_put(priority, task)
            logger.debug(f"入队成功: {task} (优先级={priority})")
            return

        # 队列已满时的替换策略
        # 1. 取出所有任务，计算动态优先级并过滤优先数较大的任务
        queue_items = await self._process_queue()

        # 2. 添加新任务到临时列表
        queue_items.append((priority, task))

        # 3. 按动态优先级排序（优先级数值越小、时间越晚越优先）
        queue_items.sort(key=lambda x: (x[0], -x[1].time))

        # 4. 抛弃优先级数值最大、时间最早的事件
        queue_items.pop()

        logger.debug(f"队列满处理后状态:\n{self.get_priority_snapshot()}")

    def start(self):
        if self.is_running:
            logger.info('事件队列已在运行中')
            return False
        if not self.first_run:
            self.__init__(False)
        self.is_running = True

        # 启动后台线程，运行事件队列
        AsyncQueueThread(self).start()

        logger.info('事件队列已启动')
        return True

        
    def stop(self):
        self.is_running = False
        self.first_run = False
        self.post_queue.is_running = False
        logger.info('事件队列已停止')

    async def __create_a_leisure_task(self):
        """
        发布一个闲时任务
        """
        await self.put(10, tasks.LeisureTask())

    async def __create_a_read_screen_task(self):
        """
        发布了一个读屏任务
        """
        await self.put(10, tasks.ReadScreenTask())

class PostProcessQueue:
    """
    正式处理队列
    """
    def __init__(self) -> None:
        self._queue = asyncio.PriorityQueue(maxsize=1)  # 队列长度1
        self.is_running = False
        self.is_task_running = False

    async def _queue_get(self) -> Tuple[float, BaseTask]:
        return await self._queue.get()
    
    async def _queue_put(self, priority:float, task: BaseTask):
        await self._queue.put((priority, task))
    
    @property
    def is_queue_full(self) -> bool:
        return self._queue.full()

    async def __run(self):
        """主处理循环"""
        self.is_running = True
        while self.is_running:
            if self._queue.empty():
                await asyncio.sleep(0.5)
                continue

            self.is_task_running = True

            try:
                priority, task = await self._queue_get()
                logger.info(f"正式处理任务: {task}")
                await task.post_response()
            except Exception as e:
                logger.error(f"正式处理失败: {e}", exc_info=True)
            
            self.is_task_running = False

    async def put(self, priority: float, task:BaseTask):
        """入队方法"""        
        if self._queue.full():
            # 队列满时直接替换
            old_task = await self._queue_get()
            logger.warning(f"正式队列替换旧任务: {old_task[1]} → {task}")
        
        await self._queue_put(priority, task)

    async def start_async(self):
        """提供异步启动方法，供 PretreatQueue 调用"""
        if self.is_running:
            return
        self.is_running = True
        asyncio.create_task(self.__run())

    def stop(self):
        self.is_running = False

