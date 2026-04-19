# Pitfalls Research: Node Capacity & Isolation Validation

**Domain:** Nested container orchestration with resource limit enforcement and cgroup validation
**Researched:** 2026-04-06
**Confidence:** HIGH (Docker/Kubernetes official sources + 2026 research + cgroup kernel documentation)

---

## Critical Pitfalls

### Pitfall 1: Cgroup v1 vs v2 Semantic Mismatch in Memory Limit Reporting

**What goes wrong:**
A stress test passes on a cgroup v1 system, showing successful memory enforcement, but fails on a cgroup v2 system (or vice versa). Tests report inconsistent memory usage numbers: the same workload consumes "more memory" on v2 than v1, even though the actual heap usage is identical. OOM kills happen unpredictably on one version but not the other.

**Why it happens:**
- **cgroup v1** uses `memory.limit_in_bytes` (hard limit) and `memory.memsw.limit_in_bytes` (memory+swap combined). Accounting includes page cache, and different controllers (CPU, memory, I/O) have inconsistent semantics.
- **cgroup v2** uses `memory.max` (hard limit only) and separate `memory.swap.max` (swap-only control). Memory reporting includes previously-uncounted allocations. Page cache is reported more accurately, often appearing higher than v1 because cgroup v1's page cache accounting was lenient.
- A stress test allocating anonymous memory might pass 512MB on v1 but fail on v2 because page cache (file I/O) now counts more aggressively.
- Swap handling differs: v1's combined counter was unintuitive; v2 separates them, so a test that relied on spill-to-swap behavior breaks if swap is capped differently.

**How to avoid:**
- **Pre-flight detection:** Implement `detect_cgroup_version()` that reads `/proc/self/cgroup` (v1) vs `/sys/fs/cgroup/unified` (v2) at node startup and store in heartbeat.
- **Separate validation suites:** Write v1-specific and v2-specific stress tests. Don't assume one works for both.
- **Document accounting differences:** Stress test scripts must account for page cache. Use `memory.stat` (v1) or `memory.stat` (v2) to subtract inactive file cache, or use direct heap pressure.
- **Sample production systems:** Before deploying validation, scan target environments for cgroup version and test on matching systems.

**Warning signs:**
- Stress test results differ 15%+ across identical jobs on different nodes
- OOM kills on some nodes but not others, despite identical memory limits
- `dmesg` shows memory.max enforcement on v2 nodes but memory.limit_in_bytes on v1 nodes
- Job exit codes differ (137 SIGKILL on v2, slower throttle on v1)

**Phase to address:**
**Phase 1 (Stress Test Corpus Creation):** Implement cgroup detection and v1/v2 dual-path stress scripts. Validation cannot proceed without understanding the cgroup version.

---

### Pitfall 2: Page Cache Surprise OOM Kills in Nested Containers

**What goes wrong:**
A stress test allocates 256MB in a container with a 512MB limit and expects to run fine. Instead, the job is OOM-killed. Logs show exit code 137. The actual heap usage was only 250MB according to the application. The problem: page cache from file I/O (logs, temp files, `dd` reads) consumed 280MB, pushing total over the limit.

**Why it happens:**
- Memory limits in cgroups count page cache against the container's limit.
- Page cache is memory the kernel keeps for "free" — it's evictable when needed, but it counts as used memory.
- A stress test that does heavy I/O (writing logs, reading files, `dd` reads) unexpectedly triggers page cache growth.
- The operator thinks "my app uses 200MB," but the cgroup sees 450MB (200MB app + 250MB cache).
- In nested containers (DinD), child cgroups inherit parent limits, and page cache can push the total over the child's limit even if the parent has free memory.

**How to avoid:**
- **Distinguish heap from page cache:** Stress tests must report both. Read from `/sys/fs/cgroup/memory/memory.stat` (v1) and subtract `total_inactive_file` for accurate heap pressure.
- **Isolate workload types:** Separate CPU/memory stress from I/O stress. A memory test should minimize I/O.
- **Set memory.high (v2) or memsw limits (v1):** Use a throttling threshold to detect pressure before OOM.
- **Script design:** Use `dd if=/dev/zero bs=1M count=X | /bin/cat > /dev/null` to allocate anonymous memory without page cache.

**Warning signs:**
- Job OOM-killed when `free` inside the container shows available memory
- Page cache grows unexpectedly during execution
- Same workload succeeds without I/O redirection but fails with logging
- Exit code 137 (SIGKILL) with no corresponding application error

