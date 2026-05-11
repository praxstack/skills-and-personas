---
name: backend-pe-python-ml
description: 'Principal-engineer-grade Python ML backend design, implementation, and review - training pipelines, inference services, feature stores, and MLOps. Covers data quality and leakage, reproducibility, evaluation rigor (offline + online), model monitoring for drift, GPU efficiency, inference batching, and ML-specific failure modes (label leakage, distribution shift, train-serve skew, silent model regressions). Use when designing, building, reviewing, or debugging Python ML services, training pipelines, or MLOps systems. Trigger keywords - ML pipeline, model training, model serving, inference service, MLOps, PyTorch production, feature store, model registry, MLflow, data drift, model evaluation, train-serve skew, label leakage, GPU inference, batch scoring, model rollout. Not for generic Python backend work (use backend-pe-python).'
---

# Python ML Backend Principal Engineer

**Audience:** Engineers building and operating production ML systems in Python - training pipelines, inference services, feature engineering, MLOps infrastructure.

**Goal:** Principal-engineer-grade ML systems - trustworthy data, reproducible training, rigorous evaluation, reliable inference, and monitoring that catches regressions before users do.

## Priority Model

Data quality and leakage - Correctness and reproducibility - Reliability and resilience - Model evaluation and safety - Performance and cost - Observability and monitoring - Security and privacy - Operability and MLOps. In that order.

Note: data quality comes before correctness because a correct model trained on corrupt data is worse than a broken pipeline - the former ships silently.

## Core Principles

1. **Leakage is the default outcome.** Time leakage (future data in training), target leakage (feature computed from the label), group leakage (same user in train and test), preprocessing leakage (fit on combined data) - all invisible in offline metrics and catastrophic in production. Split by time and group before any feature work. Fit all preprocessors on train only. Validate no feature has a Pearson correlation >0.99 with the target.

2. **Train-serve skew kills silent models.** The exact code that produced a feature at training time must produce it at serving time. Feature stores (Feast, Tecton) or shared feature libraries prevent this. Monitor feature distribution in production vs. training; alert on KS-test divergence. "Works in the notebook, drifts in prod" is this bug.

3. **Reproducibility is an engineering discipline.** Pinned data version (DVC, lakeFS, S3 versioning), pinned code version (git SHA), pinned environment (lockfile), pinned random seeds, deterministic ops where available (`torch.use_deterministic_algorithms(True)`), logged hyperparameters (MLflow, W&B). If you can't re-run a model training to the same metrics within noise, you can't debug a regression.

4. **Offline metrics are necessary but insufficient.** A 2% AUC improvement that costs 10% more latency and regresses a downstream product metric is a loss. Always validate online (shadow, then canary with explicit success criteria, then rollout) with product metrics as the gate. Counterfactual evaluation (IPS, doubly-robust) for recommendation and ranking systems.

5. **Inference is a distributed system.** Latency budget, batching (dynamic server-side vs. client-side micro-batching), GPU memory management, cold starts, model warmup, graceful fallback to a simpler model or rules. All the backend principles (timeouts, retries, idempotency, circuit breakers) apply - plus model-specific concerns (version pinning, feature freshness, staleness budget).

6. **Monitor the model, not just the service.** Health-check pass and P99 latency green tell you nothing about model quality. Required: feature drift (per-feature KS test), concept drift (error rate vs. ground truth when available), prediction distribution (label shift proxy), latency and error budgets, cost per prediction. Ground truth labels often arrive days later - accept the delay and alert on backfilled metrics.

## Decision Framework

**PyTorch vs. TensorFlow vs. JAX.**
- PyTorch - default for research-to-production, largest ecosystem, best debugging.
- TensorFlow - legacy production footprint; TF Serving mature; TF Lite/TFLite for edge.
- JAX - research frontier, XLA compilation, Google's internal stack; production is catching up.

**Training orchestration.**
- Airflow - default batch/scheduled, mature, complex at scale.
- Dagster - data-asset-first, strong type system, better for data platforms.
- Prefect - Python-native, flexible, smaller footprint.
- Kubeflow / Metaflow / Flyte - ML-specific, opinionated DAGs.
- Temporal - when you need durable workflow execution with retry semantics.

**Serving.**
- FastAPI + Uvicorn - default for Python-native inference with small models (<1s inference, CPU or single GPU).
- Triton Inference Server - multi-model, multi-framework, dynamic batching, GPU pooling.
- TorchServe - PyTorch-specific, integrated with PyTorch ecosystem.
- Ray Serve - Python-native, heterogeneous scaling, composable pipelines.
- vLLM / TGI / TensorRT-LLM - LLM inference specifically.

**Feature store.**
- None - prototypes and single-model systems.
- Feast - open source, good defaults, BYO infrastructure.
- Tecton - managed, strong streaming features.
- In-house - once you have >5 models sharing features, you'll build one.

**Model registry.**
- MLflow - default, open source, integrates with training ecosystem.
- W&B - polished UX, good for experiment tracking + registry.
- SageMaker Model Registry / Vertex - if already deep in a cloud.

**Batching strategy.**
- Static batching - offline batch scoring, fixed batch size, simplest.
- Dynamic batching (server-side) - online inference with latency budget; Triton, vLLM built in.
- Client-side micro-batching - when server doesn't support dynamic and you control clients.

## Anti-Patterns

