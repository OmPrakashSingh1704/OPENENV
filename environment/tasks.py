"""
Task definitions and incident datasets for the SRE Incident Response OpenEnv.

Each task contains a list of incidents with ground-truth labels used by graders.
Tasks progress from easy (root cause only) → medium (root cause + severity + remediation)
→ hard (full incident response + postmortem write-up)
→ reproduce (root cause + step-by-step failure reproduction instructions).
"""

TASKS: dict = {
    "easy": {
        "id": "easy",
        "name": "Incident Root Cause Classification",
        "description": (
            "Analyse each production incident and identify the root cause. "
            "Valid root causes: out_of_memory | disk_full | service_crash | "
            "config_error | network_timeout | dependency_failure | traffic_spike | "
            "deployment_failure | resource_leak | certificate_expired. "
            "Set severity=p3, remediation=investigate, postmortem_summary=null."
        ),
        "difficulty": "easy",
        "max_steps": 10,
        "incidents": [
            {
                "incident_id": "easy_001",
                "service_name": "checkout-service",
                "alert_title": "CRITICAL: checkout-service OOMKilled — pod restarting",
                "alert_description": (
                    "Pod checkout-service-7d9f4b-xkp2q was OOMKilled and restarted 4 times in the last 15 minutes. "
                    "Container limit is 512Mi. Memory usage reached 511Mi before kill."
                ),
                "error_logs": (
                    "[2026-03-15 02:14:33] FATAL: Allocating 524288000 bytes failed\n"
                    "[2026-03-15 02:14:33] java.lang.OutOfMemoryError: Java heap space\n"
                    "[2026-03-15 02:14:33]   at java.util.Arrays.copyOf(Arrays.java:3210)\n"
                    "[2026-03-15 02:14:33] Killed\n"
                    "[2026-03-15 02:14:45] Container checkout-service restarted (exit code 137)"
                ),
                "metrics": {
                    "memory_usage": "511Mi / 512Mi (99.8%)",
                    "cpu_usage": "340m / 500m (68%)",
                    "pod_restarts": "4 in last 15min",
                    "heap_used": "498Mi",
                },
                "recent_changes": "No deployments in last 48 hours. Promotions campaign started 3 hours ago.",
                "on_call_notes": "This service handles payment processing. SLA: 99.9% uptime.",
                "ground_truth": {
                    "root_cause": "out_of_memory",
                    "severity": "p1",
                    "remediation": "restart_service",
                },
            },
            {
                "incident_id": "easy_002",
                "service_name": "postgres-primary",
                "alert_title": "CRITICAL: Disk usage at 98% on postgres-primary",
                "alert_description": (
                    "Filesystem /var/lib/postgresql on postgres-primary is at 98% capacity. "
                    "Write operations are beginning to fail. Database will go read-only above 99%."
                ),
                "error_logs": (
                    "[2026-03-15 08:22:10] ERROR: could not write to file 'pg_wal/00000001000000000000001F': "
                    "No space left on device\n"
                    "[2026-03-15 08:22:10] LOG: database system is shut down\n"
                    "[2026-03-15 08:22:11] FATAL: pre-existing shared memory block is still in use\n"
                    "[2026-03-15 08:22:15] ERROR: disk full — writes rejected"
                ),
                "metrics": {
                    "disk_usage": "98.2% (490GB / 500GB)",
                    "wal_size": "42GB",
                    "table_bloat": "~15GB estimated",
                    "write_errors_per_min": "47",
                },
                "recent_changes": "WAL archiving was disabled 2 weeks ago for 'performance testing'. Not re-enabled.",
                "on_call_notes": "Postgres primary for user-profile service. Replica lag is 0ms — replica is healthy.",
                "ground_truth": {
                    "root_cause": "disk_full",
                    "severity": "p1",
                    "remediation": "clear_disk",
                },
            },
            {
                "incident_id": "easy_003",
                "service_name": "api-gateway",
                "alert_title": "DOWN: api-gateway process not responding",
                "alert_description": (
                    "api-gateway health check has been failing for 5 minutes. "
                    "Process is not found in the process list. Port 8080 is not listening."
                ),
                "error_logs": (
                    "[2026-03-15 11:05:02] ERROR: Unhandled rejection: Cannot read properties of undefined "
                    "(reading 'headers')\n"
                    "[2026-03-15 11:05:02] at Router.handle (/app/node_modules/express/lib/router/index.js:284)\n"
                    "[2026-03-15 11:05:02] Process exited with code 1\n"
                    "[2026-03-15 11:05:02] Supervisor: api-gateway stopped unexpectedly, not restarting (max_retries=0)"
                ),
                "metrics": {
                    "uptime": "0s (process down)",
                    "last_healthy": "5 minutes ago",
                    "requests_dropped": "~1200/min",
                    "port_8080_listening": "false",
                },
                "recent_changes": "Node.js version upgraded from 18 to 20 in this morning's maintenance window.",
                "on_call_notes": "All external traffic routes through api-gateway. Complete outage if down.",
                "ground_truth": {
                    "root_cause": "service_crash",
                    "severity": "p1",
                    "remediation": "restart_service",
                },
            },
            {
                "incident_id": "easy_004",
                "service_name": "notification-service",
                "alert_title": "ERROR: notification-service connecting to wrong database",
                "alert_description": (
                    "notification-service is throwing database connection errors. "
                    "Logs show it is attempting to connect to 'db-staging.internal' instead of 'db-prod.internal'."
                ),
                "error_logs": (
                    "[2026-03-15 14:33:21] ERROR: Connection refused: db-staging.internal:5432\n"
                    "[2026-03-15 14:33:21] ERROR: FATAL: password authentication failed for user 'notif_prod'\n"
                    "[2026-03-15 14:33:25] WARN: Retrying DB connection (attempt 3/5)\n"
                    "[2026-03-15 14:33:35] ERROR: All DB connection attempts failed — service degraded"
                ),
                "metrics": {
                    "db_connection_success_rate": "0%",
                    "emails_queued": "14,232 (undelivered)",
                    "error_rate": "100%",
                    "service_uptime": "Process running but non-functional",
                },
                "recent_changes": "New environment-variable secret was deployed 30 minutes ago. "
                    "Staging DB_HOST value was accidentally used in the prod secret.",
                "on_call_notes": "Push notifications and email delivery depend on this service.",
                "ground_truth": {
                    "root_cause": "config_error",
                    "severity": "p2",
                    "remediation": "fix_config",
                },
            },
            {
                "incident_id": "easy_005",
                "service_name": "payment-processor",
                "alert_title": "HIGH: payment-processor 60% timeout rate to Stripe API",
                "alert_description": (
                    "Payment processor is experiencing 60% timeout rate when calling Stripe's API. "
                    "Requests are timing out after 30 seconds. Stripe status page shows no incidents."
                ),
                "error_logs": (
                    "[2026-03-15 16:44:01] WARN: Stripe API call timed out after 30000ms (attempt 1/3)\n"
                    "[2026-03-15 16:44:31] WARN: Stripe API call timed out after 30000ms (attempt 2/3)\n"
                    "[2026-03-15 16:44:31] ERROR: All Stripe API retries exhausted — payment failed\n"
                    "[2026-03-15 16:44:33] ERROR: connect ETIMEDOUT 54.187.201.204:443"
                ),
                "metrics": {
                    "stripe_timeout_rate": "60%",
                    "avg_response_time": "28,400ms (timeouts)",
                    "successful_payments": "40% of attempts",
                    "network_packet_loss": "12% on egress",
                },
                "recent_changes": "Network team updated firewall rules 2 hours ago for PCI compliance.",
                "on_call_notes": "Revenue impact ~$3,400/min. Network team is on standby.",
                "ground_truth": {
                    "root_cause": "network_timeout",
                    "severity": "p1",
                    "remediation": "investigate",
                },
            },
            {
                "incident_id": "easy_006",
                "service_name": "user-service",
                "alert_title": "CRITICAL: user-service cannot connect to Redis cache",
                "alert_description": (
                    "user-service is failing all session lookups because Redis cluster is unreachable. "
                    "All authenticated requests are returning 401. Redis sentinel reports master is down."
                ),
                "error_logs": (
                    "[2026-03-15 19:12:44] ERROR: Redis connection error: connect ECONNREFUSED 10.0.1.45:6379\n"
                    "[2026-03-15 19:12:44] ERROR: Session lookup failed for user_id=8821 — Redis unavailable\n"
                    "[2026-03-15 19:12:45] WARN: Falling back to DB session lookup (high load risk)\n"
                    "[2026-03-15 19:12:55] ERROR: DB overloaded — session fallback failing too"
                ),
                "metrics": {
                    "redis_status": "DOWN (master + 1 replica)",
                    "auth_success_rate": "0%",
                    "db_connections": "498/500 (at limit)",
                    "active_user_sessions_lost": "~42,000",
                },
                "recent_changes": "Redis cluster upgraded from 6.2 to 7.0 yesterday. Rollback not yet tested.",
                "on_call_notes": "Redis team is paged. All users are effectively logged out.",
                "ground_truth": {
                    "root_cause": "dependency_failure",
                    "severity": "p1",
                    "remediation": "failover",
                },
            },
            {
                "incident_id": "easy_007",
                "service_name": "product-search",
                "alert_title": "HIGH: product-search latency 10x normal — traffic spike detected",
                "alert_description": (
                    "product-search is experiencing 10x normal request volume following a viral social media post. "
                    "P99 latency has gone from 120ms to 4,800ms. Auto-scaling is at max capacity."
                ),
                "error_logs": (
                    "[2026-03-15 20:05:11] WARN: Request queue depth: 8,421 (threshold: 500)\n"
                    "[2026-03-15 20:05:12] WARN: Worker pool exhausted — requests being queued\n"
                    "[2026-03-15 20:05:15] ERROR: Request timeout after 5000ms — circuit breaker open\n"
                    "[2026-03-15 20:05:20] INFO: Auto-scaler at max replicas (20/20)"
                ),
                "metrics": {
                    "requests_per_second": "12,400 (normal: 1,240)",
                    "p99_latency": "4,800ms (normal: 120ms)",
                    "pod_count": "20/20 (at limit)",
                    "error_rate": "23%",
                },
                "recent_changes": "Product featured on a popular YouTube channel 45 minutes ago.",
                "on_call_notes": "This is purely load-driven — no code changes. Need capacity decision.",
                "ground_truth": {
                    "root_cause": "traffic_spike",
                    "severity": "p2",
                    "remediation": "scale_up",
                },
            },
            {
                "incident_id": "easy_008",
                "service_name": "recommendation-engine",
                "alert_title": "CRITICAL: recommendation-engine error rate 95% after deployment",
                "alert_description": (
                    "recommendation-engine v2.4.1 was deployed 20 minutes ago. "
                    "Error rate immediately jumped from 0.1% to 95%. "
                    "Deployment pipeline shows green but runtime is failing."
                ),
                "error_logs": (
                    "[2026-03-15 22:18:03] ERROR: AttributeError: 'NoneType' object has no attribute 'predict'\n"
                    "[2026-03-15 22:18:03]   File '/app/recommender.py', line 142, in get_recommendations\n"
                    "[2026-03-15 22:18:03]     scores = self.model.predict(features)\n"
                    "[2026-03-15 22:18:03] ERROR: Model file not found: /models/v2.4.1/recommender.pkl\n"
                    "[2026-03-15 22:18:04] FATAL: 950 errors in last 60 seconds"
                ),
                "metrics": {
                    "error_rate": "95.2%",
                    "deployment_version": "v2.4.1 (deployed 20min ago)",
                    "previous_version": "v2.4.0 (last known good)",
                    "affected_users": "~38,000/min",
                },
                "recent_changes": "v2.4.1 deployed at 22:00 UTC. Changed model loading path. "
                    "Model file was not included in the container image.",
                "on_call_notes": "Quick rollback to v2.4.0 is available. Recommend immediate action.",
                "ground_truth": {
                    "root_cause": "deployment_failure",
                    "severity": "p1",
                    "remediation": "rollback_deployment",
                },
            },
            {
                "incident_id": "easy_009",
                "service_name": "analytics-collector",
                "alert_title": "HIGH: analytics-collector memory growing 50MB/hour — resource leak",
                "alert_description": (
                    "analytics-collector memory has been steadily growing since last Tuesday. "
                    "Started at 180MB RSS, now at 2.1GB. No OOMKill yet but trending toward container limit (4GB)."
                ),
                "error_logs": (
                    "[2026-03-15 09:01:44] WARN: Event buffer size: 1,842,110 (expected max: 10,000)\n"
                    "[2026-03-15 09:02:01] WARN: Goroutine count: 48,221 (started: 42)\n"
                    "[2026-03-15 09:02:15] WARN: Memory RSS: 2,143MB and growing\n"
                    "[2026-03-15 10:15:33] WARN: GC pause >500ms — heap thrashing"
                ),
                "metrics": {
                    "memory_rss": "2,143MB (started at 180MB, 6 days ago)",
                    "goroutine_count": "48,221",
                    "event_buffer_depth": "1,842,110 unconsumed events",
                    "memory_growth_rate": "~50MB/hour",
                },
                "recent_changes": "v3.1.0 deployed 6 days ago — added new event type for A/B tracking. "
                    "Introduced a channel that is written to but never consumed.",
                "on_call_notes": "Not urgent yet but will OOMKill in ~38 hours at current rate.",
                "ground_truth": {
                    "root_cause": "resource_leak",
                    "severity": "p3",
                    "remediation": "restart_service",
                },
            },
            {
                "incident_id": "easy_010",
                "service_name": "auth-service",
                "alert_title": "CRITICAL: SSL certificate expired — auth-service HTTPS broken",
                "alert_description": (
                    "auth-service TLS certificate expired at 00:00 UTC today. "
                    "All HTTPS connections are being rejected with SSL_ERROR_RX_RECORD_TOO_LONG. "
                    "Mobile apps cannot authenticate."
                ),
                "error_logs": (
                    "[2026-03-15 00:00:01] ERROR: SSL_CTX_use_certificate: certificate has expired\n"
                    "[2026-03-15 00:00:01] ERROR: TLS handshake failed: certificate expired (notAfter=Mar 15 00:00:00 2026)\n"
                    "[2026-03-15 00:00:02] WARN: Falling back to HTTP on port 80 (insecure)\n"
                    "[2026-03-15 00:01:44] ERROR: 18,420 SSL handshake failures in last 60 seconds"
                ),
                "metrics": {
                    "cert_expiry": "Expired 2026-03-15 00:00:00 UTC (today)",
                    "https_success_rate": "0%",
                    "http_fallback_active": "yes (insecure)",
                    "mobile_auth_failures": "18,420/min",
                },
                "recent_changes": "Certificate renewal was scheduled but the Let's Encrypt ACME bot failed silently "
                    "14 days ago. No alert was configured for renewal failure.",
                "on_call_notes": "HTTP fallback is active but insecure. Must renew cert immediately.",
                "ground_truth": {
                    "root_cause": "certificate_expired",
                    "severity": "p1",
                    "remediation": "renew_certificate",
                },
            },
        ],
    },

    "medium": {
        "id": "medium",
        "name": "Incident Triage and Response Planning",
        "description": (
            "Analyse each production incident and provide: root cause, severity level, "
            "and the immediate remediation action. "
            "root_cause: out_of_memory | disk_full | service_crash | config_error | "
            "network_timeout | dependency_failure | traffic_spike | deployment_failure | "
            "resource_leak | certificate_expired. "
            "severity: p1 (total outage) | p2 (major degradation) | p3 (partial impact) | p4 (minor/no user impact). "
            "remediation: restart_service | rollback_deployment | scale_up | clear_disk | fix_config | "
            "block_traffic | failover | renew_certificate | investigate | add_resources. "
            "Set postmortem_summary=null."
        ),
        "difficulty": "medium",
        "max_steps": 10,
        "incidents": [
            {
                "incident_id": "medium_001",
                "service_name": "order-service",
                "alert_title": "CRITICAL: order-service OOMKilled — 100% order failure rate",
                "alert_description": (
                    "order-service pods are being OOMKilled continuously. "
                    "All new orders are failing. Revenue impact is confirmed."
                ),
                "error_logs": (
                    "[2026-03-20 03:11:05] java.lang.OutOfMemoryError: GC overhead limit exceeded\n"
                    "[2026-03-20 03:11:05] Killed (OOMKilled, exit code 137)\n"
                    "[2026-03-20 03:11:07] Pod order-service-abc123 restarted (4th time)\n"
                    "[2026-03-20 03:11:07] CrashLoopBackOff — waiting 5m before next restart"
                ),
                "metrics": {
                    "order_success_rate": "0%",
                    "pod_memory": "2048Mi / 2048Mi (100%)",
                    "pod_restarts": "4 (CrashLoopBackOff)",
                    "orders_failed_last_10min": "8,421",
                },
                "recent_changes": "Memory limit doubled last week from 1GB to 2GB but heap not tuned.",
                "on_call_notes": "P1 — complete order outage. Restart with -Xmx1800m JVM flag may help short-term.",
                "ground_truth": {
                    "root_cause": "out_of_memory",
                    "severity": "p1",
                    "remediation": "restart_service",
                },
            },
            {
                "incident_id": "medium_002",
                "service_name": "log-aggregator",
                "alert_title": "HIGH: log-aggregator disk 97% full — writes failing",
                "alert_description": (
                    "Log aggregator disk is 97% full. New log writes are failing. "
                    "Old logs are not being rotated — log rotation cron job stopped."
                ),
                "error_logs": (
                    "[2026-03-20 07:30:12] ERROR: write /var/log/app.log: no space left on device\n"
                    "[2026-03-20 07:30:12] WARN: Log rotation job last ran: 6 days ago\n"
                    "[2026-03-20 07:30:14] ERROR: Elasticsearch indexing failed — disk quota exceeded\n"
                    "[2026-03-20 07:30:20] WARN: Dropping 2,400 log lines/sec — buffer full"
                ),
                "metrics": {
                    "disk_usage": "97.4% (973GB / 1000GB)",
                    "log_rotation_last_run": "6 days ago",
                    "logs_dropped_per_sec": "2,400",
                    "oldest_unrotated_log": "6 days old, 280GB",
                },
                "recent_changes": "logrotate cron job disabled accidentally when crontab was edited 6 days ago.",
                "on_call_notes": "Observability is degraded but services still running. Re-enable logrotate + clear old logs.",
                "ground_truth": {
                    "root_cause": "disk_full",
                    "severity": "p2",
                    "remediation": "clear_disk",
                },
            },
            {
                "incident_id": "medium_003",
                "service_name": "inventory-service",
                "alert_title": "CRITICAL: inventory-service down — segfault in native library",
                "alert_description": (
                    "inventory-service crashed with SIGSEGV in a native C extension. "
                    "Process is down and supervisor is not auto-restarting (max retries reached)."
                ),
                "error_logs": (
                    "[2026-03-20 10:55:33] Segmentation fault (core dumped)\n"
                    "[2026-03-20 10:55:33] Process received signal SIGSEGV at address 0x00007f8b4c001a20\n"
                    "[2026-03-20 10:55:34] Supervisor: inventory-service exited (signal 11)\n"
                    "[2026-03-20 10:55:34] Supervisor: max retries (5) reached — giving up"
                ),
                "metrics": {
                    "service_status": "DOWN",
                    "uptime": "0s",
                    "last_healthy": "22 minutes ago",
                    "inventory_reads_failing": "100%",
                },
                "recent_changes": "Updated libprotobuf from 3.19 to 3.25 in yesterday's dependency update.",
                "on_call_notes": "Inventory reads block checkout. Major revenue impact. Rollback of libprotobuf is one option.",
                "ground_truth": {
                    "root_cause": "service_crash",
                    "severity": "p1",
                    "remediation": "rollback_deployment",
                },
            },
            {
                "incident_id": "medium_004",
                "service_name": "email-sender",
                "alert_title": "MEDIUM: email-sender using wrong SMTP credentials",
                "alert_description": (
                    "email-sender is failing to authenticate to the SMTP relay. "
                    "Transactional emails are queuing up. No emails sent in 2 hours."
                ),
                "error_logs": (
                    "[2026-03-20 13:04:55] ERROR: SMTP AUTH failed: 535 Authentication credentials invalid\n"
                    "[2026-03-20 13:04:55] ERROR: SMTP_PASSWORD env var may be incorrect or rotated\n"
                    "[2026-03-20 13:04:58] WARN: Email queue depth: 48,200 and growing at 400/min\n"
                    "[2026-03-20 13:05:10] WARN: Password was rotated in secrets manager 2h ago"
                ),
                "metrics": {
                    "smtp_auth_success_rate": "0%",
                    "email_queue_depth": "48,200",
                    "queue_growth_rate": "400 emails/min",
                    "last_successful_send": "2 hours ago",
                },
                "recent_changes": "SMTP credentials rotated in AWS Secrets Manager 2 hours ago. "
                    "email-sender was not restarted to pick up the new secret.",
                "on_call_notes": "No user-visible errors yet (emails pending). Must fix before queue overflows.",
                "ground_truth": {
                    "root_cause": "config_error",
                    "severity": "p3",
                    "remediation": "fix_config",
                },
            },
            {
                "incident_id": "medium_005",
                "service_name": "shipping-service",
                "alert_title": "HIGH: shipping-service 80% timeout rate to FedEx API",
                "alert_description": (
                    "shipping-service is timing out on 80% of calls to FedEx label API. "
                    "Order fulfillment is severely impacted."
                ),
                "error_logs": (
                    "[2026-03-20 15:21:44] WARN: FedEx API call timeout after 10000ms\n"
                    "[2026-03-20 15:21:44] ERROR: Unable to generate shipping label for order ORD-88234\n"
                    "[2026-03-20 15:21:50] ERROR: DNS resolution timeout for api.fedex.com (5000ms)\n"
                    "[2026-03-20 15:22:01] WARN: traceroute shows packet loss after hop 8 (ISP boundary)"
                ),
                "metrics": {
                    "fedex_timeout_rate": "80%",
                    "dns_resolution_failures": "65%",
                    "label_generation_success": "20%",
                    "traceroute_packet_loss_hop8": "78%",
                },
                "recent_changes": "ISP maintenance window was scheduled for today 15:00–17:00 UTC.",
                "on_call_notes": "External ISP issue likely. Cannot fix network ourselves — need to investigate scope.",
                "ground_truth": {
                    "root_cause": "network_timeout",
                    "severity": "p2",
                    "remediation": "investigate",
                },
            },
            {
                "incident_id": "medium_006",
                "service_name": "content-delivery",
                "alert_title": "CRITICAL: content-delivery PostgreSQL replica unreachable",
                "alert_description": (
                    "content-delivery service lost connection to read replica. "
                    "All read queries are failing over to primary, which is now overloaded."
                ),
                "error_logs": (
                    "[2026-03-20 17:55:02] ERROR: could not connect to read replica postgres-replica-2:5432\n"
                    "[2026-03-20 17:55:02] WARN: Failing over all reads to primary postgres-primary:5432\n"
                    "[2026-03-20 17:55:10] ERROR: too many connections (max 200) on primary\n"
                    "[2026-03-20 17:55:15] FATAL: remaining connection slots reserved for superuser"
                ),
                "metrics": {
                    "read_replica_status": "DOWN",
                    "primary_connections": "200/200 (at limit)",
                    "query_error_rate": "72%",
                    "primary_cpu": "98%",
                },
                "recent_changes": "Replica was restarted for OS patching 30 minutes ago. "
                    "Streaming replication has not re-established.",
                "on_call_notes": "Need to either restore replica replication or scale up primary capacity.",
                "ground_truth": {
                    "root_cause": "dependency_failure",
                    "severity": "p1",
                    "remediation": "failover",
                },
            },
            {
                "incident_id": "medium_007",
                "service_name": "video-transcoder",
                "alert_title": "HIGH: video-transcoder queue depth 50k — processing 3 hours behind",
                "alert_description": (
                    "video-transcoder job queue has exploded due to a viral upload event. "
                    "Queue depth reached 50,000 jobs. Current throughput cannot clear the backlog."
                ),
                "error_logs": (
                    "[2026-03-20 20:00:11] WARN: Queue depth 50,244 (SLA threshold: 1,000)\n"
                    "[2026-03-20 20:00:15] WARN: Estimated backlog clearance: 3.2 hours at current throughput\n"
                    "[2026-03-20 20:00:20] INFO: All 10 worker pods running at 100% CPU\n"
                    "[2026-03-20 20:00:25] WARN: New uploads being delayed by 3+ hours"
                ),
                "metrics": {
                    "queue_depth": "50,244",
                    "worker_pods": "10/10 at 100% CPU",
                    "processing_rate": "280 jobs/hour",
                    "backlog_eta": "3.2 hours",
                },
                "recent_changes": "Major content creator posted a 100-part series simultaneously 1 hour ago.",
                "on_call_notes": "Not an outage — SLA breach on processing time. Add worker capacity.",
                "ground_truth": {
                    "root_cause": "traffic_spike",
                    "severity": "p2",
                    "remediation": "scale_up",
                },
            },
            {
                "incident_id": "medium_008",
                "service_name": "billing-service",
                "alert_title": "CRITICAL: billing-service 100% error rate after v3.2.0 deploy",
                "alert_description": (
                    "billing-service v3.2.0 deployed 10 minutes ago. "
                    "Error rate went from 0% to 100%. All payment processing is down."
                ),
                "error_logs": (
                    "[2026-03-20 22:05:02] ERROR: ImportError: cannot import name 'StripeClient' from 'stripe' (v6.0.0)\n"
                    "[2026-03-20 22:05:02] ERROR: Module 'stripe' API changed — StripeClient removed in v6\n"
                    "[2026-03-20 22:05:03] FATAL: Application startup failed\n"
                    "[2026-03-20 22:05:03] CrashLoopBackOff on all 5 replicas"
                ),
                "metrics": {
                    "deployment_version": "v3.2.0 (10min ago)",
                    "payment_success_rate": "0%",
                    "pod_status": "5/5 CrashLoopBackOff",
                    "last_good_version": "v3.1.9",
                },
                "recent_changes": "v3.2.0 upgraded stripe-python from 5.5.0 to 6.0.0. Breaking API change not caught in tests.",
                "on_call_notes": "Immediate rollback to v3.1.9 will restore service. Root cause fix needs stripe v6 migration.",
                "ground_truth": {
                    "root_cause": "deployment_failure",
                    "severity": "p1",
                    "remediation": "rollback_deployment",
                },
            },
            {
                "incident_id": "medium_009",
                "service_name": "ml-inference-server",
                "alert_title": "MEDIUM: ml-inference-server GPU memory leak — performance degrading",
                "alert_description": (
                    "ml-inference-server GPU memory usage has been growing for 5 days. "
                    "P99 inference latency went from 80ms to 620ms. CUDA OOM errors starting."
                ),
                "error_logs": (
                    "[2026-03-20 09:33:21] WARN: GPU memory: 23.4GB / 24GB (97.5%)\n"
                    "[2026-03-20 09:33:21] WARN: Inference P99 latency: 620ms (SLO: 200ms)\n"
                    "[2026-03-20 09:34:02] ERROR: CUDA error: out of memory — model cache eviction failed\n"
                    "[2026-03-20 09:34:10] WARN: Cached model tensors: 8,421 (expected max: 50)"
                ),
                "metrics": {
                    "gpu_memory": "23.4GB / 24GB",
                    "inference_p99_latency": "620ms (SLO: 200ms)",
                    "cached_model_tensors": "8,421",
                    "memory_growth_rate": "~500MB/day",
                },
                "recent_changes": "v2.1.0 deployed 5 days ago — added model caching feature. Cache eviction has a bug.",
                "on_call_notes": "SLO breach. Restart clears GPU memory temporarily. Proper fix needs code change.",
                "ground_truth": {
                    "root_cause": "resource_leak",
                    "severity": "p3",
                    "remediation": "add_resources",
                },
            },
            {
                "incident_id": "medium_010",
                "service_name": "webhook-service",
                "alert_title": "HIGH: webhook-service mutual TLS cert expired — partner integrations failing",
                "alert_description": (
                    "The client certificate used by webhook-service for mutual TLS to partner APIs "
                    "expired 2 hours ago. All webhook deliveries to enterprise partners are failing."
                ),
                "error_logs": (
                    "[2026-03-20 12:00:01] ERROR: TLS handshake error: certificate expired\n"
                    "[2026-03-20 12:00:01] ERROR: x509: certificate has expired or is not yet valid: "
                    "current time 2026-03-20T12:00:01Z is after 2026-03-20T10:00:00Z\n"
                    "[2026-03-20 12:00:05] WARN: Webhook delivery failed for partner_id=ACME_CORP\n"
                    "[2026-03-20 12:02:30] ERROR: 14 enterprise partners reporting webhook failures"
                ),
                "metrics": {
                    "cert_expiry": "Expired 2026-03-20T10:00:00Z (2 hours ago)",
                    "webhook_delivery_success": "0% to mTLS partners",
                    "affected_partners": "14 enterprise accounts",
                    "pending_webhook_events": "28,441",
                },
                "recent_changes": "Certificate was due for renewal. Renewal request was submitted but approved cert "
                    "was not deployed — stuck in certificate issuance queue.",
                "on_call_notes": "Enterprise SLA breach. Need to deploy renewed cert immediately.",
                "ground_truth": {
                    "root_cause": "certificate_expired",
                    "severity": "p2",
                    "remediation": "renew_certificate",
                },
            },
        ],
    },

    "hard": {
        "id": "hard",
        "name": "Full Incident Response with Postmortem",
        "description": (
            "Analyse each complex production incident. Provide: root cause, severity, immediate remediation, "
            "AND a complete postmortem_summary. "
            "The postmortem must include: (1) timeline of events, (2) root cause analysis, "
            "(3) immediate fix applied, (4) prevention measures to avoid recurrence. "
            "Aim for 150+ words in the postmortem. "
            "root_cause: out_of_memory | disk_full | service_crash | config_error | "
            "network_timeout | dependency_failure | traffic_spike | deployment_failure | "
            "resource_leak | certificate_expired. "
            "severity: p1 | p2 | p3 | p4. "
            "remediation: restart_service | rollback_deployment | scale_up | clear_disk | fix_config | "
            "block_traffic | failover | renew_certificate | investigate | add_resources."
        ),
        "difficulty": "hard",
        "max_steps": 5,
        "incidents": [
            {
                "incident_id": "hard_001",
                "service_name": "platform-api",
                "alert_title": "CRITICAL: platform-api cascading failure — all endpoints returning 500",
                "alert_description": (
                    "platform-api has been fully down for 22 minutes. "
                    "Root cause is traced to a new deployment that introduced an incompatible database migration. "
                    "The migration added a NOT NULL column without a default, causing all INSERT/UPDATE queries to fail. "
                    "Database is healthy but application is crashing on every write operation."
                ),
                "error_logs": (
                    "[2026-03-25 14:00:01] Deploying platform-api v4.1.0\n"
                    "[2026-03-25 14:00:15] Running migration 0042_add_user_tier_column\n"
                    "[2026-03-25 14:00:16] ALTER TABLE users ADD COLUMN tier VARCHAR(20) NOT NULL\n"
                    "[2026-03-25 14:00:18] Migration complete\n"
                    "[2026-03-25 14:00:20] ERROR: null value in column 'tier' of relation 'users' "
                    "violates not-null constraint\n"
                    "[2026-03-25 14:00:20] ERROR: INSERT INTO users (...) failed — 500 Internal Server Error\n"
                    "[2026-03-25 14:00:20] FATAL: All write operations failing — 100% 500 error rate\n"
                    "[2026-03-25 14:00:25] WARN: Circuit breaker opened on downstream services\n"
                    "[2026-03-25 14:20:45] ALERT: platform-api down 20 minutes — major incident declared"
                ),
                "metrics": {
                    "error_rate": "100%",
                    "deployment_version": "v4.1.0 (deployed 22min ago)",
                    "db_write_success_rate": "0%",
                    "affected_users": "~85,000 active sessions",
                    "downstream_services_impacted": "7 (circuit breakers open)",
                    "estimated_revenue_loss": "$41,000",
                },
                "recent_changes": (
                    "v4.1.0 added user tier system. Migration engineer added NOT NULL column without DEFAULT. "
                    "Staging uses small dataset (migration passed). Prod has millions of existing rows. "
                    "Code review did not catch the missing DEFAULT value."
                ),
                "on_call_notes": (
                    "Incident commander: Priya Sharma. "
                    "Rollback to v4.0.9 will restore API but leaves the bad column in place. "
                    "Must also add DEFAULT 'standard' to the column after rollback. "
                    "7 downstream services are circuit-broken and need manual reset post-recovery."
                ),
                "ground_truth": {
                    "root_cause": "deployment_failure",
                    "severity": "p1",
                    "remediation": "rollback_deployment",
                    "postmortem_requirements": {
                        "must_include": [
                            "migration", "NOT NULL", "rollback",
                            "prevention", "timeline", "DEFAULT"
                        ],
                        "must_not_include": ["blame", "negligence"],
                        "min_words": 150,
                    },
                },
            },
            {
                "incident_id": "hard_002",
                "service_name": "realtime-pipeline",
                "alert_title": "CRITICAL: realtime-pipeline Kafka consumer lag 48 hours — data loss risk",
                "alert_description": (
                    "realtime-pipeline Kafka consumer has been falling behind for 3 days due to a memory leak "
                    "introduced in v5.2.0. Consumer lag has reached 48 hours worth of events. "
                    "Kafka topic retention is 72 hours — data loss will occur in 24 hours if not resolved. "
                    "The leak is in the Avro deserialization cache which never evicts entries."
                ),
                "error_logs": (
                    "[2026-03-22 06:00:00] Deploying realtime-pipeline v5.2.0\n"
                    "[2026-03-22 06:01:00] INFO: AvroDeserializer cache initialized (no eviction policy)\n"
                    "[2026-03-22 07:00:00] INFO: Memory RSS: 340MB\n"
                    "[2026-03-23 07:00:00] WARN: Memory RSS: 2,100MB — consumer throughput dropping\n"
                    "[2026-03-24 07:00:00] ERROR: Memory RSS: 5,800MB — GC pauses >10s\n"
                    "[2026-03-25 07:00:00] CRITICAL: Memory RSS: 9,200MB / 10,240MB limit\n"
                    "[2026-03-25 07:00:00] CRITICAL: Kafka consumer lag: 172,800,000 events (~48 hours)\n"
                    "[2026-03-25 07:00:00] ALERT: Data loss in ~24 hours if consumer does not catch up"
                ),
                "metrics": {
                    "consumer_lag_hours": "48",
                    "memory_rss": "9.2GB / 10GB limit",
                    "avro_cache_entries": "8,421,000 (unbounded)",
                    "consumer_throughput": "120 events/sec (normal: 12,000/sec)",
                    "kafka_retention_remaining": "24 hours before oldest data deleted",
                    "data_at_risk": "~48 hours of pipeline events",
                },
                "recent_changes": (
                    "v5.2.0 added Avro schema caching for performance. Cache implementation uses a plain HashMap "
                    "with no eviction. 8.4M unique schema fingerprints accumulated over 3 days."
                ),
                "on_call_notes": (
                    "Incident commander: Marcus Chen. "
                    "Immediate: restart to clear memory, consume backlog before retention expires. "
                    "Need to add LRU eviction (max 10,000 entries) to AvroDeserializer. "
                    "After restart, throughput will recover and lag should clear in ~4 hours."
                ),
                "ground_truth": {
                    "root_cause": "resource_leak",
                    "severity": "p1",
                    "remediation": "restart_service",
                    "postmortem_requirements": {
                        "must_include": [
                            "memory leak", "cache", "eviction", "kafka",
                            "timeline", "prevention", "restart"
                        ],
                        "must_not_include": ["blame"],
                        "min_words": 150,
                    },
                },
            },
            {
                "incident_id": "hard_003",
                "service_name": "multi-region-lb",
                "alert_title": "CRITICAL: multi-region-lb misconfiguration routing prod traffic to dev",
                "alert_description": (
                    "A Terraform misconfiguration deployed 2 hours ago caused multi-region-lb to route "
                    "15% of production traffic to the development environment. "
                    "Development database received production user data. GDPR and data isolation breach confirmed. "
                    "Development environment's weaker rate limits caused some requests to be blocked."
                ),
                "error_logs": (
                    "[2026-03-24 10:00:00] Applying Terraform plan: multi-region-lb-v2\n"
                    "[2026-03-24 10:00:45] Changed: aws_lb_target_group.prod weight: [100, 0] -> [85, 15]\n"
                    "[2026-03-24 10:00:45] Changed: target group 2 backend: us-east-1-prod -> us-east-1-dev\n"
                    "[2026-03-24 10:01:00] Apply complete\n"
                    "[2026-03-24 10:05:00] WARN: 15% of requests returning unexpected responses\n"
                    "[2026-03-24 10:15:00] ERROR: User data observed in dev database — data isolation breach\n"
                    "[2026-03-24 11:55:00] CRITICAL: GDPR breach confirmed — DPO notified"
                ),
                "metrics": {
                    "traffic_misrouted_to_dev": "15%",
                    "affected_requests": "~180,000 in 2 hours",
                    "dev_db_prod_records_written": "~4,200",
                    "gdpr_breach_confirmed": "yes — DPO notified",
                    "error_rate_from_dev": "8% (rate limit rejections)",
                },
                "recent_changes": (
                    "Terraform refactor to support multi-region routing. Engineer copy-pasted target group block "
                    "and changed region but forgot to update backend to 'prod'. "
                    "Terraform plan review did not catch the logical error (looked syntactically correct)."
                ),
                "on_call_notes": (
                    "Incident commander: Aisha Okonkwo. DPO and Legal already engaged. "
                    "Priority: fix_config to restore 100% prod routing immediately. "
                    "Then audit dev DB for prod data and purge. "
                    "72-hour GDPR breach notification window has started."
                ),
                "ground_truth": {
                    "root_cause": "config_error",
                    "severity": "p1",
                    "remediation": "fix_config",
                    "postmortem_requirements": {
                        "must_include": [
                            "Terraform", "misconfiguration", "GDPR", "data",
                            "timeline", "prevention", "review"
                        ],
                        "must_not_include": ["blame"],
                        "min_words": 150,
                    },
                },
            },
            {
                "incident_id": "hard_004",
                "service_name": "cdn-origin",
                "alert_title": "HIGH: cdn-origin certificate chain incomplete — 35% of users getting SSL errors",
                "alert_description": (
                    "cdn-origin renewed its TLS certificate 4 hours ago but the intermediate CA certificate "
                    "was not included in the certificate chain. Modern browsers with cached intermediate certs work fine "
                    "(65% of users). But mobile apps, curl, and browsers without the cached intermediate cert "
                    "are getting SSL_ERROR_BAD_CERT_DOMAIN errors (35% of users)."
                ),
                "error_logs": (
                    "[2026-03-23 08:00:00] Certificate renewed and deployed for cdn-origin.example.com\n"
                    "[2026-03-23 08:00:30] Only leaf certificate installed — intermediate CA omitted\n"
                    "[2026-03-23 08:05:00] WARN: SSL errors reported from mobile app version <4.2\n"
                    "[2026-03-23 08:30:00] ERROR: curl: (60) SSL certificate problem: unable to get local issuer certificate\n"
                    "[2026-03-23 09:00:00] HIGH: 35% of CDN requests failing SSL handshake\n"
                    "[2026-03-23 11:45:00] WARN: Customer support tickets spiking (+320 in 3 hours)"
                ),
                "metrics": {
                    "ssl_error_rate": "35%",
                    "affected_clients": "mobile apps, curl, non-cached-intermediate browsers",
                    "unaffected_clients": "65% (cached intermediate cert in browser store)",
                    "support_tickets_3h": "320",
                    "cert_expiry": "Valid until 2027-03-23 (newly renewed — correct)",
                },
                "recent_changes": (
                    "Certificate renewal used a new automation script. Script correctly fetched the leaf cert "
                    "but did not include the Let's Encrypt R11 intermediate CA. "
                    "Previous renewals were done manually and always included the full chain."
                ),
                "on_call_notes": (
                    "Incident commander: Tomás Rivera. "
                    "Fix: redeploy cert with full chain (leaf + Let's Encrypt R11 intermediate + ISRG Root X1). "
                    "No need for new cert — just reconfigure nginx with the full chain bundle."
                ),
                "ground_truth": {
                    "root_cause": "certificate_expired",
                    "severity": "p2",
                    "remediation": "renew_certificate",
                    "postmortem_requirements": {
                        "must_include": [
                            "certificate", "chain", "intermediate",
                            "timeline", "prevention", "automation"
                        ],
                        "must_not_include": ["blame"],
                        "min_words": 150,
                    },
                },
            },
            {
                "incident_id": "hard_005",
                "service_name": "search-cluster",
                "alert_title": "CRITICAL: search-cluster Elasticsearch OOM + disk full — dual failure",
                "alert_description": (
                    "search-cluster is experiencing a dual failure: Elasticsearch data nodes are being OOMKilled "
                    "because a runaway aggregation query caused JVM heap to spike to 100%, "
                    "AND the query also generated a 180GB temporary result set that filled the disk. "
                    "All search is down. The offending query came from a new analytics dashboard deployed this morning."
                ),
                "error_logs": (
                    "[2026-03-26 09:00:00] Analytics dashboard v1.0.0 deployed\n"
                    "[2026-03-26 09:02:00] INFO: Dashboard running aggregation query: "
                    "terms agg on 'user_id' field, size=100000\n"
                    "[2026-03-26 09:02:10] WARN: JVM heap: 28GB / 30GB (93%)\n"
                    "[2026-03-26 09:02:30] ERROR: JVM heap: 30GB / 30GB (100%) — GC thrashing\n"
                    "[2026-03-26 09:02:45] ERROR: java.lang.OutOfMemoryError: Java heap space\n"
                    "[2026-03-26 09:02:45] OOMKilled: elasticsearch-data-0\n"
                    "[2026-03-26 09:02:46] OOMKilled: elasticsearch-data-1\n"
                    "[2026-03-26 09:02:46] OOMKilled: elasticsearch-data-2\n"
                    "[2026-03-26 09:03:00] ERROR: disk /data: 100% full (180GB temp files from agg query)\n"
                    "[2026-03-26 09:03:05] FATAL: All search requests returning 503"
                ),
                "metrics": {
                    "search_availability": "0%",
                    "es_nodes_down": "3/3 data nodes OOMKilled",
                    "disk_usage": "100% (180GB temp from aggregation)",
                    "jvm_heap_at_failure": "30GB / 30GB (100%)",
                    "offending_query": "terms aggregation, size=100000 on user_id field",
                    "affected_users": "~120,000 (all search down)",
                },
                "recent_changes": (
                    "Analytics dashboard v1.0.0 deployed at 09:00. "
                    "Dashboard runs an unbounded terms aggregation (size=100000) on the 50M-document user index "
                    "every 60 seconds. Query was never load-tested against production data volume."
                ),
                "on_call_notes": (
                    "Incident commander: Yuki Tanaka. "
                    "Step 1: Block the dashboard queries (block_traffic or disable dashboard). "
                    "Step 2: Clear disk temp files. "
                    "Step 3: Restart Elasticsearch nodes. "
                    "Step 4: Add circuit breaker / query cost limit to prevent future runaway queries."
                ),
                "ground_truth": {
                    "root_cause": "out_of_memory",
                    "severity": "p1",
                    "remediation": "block_traffic",
                    "postmortem_requirements": {
                        "must_include": [
                            "aggregation", "query", "heap", "disk",
                            "timeline", "prevention", "circuit breaker"
                        ],
                        "must_not_include": ["blame"],
                        "min_words": 150,
                    },
                },
            },
        ],
    },

    "reproduce": {
        "id": "reproduce",
        "name": "Failure Reproduction Steps",
        "description": (
            "Analyse each production incident and provide: the root cause AND detailed step-by-step "
            "instructions that an engineer could follow to reproduce the failure in a test environment. "
            "reproduction_steps must be a numbered list (Step 1, Step 2, ...) covering: "
            "(1) the preconditions / setup required, "
            "(2) the specific action or change that triggers the failure, "
            "(3) what observable symptoms confirm the failure is reproduced. "
            "Aim for 5+ steps and 80+ words. "
            "root_cause: out_of_memory | disk_full | service_crash | config_error | "
            "network_timeout | dependency_failure | traffic_spike | deployment_failure | "
            "resource_leak | certificate_expired. "
            "Set severity=p3, remediation=investigate, postmortem_summary=null."
        ),
        "difficulty": "medium",
        "max_steps": 5,
        "incidents": [
            {
                "incident_id": "repro_001",
                "service_name": "checkout-service",
                "alert_title": "CRITICAL: checkout-service OOMKilled — pod restarting repeatedly",
                "alert_description": (
                    "checkout-service pods are being OOMKilled continuously under promotional traffic load. "
                    "The service has a 512Mi memory limit. Memory spikes to 511Mi and the container is killed. "
                    "The root cause is that the in-memory cart object cache has no size limit and grows unboundedly "
                    "during high-traffic events."
                ),
                "error_logs": (
                    "[2026-04-01 12:00:00] INFO: Promotions campaign started — traffic x10\n"
                    "[2026-04-01 12:14:33] WARN: JVM heap: 490Mi / 512Mi (95%)\n"
                    "[2026-04-01 12:14:55] FATAL: java.lang.OutOfMemoryError: Java heap space\n"
                    "[2026-04-01 12:14:55] Killed (exit code 137)\n"
                    "[2026-04-01 12:15:01] Container checkout-service restarted (4th restart in 15min)"
                ),
                "metrics": {
                    "memory_limit": "512Mi",
                    "memory_at_kill": "511Mi (99.8%)",
                    "pod_restarts": "4 in last 15 minutes",
                    "cart_cache_entries": "~180,000 (no eviction)",
                    "traffic_multiplier": "10x (promotional campaign)",
                },
                "recent_changes": "Promotions campaign started 15 minutes ago. No code changes in 48 hours.",
                "on_call_notes": (
                    "Cart cache at com.example.checkout.CartCache uses a plain HashMap with no size cap. "
                    "Normal traffic keeps it under 20,000 entries. x10 traffic fills it to 180k+."
                ),
                "ground_truth": {
                    "root_cause": "out_of_memory",
                    "severity": "p1",
                    "remediation": "restart_service",
                    "reproduction_requirements": {
                        "must_include": [
                            "memory", "512", "traffic", "cache", "load",
                            "step", "restart"
                        ],
                        "must_have_steps": True,
                        "min_words": 80,
                    },
                },
            },
            {
                "incident_id": "repro_002",
                "service_name": "postgres-primary",
                "alert_title": "CRITICAL: Disk full on postgres-primary — writes failing",
                "alert_description": (
                    "PostgreSQL primary disk reached 100% because WAL archiving was disabled "
                    "and old WAL files were never cleaned up. The root cause is a missing cron job "
                    "that was accidentally deleted when the crontab was edited two weeks ago."
                ),
                "error_logs": (
                    "[2026-04-02 08:22:10] ERROR: could not write to file 'pg_wal/000000010000001F': "
                    "No space left on device\n"
                    "[2026-04-02 08:22:10] LOG: database system is shut down\n"
                    "[2026-04-02 08:22:15] ERROR: disk full — all writes rejected\n"
                    "[2026-04-02 08:22:20] WARN: WAL directory size: 42GB (accumulated over 14 days)"
                ),
                "metrics": {
                    "disk_usage": "100% (500GB / 500GB)",
                    "wal_directory_size": "42GB",
                    "log_rotation_last_run": "14 days ago",
                    "write_error_rate": "100%",
                },
                "recent_changes": "Crontab edited 14 days ago for unrelated task. pg_wal_cleanup job accidentally deleted.",
                "on_call_notes": (
                    "Cron job: `0 2 * * * /usr/local/bin/pg_wal_cleanup.sh` was removed from crontab. "
                    "WAL files accumulated over 14 days at ~3GB/day."
                ),
                "ground_truth": {
                    "root_cause": "disk_full",
                    "severity": "p1",
                    "remediation": "clear_disk",
                    "reproduction_requirements": {
                        "must_include": [
                            "cron", "WAL", "disk", "14", "delete",
                            "step", "accumulate"
                        ],
                        "must_have_steps": True,
                        "min_words": 80,
                    },
                },
            },
            {
                "incident_id": "repro_003",
                "service_name": "notification-service",
                "alert_title": "ERROR: notification-service connecting to wrong database after secret rotation",
                "alert_description": (
                    "After rotating the DB_HOST secret in AWS Secrets Manager, notification-service "
                    "was not restarted and continued using the old cached value pointing to the staging database. "
                    "All emails and push notifications are silently failing."
                ),
                "error_logs": (
                    "[2026-04-03 14:33:21] ERROR: Connection refused: db-staging.internal:5432\n"
                    "[2026-04-03 14:33:21] ERROR: FATAL: password authentication failed for user 'notif_prod'\n"
                    "[2026-04-03 14:33:25] WARN: Retrying DB connection (attempt 3/5) — all failing\n"
                    "[2026-04-03 14:33:35] ERROR: Email queue depth: 14,232 (undelivered and growing)"
                ),
                "metrics": {
                    "db_connection_success_rate": "0%",
                    "emails_queued_undelivered": "14,232",
                    "time_since_secret_rotation": "30 minutes",
                    "service_process_status": "Running (but non-functional)",
                },
                "recent_changes": (
                    "DB_HOST secret rotated in AWS Secrets Manager 30 minutes ago. "
                    "New value correctly points to db-prod.internal. "
                    "Service reads secret only at startup — not restarted after rotation."
                ),
                "on_call_notes": (
                    "Service reads secrets at startup via boto3 get_secret_value(). "
                    "Secret was rotated but service was not restarted. "
                    "Old value (db-staging.internal) is cached in process memory."
                ),
                "ground_truth": {
                    "root_cause": "config_error",
                    "severity": "p2",
                    "remediation": "fix_config",
                    "reproduction_requirements": {
                        "must_include": [
                            "secret", "restart", "rotate", "staging", "startup",
                            "step", "config"
                        ],
                        "must_have_steps": True,
                        "min_words": 80,
                    },
                },
            },
            {
                "incident_id": "repro_004",
                "service_name": "billing-service",
                "alert_title": "CRITICAL: billing-service crashes on startup after stripe-python v6 upgrade",
                "alert_description": (
                    "billing-service v3.2.0 introduced stripe-python 6.0.0 which removed the StripeClient class. "
                    "All 5 pods are in CrashLoopBackOff. The failure is 100% reproducible by deploying v3.2.0 "
                    "or by installing stripe==6.0.0 and importing the old StripeClient class."
                ),
                "error_logs": (
                    "[2026-04-04 22:05:02] ERROR: ImportError: cannot import name 'StripeClient' from 'stripe'\n"
                    "[2026-04-04 22:05:02] ERROR: stripe v6.0.0 removed StripeClient — use stripe.Stripe() instead\n"
                    "[2026-04-04 22:05:03] FATAL: Application startup failed — exiting\n"
                    "[2026-04-04 22:05:10] CrashLoopBackOff: 5/5 pods failing at import time"
                ),
                "metrics": {
                    "deployment_version": "v3.2.0",
                    "stripe_python_version": "6.0.0 (was 5.5.0)",
                    "pod_status": "5/5 CrashLoopBackOff",
                    "payment_success_rate": "0%",
                },
                "recent_changes": "requirements.txt changed: stripe==5.5.0 → stripe==6.0.0. StripeClient was removed in v6.",
                "on_call_notes": (
                    "stripe v6 breaking change: `from stripe import StripeClient` raises ImportError. "
                    "Fix is to replace with `stripe.Stripe()` API or pin back to stripe==5.5.0."
                ),
                "ground_truth": {
                    "root_cause": "deployment_failure",
                    "severity": "p1",
                    "remediation": "rollback_deployment",
                    "reproduction_requirements": {
                        "must_include": [
                            "stripe", "6.0.0", "import", "StripeClient", "install",
                            "step", "crash"
                        ],
                        "must_have_steps": True,
                        "min_words": 80,
                    },
                },
            },
            {
                "incident_id": "repro_005",
                "service_name": "analytics-collector",
                "alert_title": "HIGH: analytics-collector goroutine leak — memory grows 50MB/hour",
                "alert_description": (
                    "analytics-collector v3.1.0 introduced a goroutine leak: each incoming event spawns a goroutine "
                    "that writes to an unbuffered channel, but the channel reader goroutine was accidentally removed "
                    "in the refactor. Goroutines block forever, accumulate, and leak memory at ~50MB/hour."
                ),
                "error_logs": (
                    "[2026-04-05 09:00:00] INFO: v3.1.0 deployed — refactored event pipeline\n"
                    "[2026-04-05 10:00:00] WARN: Goroutine count: 12,441 (normal: ~42)\n"
                    "[2026-04-05 11:00:00] WARN: Goroutine count: 24,883 — memory RSS: 820MB\n"
                    "[2026-04-05 12:00:00] ERROR: Goroutine count: 37,200 — memory RSS: 1,420MB\n"
                    "[2026-04-05 13:00:00] CRITICAL: Memory RSS: 2,100MB — GC pauses >500ms"
                ),
                "metrics": {
                    "goroutine_count": "37,200 (normal: ~42)",
                    "memory_rss": "2,100MB (started at 180MB)",
                    "memory_growth_rate": "~50MB/hour",
                    "deployment_age": "v3.1.0 deployed 4 hours ago",
                },
                "recent_changes": (
                    "v3.1.0 refactored event pipeline. "
                    "eventConsumer goroutine that read from eventChan was accidentally deleted. "
                    "eventProducer goroutines still write to eventChan (unbuffered) and block forever."
                ),
                "on_call_notes": (
                    "The leak: `go func() { eventChan <- event }()` spawns goroutines that block on write. "
                    "eventChan is unbuffered and has no reader. Each event request leaks one goroutine."
                ),
                "ground_truth": {
                    "root_cause": "resource_leak",
                    "severity": "p3",
                    "remediation": "restart_service",
                    "reproduction_requirements": {
                        "must_include": [
                            "goroutine", "channel", "deploy", "event", "memory",
                            "step", "request"
                        ],
                        "must_have_steps": True,
                        "min_words": 80,
                    },
                },
            },
        ],
    },
}
