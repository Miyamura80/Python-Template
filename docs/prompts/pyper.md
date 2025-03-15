# Pyper Parallelization


Let's suppose you have an original for loop that you want to parallelize.

```python
results = []
for data in data_list: # <-- NTOE: Assuming here no shared state, hence parallelization is safe
    s1 = f2(data)
    s2 = f3(s1)
    results.append(s2)

```


The main syntax is as follows:
```python
import asyncio
import time
from pyper import task

def get_data(data_list: list):
    for data in data_list:
        yield data # <-- NTOE: Make sure this is a yield statement

def f2(x: int):
    return x * 2 # <-- NTOE: These are okay to return


WORKERS = 10

pipeline = (
    task(data_generator, branch=True, bind=task.bind(x=x))
    | task(f2, workers=WORKERS)
    | task(f3, workers=WORKERS)
)

results = []
async for output in pipeline():
    results.append(output)
```

Note: 
- For `async for` to work, all the functions in the pipeline must be `async` functions.




## Sharp Cases

1. Multiple branches

```python
pipeline = (
    task(data_generator, branch=True, bind=True)
    | task(f2, workers=WORKERS)
    | task(f3, workers=WORKERS, branch=True)
)
```