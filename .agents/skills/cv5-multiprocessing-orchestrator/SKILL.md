---
name: cv5-multiprocessing-orchestrator
description: Dédié aux patterns d'exécution parallèle et de communication IPC sous OpenCV 5.0 DNN. Prévient les deadlocks de contexte et l'oversubscription CPU via `spawn` et `setNumThreads`.
---

# OpenCV 5.0 Multiprocessing Orchestrator

**TL;DR**: Multiprocessing with OpenCV 5.0 DNN requires the `spawn` context and strict thread limitations (`cv2.setNumThreads(1)`). Otherwise, you will encounter context deadlocks and CPU oversubscription.

## The Context Deadlock Problem

When you fork a Python process that has already initialized OpenCV (or CUDA contexts), the child inherits a corrupted state. OpenCV 5.0's thread pool is particularly sensitive to this. 

### ❌ The Default (Fork) Approach

```python
import multiprocessing as mp
import cv2

# Forking inherits the parent's potentially polluted OpenCV state
pool = mp.Pool(processes=4) 
```

### ✅ The Spawn Approach

```python
import multiprocessing as mp
import cv2

# Spawn creates a fresh Python interpreter for each worker
ctx = mp.get_context('spawn')
pool = ctx.Pool(processes=4)
```

## Preventing CPU Oversubscription

OpenCV defaults to using all available CPU cores for its internal operations. If you spawn 4 workers, and each worker tries to use 16 cores, you create 64 threads fighting for resources. This destroys performance.

You must explicitly throttle each worker's thread count immediately upon initialization:

```python
def worker_init():
    # Prevent OpenCV from spawning massive thread pools per worker
    cv2.setNumThreads(1)
```

## Clean IPC and UI Aggregation

Workers should never write directly to `stdout`. Concurrent `print` statements collide, creating unreadable logs and breaking terminal UIs. 

Instead, use a centralized `Queue` for Inter-Process Communication (IPC).

1. Workers serialize their state (progress, errors) using `orjson` and push to the queue.
2. The parent process reads the queue and aggregates the data.
3. The parent is solely responsible for rendering the multi-line UI (`[Progression-MultiLine]`).

This pattern cleanly separates the work from the reporting, ensuring robust terminal output even when tracking multiple video chunks simultaneously.