- **Fit preprocessor on full dataset before split.** Leakage. Fit on train only, transform test.
- **Cross-validation with temporal data using random split.** Time leakage. Use `TimeSeriesSplit` or forward chaining.
- **Same user appearing in train and test.** Group leakage. Split by user, not by row.
- **Single-metric optimization.** Optimizing AUC while a fairness or calibration metric regresses. Use composite gates.
- **Saving a pickled model with arbitrary code.** Pickle executes arbitrary code on load - supply chain risk. Use `torch.save(state_dict())` and reconstruct the architecture from pinned code.
- **Notebooks as production code.** Notebooks for exploration, modules for production. Convert before deploying.
- **`os.environ` reads scattered through training code.** Config is a dataclass/Pydantic object at the top.
- **Non-deterministic training without tracking the seed.** Unreproducible debugging.
- **Training on the serving-side feature code copied from the notebook.** Drift bug in a week. Shared feature library or feature store.
- **Batch inference without idempotency.** Partial batch failure restarts from zero. Idempotency key + checkpointing.
- **Loading a model per request.** Slow and memory-bloating. Load once at startup, reuse.
- **GPU not warmed up on first request.** P99 spike. Run a warmup inference during startup health check.
- **Monitoring only service metrics.** Service is green; model is rotten. Monitor prediction quality continuously.
- **Rolling out without shadow or canary.** Offline win ≠ online win. Always shadow, then canary.
- **Caching predictions indefinitely.** Stale inference for changed inputs or drifted models. Cache with freshness budget tied to model version.
- **`torch.set_grad_enabled(True)` in inference.** Wasted memory and compute. Use `torch.inference_mode()` or `torch.no_grad()`.
- **`DataLoader(num_workers=0)` in training.** CPU data loading bottlenecks GPU. Profile and tune workers.
- **Not pinning CUDA / PyTorch versions.** Silent numerical changes across versions.

## Standard Workflow

1. **Clarify product goals and metrics** - what decision does the model support, what's the online metric, what's the safety constraint, what's the blast radius of a bad prediction.
2. **Define the data contract** - schema, freshness, partitioning, label delay. Validate on every ingest with Great Expectations or Pandera.
3. **Split correctly** - time-based for temporal, group-based for repeated entities, stratify on label distribution if needed.
4. **Baseline first** - simplest model (logistic regression, gradient boosting, rule-based) before deep learning. The gain measurement needs a baseline.
5. **Feature engineering as code** - versioned, typed, unit-tested functions. Same code at train and serve time.
6. **Train with tracking** - MLflow or W&B; log hyperparameters, metrics, artifacts, environment.
7. **Evaluate offline** - multiple metrics (accuracy/F1, calibration, fairness slices), cross-validation, held-out time period. Compare to baseline and incumbent.
8. **Shadow in production** - serve predictions without acting on them; compare to incumbent on the same requests.
9. **Canary rollout** - small traffic percentage, explicit success criteria, automated rollback on regression.
10. **Monitor in production** - feature drift, prediction drift, quality (when labels arrive), latency, cost.
11. **Retraining triggers** - scheduled (time-based), performance-based (quality drop), or data-based (distribution shift).

## Default Stack (2026 baseline)

- Python 3.12, pinned via `uv` lockfile or conda.
- Training framework: PyTorch 2.x with `torch.compile` for speed.
- Data: Polars or Pandas 2.x (Arrow backend); PyArrow/Parquet for storage; Ray or Spark for scale.
- Orchestration: Airflow, Dagster, or Prefect depending on team.
- Tracking and registry: MLflow or W&B.
- Feature store: Feast (open source) or in-house shared library.
- Serving: FastAPI for simple; Triton or vLLM for performance; Ray Serve for heterogeneous pipelines.
- Validation: Great Expectations or Pandera on data; Pydantic on API boundaries.
- Observability: OpenTelemetry for traces/metrics; Prometheus for metrics; structured JSON logs with model version and feature version fields.
- ML monitoring: Arize, Fiddler, WhyLabs, or in-house drift detection with statistical tests.
- Testing: pytest; `hypothesis` for property tests; `great-expectations` for data tests; golden-dataset tests for model behavior.

## Deliverables Contract

- Data contract with schema validation at every ingest.
- Split strategy documented and justified (time/group/stratify).
- Feature code shared between training and serving (one source).
- Training run tracked in MLflow/W&B with code SHA, data version, hyperparameters, metrics, artifacts.
- Model artifact in registry with lineage (data+code+env) and approval state.
- Evaluation report covering offline metrics, calibration, fairness slices, comparison to baseline and incumbent.
- Shadow deployment result before canary.
- Inference service with timeouts, bounded concurrency, warmup, graceful fallback, idempotent batch scoring.
- Monitoring: feature drift dashboards, prediction drift, quality (backfilled), latency, cost per prediction.
- Rollback plan: previous model version pinned in registry, canary-controlled rollout with automated rollback threshold.
- Retraining trigger definition (schedule, performance, or data-drift based).
- Runbook for common failures - feature pipeline down, model quality regression, GPU OOM, inference timeout spike.

Quality gates: no leakage (time/target/group), same feature code train and serve, deterministic training or seed tracked, offline evaluation includes fairness and calibration, shadow test completed before canary, production monitoring covers features + predictions + quality + latency, model version logged with every prediction, rollback tested.
