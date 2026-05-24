import asyncio
import sys
from typing import List, Dict, Any, Optional
from app.db.supabase_client import get_client, execute_with_retry

class EventBatchWriter:
    """Buffers network event records in an async queue and batch-inserts them to Supabase.
    
    This prevents blocking the packet sniffing pipeline with individual database network calls
    (reducing network roundtrips up to 100x), allowing high sustained packet-per-second capture.
    """

    def __init__(self, batch_size: int = 100, flush_interval: float = 1.0):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def start(self) -> None:
        """Starts the background batch writer consumer task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._worker())
        print("[batch_writer] Background batch writer consumer task started.", file=sys.stderr)

    async def stop(self) -> None:
        """Stops the consumer and flushes all remaining events to the database."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[batch_writer] Error stopping background task: {e}", file=sys.stderr)
        
        # Safe flush of any leftover queue events
        await self._flush_remaining()
        print("[batch_writer] Background batch writer consumer task stopped and flushed.", file=sys.stderr)

    async def enqueue(self, event_row: Dict[str, Any]) -> None:
        """Adds a new event record to the insertion buffer."""
        await self.queue.put(event_row)

    async def _worker(self) -> None:
        """Background worker consuming events and performing batch inserts."""
        while self._running:
            try:
                batch = []
                start_time = asyncio.get_event_loop().time()

                # Await at least one item from the queue, or timeout
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=self.flush_interval)
                    batch.append(item)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    # No events arrived within flush_interval, loop again
                    pass

                # If we got at least one event, try to fill the batch up to batch_size
                if batch:
                    while len(batch) < self.batch_size:
                        time_spent = asyncio.get_event_loop().time() - start_time
                        time_left = self.flush_interval - time_spent
                        if time_left <= 0:
                            break
                        try:
                            # Non-blocking get of available items
                            item = self.queue.get_nowait()
                            batch.append(item)
                            self.queue.task_done()
                        except asyncio.QueueEmpty:
                            # Give other tasks a brief moment to run and queue more events
                            await asyncio.sleep(0.02)
                            continue

                # Perform the database batch insertion
                if batch:
                    await self._insert_batch(batch)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[batch_writer] Error in background consumer loop: {e}", file=sys.stderr)
                await asyncio.sleep(1.0)  # Throttled recovery backoff

    async def _insert_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Inserts a list of event dictionaries in a single query."""
        client = get_client()
        if client is None:
            return
        try:
            # Supabase client is sync (httpx blocking). Offload to thread pool so the
            # async worker loop keeps consuming the queue while the HTTP roundtrip runs.
            await asyncio.to_thread(
                execute_with_retry, lambda c: c.table("events").insert(batch)
            )
            print(f"[batch_writer] Successfully batch-inserted {len(batch)} events to Supabase.", file=sys.stderr)
        except Exception as e:
            print(f"[batch_writer] Failed to batch-insert {len(batch)} events to Supabase: {e}", file=sys.stderr)

    async def _flush_remaining(self) -> None:
        """Voids the remaining queue and writes leftovers before exit."""
        batch = []
        while not self.queue.empty():
            try:
                item = self.queue.get_nowait()
                batch.append(item)
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break
        if batch:
            await self._insert_batch(batch)
