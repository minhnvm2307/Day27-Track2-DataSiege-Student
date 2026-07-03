"""
Your defense. Implement register(ctx) and a handler per event type.
See ../README.md for the full interface + toolkit reference, and
../RULES.md before you start.
"""
from api import Verdict


def _baseline(ctx, key, default=None):
    return ctx.baseline.get(key, default)


def _tool_error(result):
    return isinstance(result, dict) and "error" in result


def _out_of_range(value, minimum=None, maximum=None):
    if minimum is not None and value < minimum:
        return True
    if maximum is not None and value > maximum:
        return True
    return False


def register(ctx):
    ctx.on("data_batch", check_data_batch)
    ctx.on("contract_checkpoint", check_contract_checkpoint)
    ctx.on("lineage_run", check_lineage_run)
    ctx.on("feature_materialization", check_feature_materialization)
    ctx.on("embedding_batch", check_embedding_batch)


def check_data_batch(payload, ctx):
    profile = ctx.tools.batch_profile(payload["batch_id"])
    if _tool_error(profile):
        return Verdict(alert=False, pillar="checks", reason=profile["error"])

    row_count = profile.get("row_count")
    null_rate = (profile.get("null_rate") or {}).get("customer_id")
    mean_amount = profile.get("mean_amount")
    staleness_min = profile.get("staleness_min")

    if _out_of_range(row_count, _baseline(ctx, "row_count_min"), _baseline(ctx, "row_count_max")):
        return Verdict(alert=True, pillar="checks", reason="row_count_out_of_bounds")
    if null_rate is not None and null_rate > _baseline(ctx, "null_rate_max"):
        return Verdict(alert=True, pillar="checks", reason="null_rate_high")
    if _out_of_range(mean_amount, _baseline(ctx, "mean_amount_min"), _baseline(ctx, "mean_amount_max")):
        return Verdict(alert=True, pillar="checks", reason="mean_amount_out_of_bounds")
    if staleness_min is not None and staleness_min > _baseline(ctx, "staleness_min_max"):
        return Verdict(alert=True, pillar="checks", reason="staleness_too_high")

    return Verdict(alert=False, pillar="checks")


def check_contract_checkpoint(payload, ctx):
    diff = ctx.tools.contract_diff(payload["contract_id"], payload["checkpoint_batch_id"])
    if _tool_error(diff):
        return Verdict(alert=False, pillar="contracts", reason=diff["error"])

    freshness_delay_min = diff.get("freshness_delay_min")
    violations = diff.get("violations") or []

    if freshness_delay_min is not None and freshness_delay_min > _baseline(ctx, "freshness_delay_max_min"):
        return Verdict(alert=True, pillar="contracts", reason="freshness_delay_high")
    if violations:
        return Verdict(alert=True, pillar="contracts", reason=",".join(sorted(violations)))

    return Verdict(alert=False, pillar="contracts")


def check_lineage_run(payload, ctx):
    graph = ctx.tools.lineage_graph_slice(payload["run_id"], depth=2)
    if _tool_error(graph):
        return Verdict(alert=False, pillar="lineage", reason=graph["error"])

    duration_ms = graph.get("duration_ms")
    actual_upstream = graph.get("actual_upstream") or []
    actual_downstream_count = graph.get("actual_downstream_count")
    upstream_count = len(actual_upstream) if hasattr(actual_upstream, "__len__") else 0

    duration_threshold = _baseline(ctx, "lineage_duration_ms_max")
    if duration_threshold is not None:
        duration_threshold *= 0.95
    if duration_ms is not None and duration_threshold is not None and duration_ms > duration_threshold:
        return Verdict(alert=True, pillar="lineage", reason="runtime_anomaly")
    if not actual_upstream:
        return Verdict(alert=True, pillar="lineage", reason="missing_upstream")
    if actual_downstream_count is not None and actual_downstream_count <= 1:
        return Verdict(alert=True, pillar="lineage", reason="orphaned_output")
    if actual_downstream_count is not None and upstream_count >= 3 and actual_downstream_count == 1:
        return Verdict(alert=True, pillar="lineage", reason="orphaned_output")

    return Verdict(alert=False, pillar="lineage")


def check_feature_materialization(payload, ctx):
    drift = ctx.tools.feature_drift(payload["feature_view"], payload["batch_id"])
    if _tool_error(drift):
        return Verdict(alert=False, pillar="ai_infra", reason=drift["error"])

    mean_shift_sigma = drift.get("mean_shift_sigma")
    threshold = _baseline(ctx, "feature_mean_shift_sigma_max")
    if threshold is not None:
        threshold = max(0.0, threshold - 0.03)
    if mean_shift_sigma is not None and threshold is not None and mean_shift_sigma > threshold:
        return Verdict(alert=True, pillar="ai_infra", reason="feature_skew")

    return Verdict(alert=False, pillar="ai_infra")


def check_embedding_batch(payload, ctx):
    drift = ctx.tools.embedding_drift(payload["corpus"], payload["chunk_batch_id"])
    if _tool_error(drift):
        return Verdict(alert=False, pillar="ai_infra", reason=drift["error"])

    centroid_shift = drift.get("centroid_shift")
    avg_doc_age_days = drift.get("avg_doc_age_days")

    if centroid_shift is not None and centroid_shift > _baseline(ctx, "embedding_centroid_shift_max"):
        return Verdict(alert=True, pillar="ai_infra", reason="embedding_drift")
    if avg_doc_age_days is not None and avg_doc_age_days > _baseline(ctx, "corpus_avg_doc_age_days_max"):
        return Verdict(alert=True, pillar="ai_infra", reason="corpus_staleness")

    return Verdict(alert=False, pillar="ai_infra")
