import { useCallback, useEffect, useState } from "react";
import api from "../services/api";
import { useNavigate } from "react-router-dom";


const actions = ["create", "update", "remove"];
const externalSources = [
  "PanelApp AUS",
  "PanelApp UK",
  "Blueprint Genetics",
  "Ontario Health",
  "ClinGen",
  "GenCC",
  "Orphanet",
];

function SourceReviewButtons({ source,
  count,
  sourceBulkAction,
  runningUpdates,
  submitting,
  onReview,
  onRun, }) {
  const disabled =
    count === 0 ||
    Boolean(sourceBulkAction) ||
    runningUpdates ||
    source === "Unknown";

  return (
    <div className="d-flex flex-column gap-1 mt-2">
      <button
        type="button"
        className="btn btn-sm btn-outline-primary"
        disabled={
          runningUpdates ||
          Boolean(sourceBulkAction) ||
          submitting ||
          !externalSources.includes(source)
        }
        onClick={() => onRun(source)}
      >
        Run update
      </button>

      <button
        type="button"
        className="btn btn-sm btn-outline-success"
        disabled={disabled}
        onClick={() => onReview(source, "approve", count)}
      >
        {sourceBulkAction === `${source}:approve`
          ? "Approving..."
          : `Approve all (${count})`}
      </button>
      <button
        type="button"
        className="btn btn-sm btn-outline-danger"
        disabled={disabled}
        onClick={() => onReview(source, "reject", count)}
      >
        {sourceBulkAction === `${source}:reject`
          ? "Rejecting..."
          : `Reject all (${count})`}
      </button>
    </div>
  );
}

// const actionStyles = {
//   create: "table-success",
//   update: "table-primary",
//   remove: "table-danger",
// };

