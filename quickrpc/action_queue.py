'''ActionQueue: a background worker that manages its own worker thread automatically.'''
from threading import Thread, Lock, Event
from queue import Queue, Empty

__all__ = [
    'ActionQueue',
    ]

class ActionQueue:
    '''A background worker that manages its own worker thread automatically.

    Enqueue work items using .put(). Work items are functions that do not
    take any parameters and return None.

    .put() returns immediately. The work items are processed in a background
    thread, in the order in which they arrived. Only one work item is processed
    at a time.

    The background thread is started when there is work to do, and teared down
    when the queue is empty.
    '''

    def __init__(self):
        self._queue = Queue()
        self._thread = None
        self._running = Event()
        self._startstop_lock = Lock()

    def put(self, action):
        '''Put an action into the queue.

        Parameters:
            action (func): a callable without params. The return value is not used.
        '''
        with self._startstop_lock:
            self._queue.put(action)
            if not self._running.is_set():
                self._thread = Thread(target=self._run_worker, name='ActionQueue')
                self._thread.start()
                self._running.wait()

    def _run_worker(self):
        self._running.set()
        while True:
            with self._startstop_lock:
                try:
                    action = self._queue.get_nowait()
                except Empty:
                    self._running.clear()
                    return
            action()

