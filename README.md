

```json
{
  "queues": [
    { "algorithm": "SRTF",   "time_slice": 1 },
    { "algorithm": "SRTF",   "time_slice": 2 },
    { "algorithm": "RR",   "time_slice": 4 },
    { "algorithm": "FCFS" }
  ]
}
```


```json
{
  "time_slices": [4, 8, 16, 100]
}
```

This is equivalent to:

```json
{
  "queues": [
    { "algorithm": "RR",   "time_slice": 4  },  
    { "algorithm": "RR",   "time_slice": 8  }, 
    { "algorithm": "RR",   "time_slice": 16 },
    { "algorithm": "FCFS" }                    
  ]
}
```
# cpu_scheduler
