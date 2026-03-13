# Admin tools[](#admin-tools)

Lightning gives infrastructure and MLOps teams the power to support AI/ML research without becoming the bottleneck. Infra teams define secure, cost-controlled development environments \(Studios\), while researchers move fast inside them. No more handholding. No more firefighting. When prototypes are ready, they seamlessly transition to production - no rewrites, no duplicated pipelines.

Researchers get freedom. Infra teams get control.


Select an Image

## Monitor infrastructure[](#monitor-infrastructure)

Infra teams are responsible for uptime but lack observability into compute usage. When things break, they find out too late, without enough context. Lightning provides live dashboards and detailed metrics. Stay ahead of issues and optimize compute usage before problems arise.


Select an Image

With built-in dashboards and Grafana views, Lightning helps you monitor everything:

  - CPU/GPU/memory/network utilization per node

  - Cluster-level utilization breakdowns

  - Historical metrics for long-term planning

  - Idle resource detection to reduce waste


## Get alerts when things fail[](#get-alerts-when-things-fail)

Infra teams are pulled into fire drills, often without clarity on what's broken. Debugging is reactive, slow, and detached from context. Lightning alerts infra teams the moment something fails. Fast response, less downtime, no more detective work.


Select an Image

Lightning's automated alerts notify you of issues in real-time, with stack traces, logs, and metadata for diagnosis. Infra teams only step in when needed - with everything they need to act fast.

## Customize environments[](#customize-environments)

Researchers require different packages and compute types; managing these is complex. Inconsistent environments and frequent requests for manual changes. Infra teams define reusable base images and compute configs. Researchers stay productive. Infra keeps control.


Select an Image

Build custom base images with pinned packages and apt configs. Define compute templates \(e.g. 8CPU-32GB, A100x2\) and set limits on scale, zones, or GPUs. Use your own bare metal or cloud accounts.

## Control compute usage[](#control-compute-usage)

Infra has no clean way to allocate credits, enforce policies, or audit users.Teams overrun budgets, misuse compute, or access resources they shouldn't. Lightning lets infra assign credits, manage users, and isolate work by TeamSpace. Governance without friction.


Select an Image

## Control data access[](#control-data-access)

AI data lives everywhere - across S3 buckets, Snowflake tables, shared drives, and on-prem clusters. Centralizing access is hard. Deciding who gets access to what is even harder. Most infra teams end up managing access manually, or not at all.


Select an Image

Lightning gives you a unified layer of control across storage backends and compute environments - so you can define, restrict, and audit access without chasing files or users.

  - Connect S3, GCS, Snowflake, or on-prem storage to specific TeamSpaces

  - Control which users and services can read, write, or modify data

  - Lock access by job type \(e.g. training vs deployment vs public app\)

  - Prevent accidental data exposure from shared or public Studios

  - Track access over time for auditability and compliance


No more “how do I get access to this bucket?” emails. You define the rules once. Lightning enforces them everywhere.

## Reduce costs[](#reduce-costs)

Infra teams struggle to control spend across clouds, users, and idle workloads. Organizations overpay for GPUs, leave resources idle, and lack visibility. Lightning automates cost savings with smart provisioning, shutdowns, and real-time monitoring. Lower infrastructure spend without sacrificing performance or researcher velocity.


Select an Image

Lightning gives you the tools to control and reduce infrastructure costs at scale:

  - Auto-select the cheapest GPU across clouds with built-in arbitrage logic

  - Preprovision machines automatically based on usage by project

  - Shut down idle resources automatically with configurable inactivity thresholds

  - Track real-time costs by user, team, and project across all compute and storage

  - Visualize GPU/CPU utilization to catch overprovisioned jobs or underutilized resources

  - Assign the right GPU for the job so developers don't waste A100s on notebooks

  - Manage multi-cloud storage from a single dashboard to avoid sprawl and duplication


No more guessing. No more waste. Just optimized usage and full transparency.

## Manage multi-cloud compute[](#manage-multi-cloud-compute)

Lightning lets infra admins manage compute across different cloud providers including their own clouds. Without lightning, teams struggle with GPU availability, unifying data across storage solutions like EFS, S3, GCS, etc. As a result, this operational complexity slows down development . With Lightning multi-cloud, teams can shop the best GPU prices, unify data sources, and remove vendor lock-in.


Select an Image

Use Lightning to bring your own cloud accounts \(AWS, GCP, Azure, on-prem\) and auto-provision the best available GPUs, connect your own buckets, run jobs and manage data across clouds from a single interface.

## Unblock AI teams[](#unblock-ai-teams)

Production teams try to enforce production tooling too early, slowing research. Innovation stalls, and prototypes don't survive handoff. AI developers get lightweight tools during prototyping. Lightning creates a smooth path to go from prototype to production. More ideas make it to production, faster.


Select an Image

Lightning separates concerns:

  - Researchers prototype in Studios with familiar tools \(VS Code, Jupyter\)

  - Infra owns the environments, governance, and production transition

  - When ready, deploy directly from Studio without rewrites


## Enforce security, compliance[](#enforce-security-compliance)

Infra teams are responsible for data access, identity, and auditability - but are often left out of fast-moving AI workflows. This creates risk and forces teams to bolt on controls after the fact. Lightning bakes security and compliance into the platform from day one.


Select an Image

Lightning gives infra teams full control over who can access what, with enterprise-grade access and identity controls:

  - Enforce SSO \(e.g., Okta, Google Workspace, Azure AD\)

  - Manage users and groups with role-based access

  - Scope access to compute, storage, and environments per TeamSpace

  - Use service accounts for automation with scoped credentials

  - Audit usage by user, resource, and time

  - Apply access rules that match internal policy


Everything is centralized and traceable - so compliance isn’t an afterthought.

# Summary[](#summary)

Infra teams are no longer the bottleneck. With Lightning, they become the platform owners that enable research velocity and production readiness - at the same time.