function ExternalUpdatesPage() {
  const navigate = useNavigate();
  const [changes, setChanges] = useState([]);
  const [expandedGroups, setExpandedGroups] = useState([]);
  const [selectedChange, setSelectedChange] = useState(null);
  const [inspected, setInspected] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [runningUpdates, setRunningUpdates] = useState(false);
  const [cancellingUpdate, setCancellingUpdate] = useState(false);
  const [sourceBulkAction, setSourceBulkAction] = useState(null);
  const [sourceBulkResult, setSourceBulkResult] = useState(null);
  const [updateRunId, setUpdateRunId] = useState(null);
  const [updateSummary, setUpdateSummary] = useState(null);
  const [error, setError] = useState("");

  const loadChanges = useCallback(async () => {
    const allChanges = [];
    const limit = 50;
    let offset = 0;
    let page;

    do {
      const response = await api.get("/external-changes", {
        params: { limit, offset },
      });

      page = response.data;
      allChanges.push(...page);
      offset += limit;
    } while (page.length === limit);

    setChanges(allChanges);
  }, []);

  useEffect(() => {
    async function load() {
      try {
        await loadChanges();
      } catch {
        setError("Could not load external changes.");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [loadChanges]);

  useEffect(() => {
    let stopped = false;

    async function restoreActiveRun() {
      try {
        const response = await api.get("/external-updates/active-run");
        if (stopped || !response.data) return;

        setUpdateSummary(response.data);
        setUpdateRunId(response.data.run_id);
        setRunningUpdates(true);
      } catch {
        // Keep the pending-change page usable if progress cannot be restored.
      }
    }

    restoreActiveRun();

    return () => {
      stopped = true;
    };
  }, []);

  function toggleGroup(groupKey) {
    setExpandedGroups((current) =>
      current.includes(groupKey)
        ? current.filter((key) => key !== groupKey)
        : [...current, groupKey]
    );
  }

  async function inspectChange(changeId) {
    setSelectedChange(null);
    setInspected(false);
    setConfirmAction(null);
    setError("");
    setDetailsLoading(true);

    try {
      const response = await api.get(`/external-changes/${changeId}`);
      setSelectedChange(response.data);
    } catch {
      setError("Could not load this change request.");
    } finally {
      setDetailsLoading(false);
    }
  }

  async function submitDecision() {
    if (!selectedChange || !confirmAction) return;

    setSubmitting(true);
    setError("");

    try {
      await api.post(
        `/external-changes/${selectedChange.change_id}/${confirmAction}`
      );

      await loadChanges();
      setSelectedChange(null);
      setInspected(false);
      setConfirmAction(null);
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
        `Could not ${confirmAction} this change.`
      );
      setConfirmAction(null);
    } finally {
      setSubmitting(false);
    }
  }

  async function runAllUpdates() {
    if (runningUpdates || sourceBulkAction || submitting) return;

    setRunningUpdates(true);
    setError("");

    try {
      const response = await api.post("/external-updates/run-all");
      setUpdateSummary(response.data);
      setUpdateRunId(response.data.run_id);
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;

      // If another browser started the run, join its progress instead of
      // replacing the current summary with an error.
      if (detail && typeof detail === "object" && detail.run_id) {
        setUpdateRunId(detail.run_id);
        return;
      }

      setRunningUpdates(false);
      setError(typeof detail === "string"
        ? detail
        : detail?.message || "Could not run the external source updates.");
    }
  }



  async function runSourceUpdate(source) {
    if (runningUpdates || sourceBulkAction || submitting) return;

    setRunningUpdates(true);
    setError("");

    try {
      const response = await api.post(
        `/external-updates/run/${encodeURIComponent(source)}`
      );

      setUpdateSummary(response.data);
      setUpdateRunId(response.data.run_id);
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;

      // Reconnect to the existing run if another update is active.
      if (detail && typeof detail === "object" && detail.run_id) {
        setUpdateRunId(detail.run_id);
        return;
      }

      setRunningUpdates(false);
      setError(
        typeof detail === "string"
          ? detail
          : detail?.message || `Could not run updates for ${source}.`
      );
    }
  }

  async function cancelRun() {
    if (!updateRunId || cancellingUpdate) return;

    setCancellingUpdate(true);
    setError("");

    try {
      const response = await api.post(
        `/external-updates/runs/${updateRunId}/cancel`
      );
      setUpdateSummary(response.data);
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(typeof detail === "string"
        ? detail
        : detail?.message || "Could not cancel the update run.");
    } finally {
      setCancellingUpdate(false);
    }
  }

  async function reviewAllForSource(source, decision, changeCount) {
    if (sourceBulkAction || runningUpdates) return;

    const decisionLabel = decision === "approve" ? "approve" : "reject";
    const confirmed = window.confirm(
      `I have inspected every pending change for ${source}. Do you want to ${decisionLabel} all ${changeCount} change(s) from this source?`
    );
    if (!confirmed) return;

    setSourceBulkAction(`${source}:${decision}`);
    setSourceBulkResult(null);
    setError("");

    try {
      const response = await api.post(
        `/external-changes/source/${encodeURIComponent(source)}/${decision}`
      );
      setSourceBulkResult(response.data);

      try {
        await loadChanges();
      } catch {
        setError(
          "The source changes were reviewed, but the pending list could not be reloaded."
        );
      }
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
        `Could not ${decisionLabel} all changes for ${source}.`
      );
    } finally {
      setSourceBulkAction(null);
    }
  }

  useEffect(() => {
    if (!updateRunId) return undefined;

    let stopped = false;
    let pollTimer;

    async function checkRunProgress() {
      try {
        const response = await api.get(
          `/external-updates/runs/${updateRunId}`
        );
        if (stopped) return;

        const run = response.data;
        setError("");
        setUpdateSummary(run);

        if (["queued", "running", "cancelling"].includes(run.status)) {
          pollTimer = setTimeout(checkRunProgress, 1200);
          return;
        }

        setRunningUpdates(false);
        setUpdateRunId(null);

        try {
          await loadChanges();
        } catch {
          setError(
            "Updates finished, but the pending changes could not be reloaded."
          );
        }
      } catch {
        if (!stopped) {
          setError("Could not check update progress. Retrying...");
          pollTimer = setTimeout(checkRunProgress, 2000);
        }
      }
    }

    checkRunProgress();

    return () => {
      stopped = true;
      clearTimeout(pollTimer);
    };
  }, [updateRunId, loadChanges]);

  const sources = [
    ...new Set([
      ...externalSources,
      ...changes.map((change) => change.source || "Unknown"),
    ]),
  ];

  const finishedSourceCount = updateSummary?.sources?.filter(
    (sourceResult) =>
      ["completed", "failed", "cancelled"].includes(sourceResult.status)
  ).length || 0;
  // const totalSourceCount = updateSummary?.total_sources || 6;
  const totalSourceCount = updateSummary?.total_sources || externalSources.length;
  const progressPercent = Math.round(
    (finishedSourceCount / totalSourceCount) * 100
  );

  const proposal = selectedChange?.proposed_data || {};
  const differences = proposal.changes || {};
  const metadata = differences.metadata || {};
  const genes = differences.genes || {};
  const strs = differences.strs || {};

  return (
    <div className="container mt-4">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <h1 className="mb-0" style={{ color: "#256fa1" }}>Pending Updates</h1>
        <div className="d-flex gap-2">
          <button
            type="button"
            className="btn btn-outline-danger"
            onClick={cancelRun}
            disabled={
              !runningUpdates ||
              !updateRunId ||
              cancellingUpdate ||
              updateSummary?.cancel_requested
            }
          >
            {cancellingUpdate || updateSummary?.cancel_requested
              ? "Cancelling after current source..."
              : "Cancel update"}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={runAllUpdates}
            disabled={runningUpdates || Boolean(sourceBulkAction) || submitting}
          >
            {runningUpdates ? "Running source updates..." : "Run all updates"}
          </button>
        </div>
      </div>

      {loading && <p>Loading pending changes...</p>}
      {error && <div className="alert alert-danger">{error}</div>}

      {sourceBulkResult && (
        <div className={`alert ${sourceBulkResult.failed_count ? "alert-warning" : "alert-success"}`}>
          {sourceBulkResult.source}: {sourceBulkResult.decision === "approve" ? "approved" : "rejected"} {sourceBulkResult.success_count} of {sourceBulkResult.total} pending changes.
          {sourceBulkResult.failed_count > 0 && (
            <>
              <div>{sourceBulkResult.failed_count} change(s) could not be processed:</div>
              <ul className="mb-0 mt-2">
                {sourceBulkResult.results
                  .filter((result) => result.status === "failed")
                  .map((result) => (
                    <li key={result.change_id}>
                      Change #{result.change_id}: {result.error}
                    </li>
                  ))}
              </ul>
            </>
          )}
        </div>
      )}

      {updateSummary && (
        <div className={`alert ${["completed", "queued", "running", "cancelling"].includes(updateSummary.status) ? "alert-info" : "alert-warning"}`}>
          <h2 className="h6">Update run: {updateSummary.status}</h2>
          <p className="mb-2">
            {updateSummary.cancel_requested
              ? "Cancellation requested. The current source will finish before the remaining sources are skipped."
              : updateSummary.current_source
                ? `Updating ${updateSummary.current_source} (${Math.min(finishedSourceCount + 1, totalSourceCount)} of ${totalSourceCount})`
                : `${finishedSourceCount} of ${totalSourceCount} sources complete`}
          </p>
          <div
            className="progress mb-3"
            role="progressbar"
            aria-label="External source update progress"
            aria-valuenow={progressPercent}
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div
              className="progress-bar bg-success"
              style={{ width: `${progressPercent}%` }}
            >
              {progressPercent > 0 ? `${finishedSourceCount}/${totalSourceCount} complete` : ""}
            </div>
            {runningUpdates && updateSummary.current_source && (
              <div
                className="progress-bar progress-bar-striped progress-bar-animated"
                style={{ width: `${100 / totalSourceCount}%` }}
                aria-label={`${updateSummary.current_source} is running`}
              />
            )}
          </div>
          <div className="table-responsive mb-0">
            <table className="table table-sm align-middle mb-0">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Compared</th>
                  <th>New</th>
                  <th>Changed</th>
                  <th>Unchanged</th>
                  <th>Removed</th>
                </tr>
              </thead>
              <tbody>
                {updateSummary.sources.map((sourceResult) => (
                  <tr key={sourceResult.source}>
                    <td>{sourceResult.source}</td>
                    <td className={
                      sourceResult.status === "failed"
                        ? "text-danger"
                        : sourceResult.status === "cancelled" || sourceResult.status === "waiting"
                          ? "text-muted"
                          : sourceResult.status === "running"
                            ? "text-primary"
                            : "text-success"
                    }>
                      {sourceResult.status}
                      {sourceResult.error && (
                        <div className="small text-danger">{sourceResult.error}</div>
                      )}
                    </td>
                    <td>{sourceResult.compared}</td>
                    <td>{sourceResult.new}</td>
                    <td>{sourceResult.changed}</td>
                    <td>{sourceResult.unchanged}</td>
                    <td>{sourceResult.removed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && !error && changes.length === 0 && (
        <div className="alert alert-info">No pending external changes.</div>
      )}

      {!loading && !error && (
        <div className="table-responsive">
          <table className="table table-bordered align-middle">
            <thead className="table-light">
              <tr>
                <th>Source</th>
                <th>Action</th>
                <th>Pending requests</th>
              </tr>
            </thead>

            <tbody>
              {sources.map((source) => {
                const sourceChanges = changes.filter(
                  (change) => (change.source || "Unknown") === source
                );

                const groups = actions
                  .map((action) => ({
                    action,
                    panels: sourceChanges.filter(
                      (change) => change.action === action
                    ),
                  }))
                  .filter((group) => group.panels.length > 0);

                if (groups.length === 0) {
                  return (
                    <tr key={`${source}-no-pending`}>
                      <th scope="row" className="bg-light">
                        <div>{source}</div>
                        <SourceReviewButtons
                          source={source}
                          count={sourceChanges.length}
                          sourceBulkAction={sourceBulkAction}
                          runningUpdates={runningUpdates}
                          onReview={reviewAllForSource}
                          onRun={runSourceUpdate}
                          submitting={submitting}
                        />
                      </th>
                      <td colSpan={2} className="text-muted">
                        {sourceChanges.length === 0
                          ? "No pending changes"
                          : "Pending changes have an unrecognized action type"}
                      </td>
                    </tr>
                  );
                }

                return groups.map((group, index) => {
                  const groupKey = `${source}-${group.action}`;
                  const expanded = expandedGroups.includes(groupKey);
                  const visiblePanels = expanded
                    ? group.panels
                    : group.panels.slice(0, 3);

                  return (
                    <tr
                      key={groupKey}

                    >
                      {index === 0 && (
                        <th
                          scope="row"
                          rowSpan={groups.length}
                          className="bg-light"
                        >
                          <div>{source}</div>
                          <SourceReviewButtons
                            source={source}
                            count={sourceChanges.length}
                            sourceBulkAction={sourceBulkAction}
                            runningUpdates={runningUpdates}
                            onReview={reviewAllForSource}
                            onRun={runSourceUpdate}
                            submitting={submitting}
                          />
                        </th>
                      )}


                      <td
                        className={
                          group.action === "create"
                            ? "bg-success-subtle"
                            : group.action === "update"
                              ? "bg-primary-subtle"
                              : "bg-danger-subtle"
                        }
                      >
                        <strong className="text-capitalize text-dark">
                          {group.action}
                        </strong>{" "}
                        <span className="badge text-bg-light">
                          {group.panels.length}
                        </span>
                      </td>


                      {/* <td className="text-capitalize">
                        <strong
                          className={
                            group.action === "remove"
                              ? "text-danger"
                              : group.action === "create"
                                ? "text-success"
                                : "text-primary"
                          }
                        >
                          {group.action}
                        </strong>{" "}
                        <span className="badge text-bg-light">
                          {group.panels.length}
                        </span>
                      </td> */}



                      <td>
                        {visiblePanels.map((change) => (
                          <div key={change.change_id} className="mb-1">
                            <button
                              type="button"
                              className={`btn btn-sm text-dark text-start border-0 me-2 mb-2 ${group.action === "create"
                                ? "bg-success-subtle"
                                : group.action === "update"
                                  ? "bg-primary-subtle"
                                  : "bg-danger-subtle"
                                }`}
                              // className="btn btn-sm btn-outline-secondary text-start me-2 mb-2"
                              // className="btn btn-link link-dark text-decoration-none text-start p-0"
                              onClick={() =>
                                navigate(`/external-updates/change/${change.change_id}`)
                              }
                            >
                              {/* {change.panel_name || "Unnamed panel"} */}
                              {change.target === "orphanet_disease" ? (
                                <>
                                  {change.disease_name || "Unnamed disease"}
                                  {change.orpha_code != null && ` · ORPHA:${change.orpha_code}`}
                                </>
                              ) : (
                                change.panel_name || "Unnamed panel"
                              )}
                            </button>
                          </div>
                        ))}

                        {group.panels.length > 3 && (
                          <button
                            type="button"
                            className="btn btn-link link-secondary text-decoration-none p-0 mt-1"
                            // className="btn btn-sm btn-outline-secondary mt-2"
                            onClick={() => toggleGroup(groupKey)}
                          >
                            {expanded
                              ? "Show fewer"
                              : `View ${group.panels.length - 3} more`}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                });
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* {detailsLoading && <p>Loading change details...</p>}

      {selectedChange && (
        <div className="card mt-4 mb-5">
          <div className="card-body">
            <div className="d-flex justify-content-between align-items-start">
              <div>
                <h2 className="h4">
                  {proposal.data?.panel_name || "Unnamed panel"}
                </h2>
                <p className="text-muted mb-3">
                  {proposal.data?.source} · {proposal.action} · Request #
                  {selectedChange.change_id}
                </p>
              </div>

              <button
                type="button"
                className="btn-close"
                aria-label="Close details"
                onClick={() => setSelectedChange(null)}
              />
            </div>

            <h3 className="h6">Metadata changes</h3>
            {Object.keys(metadata).length === 0 ? (
              <p className="text-muted">None listed.</p>
            ) : (
              <ul>
                {Object.entries(metadata).map(([field, change]) => (
                  <li key={field}>
                    <strong>{field}:</strong>{" "}
                    {JSON.stringify(change.old) ?? "—"} →{" "}
                    {JSON.stringify(change.new) ?? "—"}
                  </li>
                ))}
              </ul>
            )}

            <h3 className="h6">Gene changes</h3>
            <p>
              Added: {genes.added?.length || 0} · Removed:{" "}
              {genes.removed?.length || 0} · Modified:{" "}
              {genes.modified?.length || 0}
            </p>

            <h3 className="h6">STR changes</h3>
            <p>
              Added: {strs.added?.length || 0} · Removed:{" "}
              {strs.removed?.length || 0} · Modified:{" "}
              {strs.modified?.length || 0}
            </p>

            {!inspected && (
              <button
                type="button"
                className="btn btn-outline-primary"
                onClick={() => setInspected(true)}
              >
                I have inspected this change
              </button>
            )}

            {inspected && !confirmAction && (
              <div className="d-flex gap-2">
                <button
                  type="button"
                  className="btn btn-success"
                  onClick={() => setConfirmAction("approve")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => setConfirmAction("reject")}
                >
                  Reject
                </button>
              </div>
            )}

            {confirmAction && (
              <div className="alert alert-warning mt-3 mb-0">
                <p>
                  Are you sure you want to {confirmAction} this change?
                </p>
                <button
                  type="button"
                  className={`btn me-2 ${confirmAction === "approve"
                    ? "btn-success"
                    : "btn-danger"
                    }`}
                  disabled={submitting}
                  onClick={submitDecision}
                >
                  {submitting
                    ? `${confirmAction === "approve" ? "Approving" : "Rejecting"}...`
                    : `Yes, ${confirmAction}`}
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  disabled={submitting}
                  onClick={() => setConfirmAction(null)}
                >
                  Inspect changes again
                </button>
              </div>
            )}
          </div>
        </div>
      )} */}
    </div>
  );
}

export default ExternalUpdatesPage;