**Phase to address:**
**Phase 2 (Cgroup Pre-flight & Validation):** Implement memory.stat parsing in validation scripts. Store page cache metrics separately from heap metrics.

---

### Pitfall 3: Docker-in-Docker (DinD) Cgroup Inheritance & Parent Limit Overwriting

**What goes wrong:**
A node container is created with `--memory=4g`. Inside that node, the orchestrator launches job containers with `--memory=512m`. Job containers fail with cryptic cgroup errors or silently ignore the memory limit. Stress tests show job containers can allocate memory beyond their declared limits because they inherit the 4g parent limit.

**Why it happens:**
- Docker daemon assigns the outer container to `/docker/<id>` in the host's cgroup hierarchy. The Docker daemon inside the outer container sees a nested hierarchy.
- When inner Docker tries to apply resource limits to a child container, it attempts to write to cgroup files that are already constrained by the parent, leading to "domain threaded mode" conflicts in cgroup v2.
- Parent cgroup limits can be **overwritten** when the inner Docker daemon starts. The inner Docker sees `memory.max` as "unlimited" and may override it to a very high value.
- Cgroup v2's "no internal process" constraint prevents parent containers from having child cgroups with domain controllers if the parent has processes.

**How to avoid:**
- **Use `--cgroup-parent` explicitly:** When launching the node container, set a cgroup parent that won't conflict with inner containers.
- **Avoid cgroup v2 domain threaded mode:** If targeting cgroup v2, ensure proper delegation.
- **Enforce limits at job submission time:** Don't rely on inner Docker to enforce limits. Implement admission control.
- **Use EXECUTION_MODE=direct for DinD:** Avoid nested runtimes. Run jobs as Python subprocesses inside the node container.

**Warning signs:**
- Job containers created inside nodes report `memory.max=unlimited` or a suspiciously large value
- Stress tests inside job containers can allocate beyond the declared limit
- Inner Docker daemon logs show cgroup permission errors
- Memory limits work on bare-metal nodes but not on DinD nodes

**Phase to address:**
**Phase 2 (Cgroup Pre-flight & Validation):** Detect DinD setup and validate cgroup parent configuration. Implement node-level admission control.

---

### Pitfall 4: Invisible OOM Kills and "Partial" Process Termination

**What goes wrong:**
A job container is running and reporting "success," but critical child processes have been OOM-killed. The main process (PID 1) continues running, but helper threads or background daemons were terminated. The orchestrator sees exit code 0 (success) instead of 137 (OOM kill), leading to false positives in validation tests.

**Why it happens:**
- When the cgroup hits its memory limit, the Linux OOM killer doesn't necessarily kill PID 1. It may kill any other process in the cgroup that can free memory.
- If a background daemon is selected instead of the main application, the container appears to succeed even though it's partially dead.
- **cgroup v1** suffers more from this: the OOM killer makes independent decisions per-process, not per-cgroup.
- **cgroup v2** is better but still not deterministic if multiple processes are running.
- The orchestrator queries the container exit code via the Docker/Podman API, which only reflects PID 1. Child process deaths are invisible.

**How to avoid:**
- **Use cgroup v2 with cgroup grouping:** cgroup v2 improves OOM killer behavior, but only if the kernel is recent enough (Kubernetes 1.28+).
- **Minimize processes in job containers:** Use a lightweight init or run jobs directly as the main process (no background daemons).
- **Monitor exit codes strictly:** Exit code 137 = OOM/SIGKILL. Map all non-zero exits to job failure.
- **Log kernel events:** Before declaring a test successful, check `dmesg` for OOM killer logs.
- **Validate with verbose memory tracking:** Query `memory.oom_control` (v1) or `memory.events` (v2) to detect OOM events.

