# Enterprise Operations Guide: Deployment Manuals & Incident Runbooks
This document provides production-ready deployment strategies, scalability architectures, and incident response procedures for operators of the Enterprise Ticketing Platform.

---

## 🌐 Production Architecture & Deployment

### 1. Zero-Downtime Blue-Green Strategy
To update the core Django container nodes in Kubernetes without interrupting concurrent booking operations:
1. **Build and Tag** new docker image versions via the GitHub Actions CI/CD pipeline.
2. **Apply Rolling Update**: EKS will launch new pods (`vNext`) and direct read/write readiness gates.
3. **Draining Connections**: Active WebSocket clients connected via daphne to older pods (`vCurrent`) are gracefully drained as the HAProxy ingress routes new sessions onto the new containers.

```
                  [ HAProxy / Nginx Ingress ]
                   /                       \
        [ Web Pods (vCurrent) ]     [ Web Pods (vNext) ]
           (Active Connections)        (Ready & Health checked)
                   |                           |
             [ Redis Cache ] <----------- [ PostgreSQL DB ]
```

### 2. Tuning Daphne & Nginx for WebSockets
WebSockets require open long-running TCP sockets. Default configurations must be tuned:
* **Host OS Limits (`/etc/security/limits.conf`)**:
  ```text
  * soft nofile 65535
  * hard nofile 65535
  ```
* **Nginx Configuration (`/etc/nginx/nginx.conf`)**:
  Ensure the reverse proxy passes connection upgrade headers correctly:
  ```nginx
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  ```

---

## 🛠️ PostgreSQL & Database Operations

### 1. High Availability Failover
The terraform module provisions an RDS instance with **Multi-AZ enabled**.
* **Automatic Recovery**: If the primary instance goes offline in availability zone `eu-west-3a`, AWS Route53 records automatically swap target endpoints to the synchronous backup replica in `eu-west-3b` within 60 seconds.
* **Force Manual Failover**:
  ```bash
  aws rds reboot-db-instance --db-instance-identifier ticket-platform-postgres --force-failover
  ```

### 2. Production Backups
The database runs automatic daily snapshot schedules. To trigger an ad-hoc logical backup:
```bash
pg_dump -h <db_host> -U django_admin -d ticket_db -F c -b -v -f /backups/ticket_db_$(date +%F).dump
```

---

## ⚙️ Redis & Celery Maintenance

### 1. Redis Cache Eviction Policy
Our Redis cluster operates both as a WebSockets backend (Channel Layer) and a transient store for cart-lock handles.
* **MANDATORY POLICY**: Use `volatile-lru` or `noeviction` to ensure active locked items are never silently evicted before their official 15-minute timeout.
* **Inspect Current Memory Size**:
  ```bash
  redis-cli -h <redis_host> info memory
  ```

### 2. Celery Worker Monitoring
Use `Flower` to gain live dashboards on task failures, execution queues, and worker load:
```bash
celery -A config flower --port=5555
```
Or check worker statuses via command line:
```bash
celery -A config inspect active
celery -A config inspect ping
```

---

## 🚨 Incident Response Runbooks

### Incident 1: Double Booking Alerts
* **Symptom**: Custom database exception or user-facing message warning `Transaction error / Optimistic Seat Lock failure`.
* **Root Cause**: Two buyers concurrently completed their order forms for the exact same seat within the same millisecond, and database locks did not coordinate with Redis cart states.
* **Immediate Remediation**:
  1. Verify if the seat in question has more than one confirmed `Ticket` model instance.
  2. Run audit trail queries in `/admin-dashboard/audit-logs/` to locate the target transaction histories.
  3. If double-booked, the system automatically tags the second transaction as `CANCELLED` and triggers an automatic Stripe/Mobile Money refund webhook.
  4. Ensure Redis is reachable and the keyspace event listener for cart timeouts is healthy.

### Incident 2: Redis Out of Memory (OOM)
* **Symptom**: Django logs indicate `OOM command not allowed when used memory > 'maxmemory'`. Live seat maps fail to lock.
* **Immediate Remediation**:
  1. Connect to the redis CLI and identify orphaned keys:
     ```bash
     redis-cli -h <redis_host> --bigkeys
     ```
  2. Identify if expired cart cleanups are stuck. Run a manual sweep task using Celery command line shell:
     ```bash
     python manage.py shell -c "from reservations.tasks import release_expired_carts_and_reservations; release_expired_carts_and_reservations()"
     ```
  3. If needed, temporarily scale up the ElastiCache node class via AWS console or Terraform variables.

### Incident 3: Celery Task Backlog Spikes
* **Symptom**: Expired carts are not being released, holding seats hostage long after their 15-minute timer has expired.
* **Immediate Remediation**:
  1. Inspect the backlog queue depth:
     ```bash
     redis-cli -h <redis_host> llen celery
     ```
  2. If the queue length > 10,000, spin up additional horizontal Celery worker pods in Kubernetes:
     ```bash
     kubectl scale deployment ticket-platform-celery-worker --replicas=5
     ```
  3. If corrupt tasks are infinite looping, purge the queue (Warning: will delete pending jobs; users may have to re-initiate payments):
     ```bash
     celery -A config purge -f
     ```
