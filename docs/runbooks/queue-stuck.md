# Runbook: Job Queue Stuck

**Symptom:** Jobs remain in `queued` status for more than 10 minutes.

## Diagnosis

```bash
# Check Redis queue depth
redis-cli -u $REDIS_URL llen rq:queue:advocate

# Check running workers
redis-cli -u $REDIS_URL smembers rq:workers

# Check failed jobs
redis-cli -u $REDIS_URL lrange rq:queue:failed 0 -1
```

## Resolution

1. **No workers running** — restart worker containers:
   ```bash
   docker compose restart worker
   ```

2. **Redis unreachable** — check Redis health:
   ```bash
   docker compose ps redis
   redis-cli -u $REDIS_URL ping
   ```

3. **Worker crash loop** — check logs:
   ```bash
   docker compose logs worker --tail=100
   ```
   Common cause: bad Python dependency or import error.
   Fix: `pip install -r requirements.txt` and restart.

4. **Job in dead queue** — inspect and requeue:
   ```bash
   python -c "
   from redis import Redis; from rq import Queue
   conn = Redis.from_url('$REDIS_URL')
   dq = Queue('failed', connection=conn)
   for job in dq.jobs[:5]:
       print(job.id, job.exc_info)
   "
   ```

## Prevention

- Worker health check in docker-compose ensures auto-restart.
- `/ready` endpoint checks Redis connection.
- Alert on `job_queue_depth > 50` for more than 5 minutes in Prometheus.