**Warning signs:**
- Stress test reports "passed" but `dmesg` shows OOM killer activity
- Job output is incomplete (e.g., test script starts but doesn't finish)
- Child processes disappear mid-execution but container keeps running
- Exit code is 0 or non-137, but memory.oom_control shows OOM event occurred

**Phase to address:**
**Phase 2 (Cgroup Pre-flight & Validation):** Implement kernel log monitoring. Add `memory.events` / `memory.oom_control` checking to validation suite. Require single-process job containers.

---

### Pitfall 5: EXECUTION_MODE=direct Bypasses All Container Isolation

**What goes wrong:**
A stress test allocates memory in EXECUTION_MODE=direct (Python subprocess), saturating the node's memory. This causes all concurrent jobs to slow down (memory pressure, page cache reclaim). A "noisy neighbor" job can starve legitimate workloads. Meanwhile, a CPU stress test in direct mode consumes a full CPU core, monopolizing it.

**Why it happens:**
- **EXECUTION_MODE=direct** runs jobs as Python subprocess calls, not as containers. This avoids nested container complexity but sacrifices all cgroup-based isolation.
- Subprocesses run under the parent node container's cgroup. They consume memory, CPU, and I/O from the same pool as the orchestrator itself.
- There's no per-job memory limit, no per-job CPU quota, no memory-to-swap accounting. A runaway job can OOM the entire node.
- Resource limits passed to `runtime.py` are **completely ignored** when mode is `direct`.

**How to avoid:**
- **Document the tradeoff clearly:** EXECUTION_MODE=direct is a workaround for DinD cgroup issues, not a long-term solution.
- **Add runtime validation:** Before accepting a job, `runtime.py` must verify the execution mode and warn when limits are ignored.
- **Enforce admission control at the node level:** Even with direct mode, implement checks for free memory and available CPU before accepting the job at `/work/pull`.
- **Reserve headroom:** If using direct mode, enforce that job memory + reserved orchestrator memory < total node memory.
- **Stress tests must use container mode:** For validation, explicitly use EXECUTION_MODE=docker or podman.

**Warning signs:**
- A single job causes the entire node to become unresponsive
- Memory limits in the job spec are silently ignored (no warning logs)
- CPU stress test consumes full cores without sharing
- Concurrent jobs interfere with each other (cache thrashing, OOM)

**Phase to address:**
**Phase 2 (Execution Mode Validation):** Implement mode-aware admission control. Add warnings for ignored limits. Verify that direct mode is only used in DinD scenarios.

---

### Pitfall 6: Stress Test Variation Across Architectures & Cross-Platform Scripts

**What goes wrong:**
A CPU stress script written in Bash works perfectly on Linux but PowerShell versions on Windows Server hang or produce incorrect load. Memory stress tools behave differently on Alpine vs. Debian (musl vs. glibc memory allocators). Cross-platform stress tests are unreliable indicators of actual resource enforcement.

**Why it happens:**
- **Shell differences:** Bash and PowerShell have different process models. Bash `for` loops spawn processes per iteration; PowerShell has built-in parallelism.
- **Memory allocators:** Python's `memory_profiler`, Linux libc malloc, and musl malloc behave differently.
- **CPU affinity:** PowerShell and Windows don't have `taskset` or cgroup-style CPU pinning. Without explicit affinity, a single thread can bounce between cores.
- **I/O differences:** `/dev/zero` on Linux is fast; Windows `NUL` device has different behavior.
- **Swap behavior:** Windows doesn't have swap in the Linux sense; Alpine containers may have swap disabled.

**How to avoid:**
- **Platform-specific stress suites:** Maintain separate scripts for different platforms.
- **Validate allocator behavior:** Before running stress tests, profile the actual memory consumption.
- **Use established tools:** Instead of custom stress scripts, wrap known-good tools like `stress-ng` for Linux.
- **Document platform constraints:** Clearly note in validation reports which platforms each test is valid for.

**Warning signs:**
- Stress test results vary by >10% across identical workloads on different platforms
- PowerShell script hangs or produces 0% load despite loops running
- Bash script works on Debian but crashes on Alpine
- CPU load reported by `top` differs from test script's expectation

**Phase to address:**
**Phase 1 (Stress Test Corpus Creation):** Build platform-aware test suite. Use `stress-ng` or equivalent canonical tools instead of custom scripts.

---

### Pitfall 7: Swap Accounting Differences Break Comparative Testing

**What goes wrong:**
A node has swap enabled; another doesn't. A stress test allocates 1.5GB to a container with a 1GB memory limit. On the no-swap node, it fails immediately (exit 137, OOM). On the swap-enabled node, it "succeeds" but the system becomes unusable (swapping to disk, 10s+ latency). The validation report is inconsistent.

**Why it happens:**
- **cgroup v1:** `memory.memsw.limit_in_bytes` is a combined memory+swap limit. A job can allocate beyond its memory limit, using swap instead.
- **cgroup v2:** `memory.max` caps memory only; `memory.swap.max` caps swap separately.
- **Swap disabled:** Many cloud providers disable swap to avoid unpredictable latency. A stress test that passes with swap fails without it.
- **Different limits on different nodes:** One node might have different swap configuration than another.

**How to avoid:**
- **Standardize swap configuration:** Document the swap expectation across all nodes.
- **Query swap limits in pre-flight checks:** At node enrollment, record swap configuration and fail if inconsistent.
- **Separate tests:** Create two test suites — "Memory test (no swap)" and "Memory+Swap test".
- **Validation warning:** If swap is detected, add a note about the difference.

**Warning signs:**
- Stress test succeeds on some nodes, fails on others, despite identical configuration
- Node reports high swap usage (> 100MB) during stress tests
- Validation suite detects inconsistent swap configuration across nodes
- A job completes but with severe latency degradation

**Phase to address:**
**Phase 2 (Cgroup Pre-flight & Validation):** Detect and record swap configuration per node. Provide swap-aware stress test variants.

---

### Pitfall 8: Child Cgroup Limit Conflicts in Nested Runtimes (cgroup v2 Domain Threaded Mode)

**What goes wrong:**
The orchestrator tries to spawn a job container inside a node with memory and CPU limits. The inner Docker/Podman daemon fails with cgroup errors or silently creates a container with no limits. The inner runtime can't delegate cgroup subtrees to job containers because of domain threading constraints.

**Why it happens:**
- **cgroup v2 design:** Parent cgroups with domain controllers can't have child cgroups with the same controllers if the parent has active processes.
- **Domain threaded mode:** When a cgroup is set to "threaded," it can't have domain controllers. Mismatches cause conflicts.
- **Nested container runtimes:** The node container is a domain cgroup. The inner Docker daemon tries to create domain child cgroups, violating constraints.
- **Silent failure:** Some runtime versions don't error explicitly; they just create the child cgroup without the requested limits.

**How to avoid:**
- **Detect cgroup mode at enrollment:** Check if the node's cgroup is in "domain" or "threaded" mode and reject incompatible modes.
- **Pre-flight test:** At node enrollment, try to spawn a test container with memory limits. Fail enrollment if this fails.
- **Explicit cgroup parent delegation:** When spawning the node, use `--cgroup-parent=/nodes/<node-id>/` to create a delegated subtree.
- **Fall back to EXECUTION_MODE=direct:** If cgroup v2 domain conflicts are unavoidable, switch to direct execution mode.
- **Linux kernel version check:** Require kernel 5.14+ for reliable cgroup v2 delegation.

**Warning signs:**
- Inner Docker logs show "cgroup: permission denied" errors
- Job containers created with memory limits but they're silently ignored
- `GET /nodes` returns cgroup_type inconsistently
- Stress tests inside job containers can over-allocate memory

**Phase to address:**
**Phase 2 (Cgroup Pre-flight & Validation):** Implement cgroup.type detection and validation. Fail node enrollment if domain conflicts are detected.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using EXECUTION_MODE=direct for all DinD nodes | Avoids cgroup nesting complexity | Zero isolation; noisy neighbors; uncontrolled resource leaks | DinD-only MVP; plan migration ASAP |
| Stress tests without cgroup detection | Simpler test suite | Tests invalid on v1 or v2; false positives/negatives | Never — always detect and branch |
| Ignoring swap in stress tests | Simpler test | Inconsistent results across swap/no-swap environments | Only if swap is standardized everywhere |
| Page cache-blind memory validation | Simpler OOM trigger | False OOM kills from page cache | Only for non-I/O workloads; document |
| Single stress test script (all platforms) | One script to maintain | Fails on non-Linux; unreliable assertions | Never — maintain platform-specific variants |
| No admission control in direct mode | Node accepts unlimited jobs | All jobs compete; cascading failures | Only in experimental/dev environments |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **Job scheduler → node `/work/pull`** | Submit large job to node with insufficient memory, expecting rejection | Implement admission control in `job_service.py` BEFORE offering the job |
| **Docker/Podman inside node → cgroup limits** | Set `--memory` flag but assume inner runtime enforces it | Verify inner runtime actually created the cgroup via docker inspect |
| **Stress test → memory.stat parsing** | Read total memory without subtracting inactive file cache | Always parse memory.stat and subtract total_inactive_file for accurate heap |
| **Node heartbeat → cgroup detection** | Assume cgroup version from `/etc/os-release` | Actually read `/proc/self/cgroup` at runtime |
| **Multi-platform test suite → Bash/PowerShell branching** | One script with shell detection | Separate script repos per platform |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **Page cache pollution during stress** | Memory test succeeds but next job OOM-kills immediately | Clear page cache before stress tests | 10+ concurrent jobs; heavy I/O |
| **Swap thrashing under memory pressure** | Stress test completes with 100x latency degradation | Disable swap on validation nodes | Any environment with swap enabled |
| **OOM killer selection bias** | Some processes killed, others survive | Use single-process containers; monitor memory.events | 5+ processes per job container |
| **Child cgroup limit inheritance stalls** | Inner container creation slow (10s+) when limits deeply nested | Flatten cgroup hierarchy; use --cgroup-parent | DinD with 3+ nesting levels |
| **Memory limit enforcement latency** | Stress test allocates to limit but kernel takes 1-2s to enforce | Set memory.high to 80% of memory.max | Bursty workloads hitting limit exactly |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Allowing EXECUTION_MODE=direct with untrusted job code** | Malicious job runs natively; can access secrets and other jobs' data | Only allow direct mode for internal/trusted scripts. Add audit log event for direct-mode dispatch |
| **Not validating cgroup limits before dispatch** | Operator submits 100GB job to 8GB node; system becomes unresponsive | Implement pre-dispatch validation. Query node free memory. Reject jobs exceeding capacity |
| **Stress tests overwriting system settings** | Test script modifies sysctl; changes persist after test | Wrap stress tests in isolated container with `--security-opt=no-new-privileges` |
| **Page cache side-channel in multi-tenant nodes** | Stress test fills page cache; Job B's I/O patterns exposed | Stress test only on dedicated validation nodes |
| **Incomplete exit code mapping in validation** | Test interprets exit 0 as success despite OOM killer invocation | Cross-reference exit code with dmesg and memory.oom_control |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **Opaque "job failed" with no resource context** | Operator doesn't know if it's memory, CPU, timeout, or code error | Return detailed status: "Job killed by OOM at 512MB (limit: 512MB)" |
| **Memory requirement form accepting "512" without units** | Operator enters "512" intending 512MB, system interprets as bytes | Use explicit dropdown: "512 MB" not "512" |
| **Stress test result report without platform context** | Operator sees "Memory enforcement: PASS" but doesn't know it's v2-only | Report: "cgroup v1 [PASS/FAIL], cgroup v2 [PASS/FAIL], kernel 5.14+ [PASS/FAIL]" |
| **No indication of cgroup mode or limits in node detail view** | Operator can't see why job is being rejected | Show: current memory usage / limit, cgroup version, swap status |
| **Stress test canvas doesn't show overhead** | Operator thinks 512MB is true limit, but 70MB was overhead | Break down: "Requested: 512MB, Overhead: 35MB, Actual: 477MB" |

---

## "Looks Done But Isn't" Checklist

- [ ] **Cgroup Detection:** Validated on both v1 and v2 systems; kernel version doesn't determine result
- [ ] **Memory Enforcement:** Tests account for page cache; memory.stat parsed correctly; page cache subtraction validated
- [ ] **DinD Cgroup:** `--cgroup-parent` set correctly; inner container spawning with limits tested; domain threaded mode handled
- [ ] **Stress Tests:** Platform-specific (Bash for Linux, PowerShell for Windows); stress-ng or equivalent used
- [ ] **Swap Handling:** Swap configuration detected per node; separate test suites for swap/no-swap variants
- [ ] **Admission Control:** Node `/work/pull` validates free memory before accepting job
- [ ] **OOM Monitoring:** Exit code 137 = always OOM; kernel logs (`dmesg`) checked; memory.events/memory.oom_control verified
- [ ] **EXECUTION_MODE Awareness:** Direct mode documented as "no isolation"; limits trigger warnings; container mode used for validation
- [ ] **Child Cgroup Conflicts:** cgroup.type detected; nested runtime test performed at enrollment
- [ ] **Performance Baseline:** Page cache cleared before stress; swap disabled or documented; latency measured separately

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Stress test false positive (passes on v1, fails on v2)** | MEDIUM | Run version-specific test suite. Backport test to both versions. |
| **DinD cgroup limit ignored** | MEDIUM | Check `docker inspect` for actual memory limit. Verify `--cgroup-parent` was passed. Test inner container creation. |
| **Noisy neighbor (uncontrolled job starves others)** | HIGH | Kill offending job. Implement admission control in `/work/pull`. Require strict memory limits. |
| **OOM-killed process misidentified as "success"** | MEDIUM | Audit exit codes. Query memory.oom_control. Check dmesg. Re-run with verbose logging. |
| **Swap-induced latency (job succeeds but system unusable)** | MEDIUM | Disable swap on affected nodes. Re-run stress tests. Measure latency separately. |
| **Child cgroup conflict (domain threaded mode)** | HIGH | Fail node enrollment. Migrate node or revert to cgroup v1. Use `--cgroup-parent` to isolate. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| **Cgroup v1 vs v2 semantic mismatch** | Phase 1: Stress Test Corpus | Run stress tests on both versions; verify memory usage matches expected ranges |
| **Page cache surprise OOM kills** | Phase 2: Cgroup Pre-flight | Parse memory.stat; confirm page cache accounted for |
| **DinD cgroup inheritance** | Phase 2: Cgroup Pre-flight | Test job container creation inside node; verify limits enforced |
| **Invisible OOM kills** | Phase 2: Cgroup Pre-flight | Check memory.oom_control after job; verify single-process containers |
| **EXECUTION_MODE=direct isolation bypass** | Phase 2: Execution Mode Validation | Implement admission control; warn on ignored limits |
| **Stress test variation across architectures** | Phase 1: Stress Test Corpus | Maintain platform-specific test suites; run on Linux, Windows, Alpine |
| **Swap accounting differences** | Phase 2: Cgroup Pre-flight | Detect swap per node; run swap/no-swap test variants |
| **Child cgroup limit conflicts (cgroup v2)** | Phase 2: Cgroup Pre-flight | Detect cgroup.type at enrollment; test inner container creation |

---

## Sources

- [Resource constraints | Docker Docs](https://docs.docker.com/engine/containers/resource_constraints/)
- [About cgroup v2 | Kubernetes](https://kubernetes.io/docs/concepts/architecture/cgroups/)
- [Differences between cgroup v1 and cgroup v2 - Alibaba Cloud](https://www.alibabacloud.com/help/en/alinux/differences-between-cgroup-v1-and-cgroup-v2)
- [Memory Resource Controller — The Linux Kernel documentation](https://docs.kernel.org/admin-guide/cgroup-v1/memory.html)
- [Memory Controller · cgroup2](https://facebookmicrosites.github.io/cgroup2/docs/memory-controller.html)
- [Diagnosing Linux cgroups v2 Memory Throttling & OOM-Killed Containers | Netdata](https://www.netdata.cloud/academy/diagnosing-linux-cgroups/)
- [DevOps Scenario #11: Why Your Docker Container Exceeds Memory Limits | by Marjan Rafi | Medium](https://medium.com/@mdmarjanrafi/devops-scenario-11-why-your-docker-container-exceeds-memory-limits-deep-dive-into-cgroups-7c4930633d2c)
- [Specifying cgroup limits on a child container fails with cgroups v2 · Issue #6288 | docker/for-mac](https://github.com/docker/for-mac/issues/6288)
- [Docker runtime would overwrite memory limit of its cgroup parent | Issue #33876 | moby/moby](https://github.com/moby/moby/issues/33876)
- [Control Group v2 — The Linux Kernel documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [cgroup2: how can we support nested containers with domain controllers? · Issue #2356 | opencontainers/runc](https://github.com/opencontainers/runc/issues/2356)
- [Tracking Down "Invisible" OOM Kills in Kubernetes | by Richard Durso | Medium](https://medium.com/@reefland/tracking-down-invisible-oom-kills-in-kubernetes-192a3de33a60)
- [Kubernetes OOMKilled Error: How to Fix & Tips for Preventing It · Dash0](https://lumigo.io/kubernetes-troubleshooting/kubernetes-oomkilled-error-how-to-fix-and-tips-for-preventing-it/)
- [How to efficiently stress test Pod memory | Chaos Mesh](https://chaos-mesh.org/blog/how-to-efficiently-stress-test-pod-memory/)
- [Linux Process Isolation and Docker Containers | by Erdem Uysal | Medium](https://erdemuysalx.medium.com/linux-process-isolation-and-docker-containers-1d134ebb796c)
- [Eliminate the Noisy Neighbor Problem in Docker using Resource Limits](https://najer.org/najer/article/download/30/32)
- [How to Mount Cgroups Inside a Docker Container | linuxvox.com](https://linuxvox.com/blog/mounting-cgroups-inside-a-docker-container/)
- [Rootless Containers — cgroup v2](https://rootlesscontaine.rs/getting-started/common/cgroup2/)

---

*Pitfalls research for: Node Capacity & Isolation Validation (v20.0)*
*Researched: 2026-04-06*
