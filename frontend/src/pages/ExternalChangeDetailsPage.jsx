import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import api from "../services/api";

function showValue(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (Array.isArray(value)) {
    return value.join(", ");
  }

  return String(value);
}



function ChangeList({ title, items, nameField }) {
  if (!items?.length) return null;

  return (
    <div className="mb-3">
      <h3 className="h6">{title} ({items.length})</h3>
      <ul className="mb-0">
        {items.map((item, index) => (
          <li key={index}>
            <strong>{item[nameField] || item.identity || "Unnamed"}</strong>
            {item.confidence_level && ` — ${item.confidence_level}`}

            {item.changes && (
              <ul>
                {Object.entries(item.changes).map(([field, values]) => (
                  <li key={field}>
                    {field}: {showValue(values.old)} →{" "}
                    {showValue(values.new)}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}


function ExternalChangeDetailsPage() {
  const navigate = useNavigate();
  const [inspected, setInspected] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [decisionError, setDecisionError] = useState("");
  const { changeId } = useParams();
  const [change, setChange] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sourceChanges, setSourceChanges] = useState([]);
  const [navigationLoading, setNavigationLoading] = useState(false);
  const [navigationError, setNavigationError] = useState("");

  // useEffect(() => {
  //   async function loadChange() {
  //     try {
  //       const response = await api.get(`/external-changes/${changeId}`);
  //       setChange(response.data);
  //     } catch {
  //       setError("Could not load this change request.");
  //     } finally {
  //       setLoading(false);
  //     }
  //   }
  //   loadChange();
  // }, [changeId]);




  useEffect(() => {
    let stopped = false;

    setLoading(true);
    setError("");
    setChange(null);
    setInspected(false);
    setConfirmAction(null);
    setDecisionError("");

    async function loadChange() {
      try {
        const response = await api.get(`/external-changes/${changeId}`);

        if (!stopped) setChange(response.data);
      } catch {
        if (!stopped) setError("Could not load this change request.");
      } finally {
        if (!stopped) setLoading(false);
      }
    }

    loadChange();

    return () => {
      stopped = true;
    };
  }, [changeId]);




  const changeSource =
    change?.data?.source ||
    change?.current_data?.source ||
    change?.source;

  useEffect(() => {
    let stopped = false;

    setSourceChanges([]);
    setNavigationError("");

    if (!changeSource) return;

    setNavigationLoading(true);

    async function loadSourceChanges() {
      try {
        const allChanges = [];
        const limit = 50;
        let offset = 0;

        while (true) {
          const response = await api.get("/external-changes", {
            params: { limit, offset },
          });

          if (stopped) return;

          allChanges.push(...response.data);

          if (response.data.length < limit) break;
          offset += limit;
        }

        setSourceChanges(
          allChanges.filter((item) => item.source === changeSource)
        );
      } catch {
        if (!stopped) {
          setNavigationError("Could not load next/previous changes.");
        }
      } finally {
        if (!stopped) setNavigationLoading(false);
      }
    }

    loadSourceChanges();

    return () => {
      stopped = true;
    };
  }, [changeSource, changeId]);

  const currentChangeIndex = sourceChanges.findIndex(
    (item) => String(item.change_id) === String(changeId)
  );

  const previousChange =
    currentChangeIndex > 0
      ? sourceChanges[currentChangeIndex - 1]
      : null;

  const nextChange =
    currentChangeIndex >= 0
      ? sourceChanges[currentChangeIndex + 1]
      : null;













  async function submitDecision() {
    if (!change || !confirmAction || submitting) return;

    setSubmitting(true);
    setDecisionError("");

    try {
      await api.post(
        `/external-changes/${change.change_id}/${confirmAction}`
      );

      navigate("/external-updates");
    } catch (requestError) {
      setDecisionError(
        requestError.response?.data?.detail ||
        `Could not ${confirmAction} this change.`
      );
      setConfirmAction(null);
    } finally {
      setSubmitting(false);
    }
  }




  if (loading) {
    return <div className="container mt-4">Loading change...</div>;
  }

  if (error) {
    return <div className="container mt-4 alert alert-danger">{error}</div>;
  }

  const action = change.action;
  const data = change.data || {};
  const current = change.current_data || {};
  const differences = change.changes || {};
  const metadata = differences.metadata || {};
  const genes = differences.genes || {};
  const strs = differences.strs || {};

  return (
    <div className="container mt-4 mb-5">
      {/* <Link to="/external-updates" className="btn btn-outline-secondary mb-4">
        Back to external updates
      </Link> */}

      <div className="d-flex flex-wrap align-items-center gap-2 mb-4">
        <Link
          to="/external-updates"
          className="btn btn-outline-secondary"
        >
          Back to external updates
        </Link>

        <button
          type="button"
          className="btn btn-outline-primary"
          disabled={navigationLoading || submitting || !previousChange}
          onClick={() =>
            navigate(`/external-updates/change/${previousChange.change_id}`)
          }
        >
          Previous change
        </button>

        <button
          type="button"
          className="btn btn-outline-primary"
          disabled={navigationLoading || submitting || !nextChange}
          onClick={() =>
            navigate(`/external-updates/change/${nextChange.change_id}`)
          }
        >
          Next change
        </button>

        {navigationLoading ? (
          <span className="small text-muted">Loading navigation...</span>
        ) : currentChangeIndex >= 0 ? (
          <span className="small text-muted">
            {currentChangeIndex + 1} of {sourceChanges.length}
            {" "}— {changeSource}
          </span>
        ) : null}
      </div>

      {navigationError && (
        <div className="alert alert-warning">{navigationError}</div>
      )}

      <h1 className="h3">{data.panel_name || current.panel_name}</h1>
      <p className="text-muted">
        {data.source || current.source || "Unknown source"} ·{" "}
        <span className="text-capitalize">{action}</span> · Request #
        {change.change_id}
      </p>

      {/* {action === "remove" && (
        <div className="alert alert-danger">
          Approving this request will make this panel inactive.
        </div>
      )} */}

      {!change.changes && (
        <div className="alert alert-warning">
          This request has no saved change breakdown. It may have been
          created before change details were saved.
        </div>
      )}

      {action === "create" && (
        <>
          <h2 className="h5 mt-4">Proposed panel</h2>
          <p><strong>Disease group:</strong> {showValue(data.disease_group)}</p>
          <p><strong>Disease subgroup:</strong> {showValue(data.disease_subgroup)}</p>
          <p><strong>Relevant diseases:</strong> {showValue(data.relevant_diseases)}</p>
          <p><strong>Lab:</strong> {showValue(data.lab_name)}</p>
          <h2 className="h5 mt-4">Genes ({data.genes?.length || 0})</h2>
          {data.genes?.length ? (
            <ul>
              {data.genes.map((gene, index) => (
                <li key={index}>
                  {gene.gene_symbol}
                  {gene.confidence_level && ` — ${gene.confidence_level}`}
                </li>
              ))}
            </ul>
          ) : (
            <p>No genes.</p>
          )}

          <h2 className="h5 mt-4">STRs ({data.strs?.length || 0})</h2>
          {data.strs?.length ? (
            <ul>
              {data.strs.map((str, index) => (
                <li key={index}>
                  {str.entity_name} — {str.gene_symbol || "Unknown gene"}
                </li>
              ))}
            </ul>
          ) : (
            <p>No STRs.</p>
          )}
        </>
      )}

      {action === "update" && (
        <>
          <h2 className="h5 mt-4">Metadata changes</h2>
          {Object.keys(metadata).length === 0 ? (
            <p>No metadata changes recorded.</p>
          ) : (
            <table className="table table-bordered">
              <thead>
                <tr><th>Field</th><th>Current</th><th>Proposed</th></tr>
              </thead>
              <tbody>
                {Object.entries(metadata).map(([field, values]) => (
                  <tr key={field}>
                    <td>{field}</td>
                    <td>{showValue(values.old)}</td>
                    <td>{showValue(values.new)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {action === "remove" && (
        <>
          <div className="alert alert-danger">
            Approving this request will make this panel inactive.
          </div>

          <h2 className="h5 mt-4">Existing panel</h2>
          <p><strong>Panel ID:</strong> {change.panel_id}</p>
          <p><strong>Name:</strong> {showValue(current.panel_name)}</p>
          <p><strong>Disease group:</strong> {showValue(current.disease_group)}</p>
          <p><strong>Disease subgroup:</strong> {showValue(current.disease_subgroup)}</p>
          <p><strong>Relevant diseases:</strong> {showValue(current.relevant_diseases)}</p>
          {current.lab_name && (
            <p><strong>Lab:</strong> {current.lab_name}</p>
          )}

          <h2 className="h5 mt-4">Genes ({current.genes?.length || 0})</h2>
          {current.genes?.length ? (
            <ul>
              {current.genes.map((gene, index) => (
                <li key={index}>
                  {gene.gene_symbol}
                  {gene.confidence_level && ` — ${gene.confidence_level}`}
                </li>
              ))}
            </ul>
          ) : (
            <p>No genes.</p>
          )}

          <h2 className="h5 mt-4">STRs ({current.strs?.length || 0})</h2>
          {current.strs?.length ? (
            <ul>
              {current.strs.map((str, index) => (
                <li key={index}>
                  {str.entity_name} — {str.gene_symbol || "Unknown gene"}
                </li>
              ))}
            </ul>
          ) : (
            <p>No STRs.</p>
          )}
        </>
      )}

      {action === "update" && change.changes && (
        <>
          <h2 className="h5 mt-4">Gene changes</h2>
          {!genes.added?.length &&
            !genes.removed?.length &&
            !genes.modified?.length ? (
            <p>No gene changes.</p>
          ) : (
            <>
              <ChangeList
                title="Added"
                items={genes.added}
                nameField="gene_symbol"
              />
              <ChangeList
                title="Removed"
                items={genes.removed}
                nameField="gene_symbol"
              />
              <ChangeList
                title="Modified"
                items={genes.modified}
                nameField="gene_symbol"
              />
            </>
          )}

          <h2 className="h5 mt-4">STR changes</h2>
          {!strs.added?.length &&
            !strs.removed?.length &&
            !strs.modified?.length ? (
            <p>No STR changes.</p>
          ) : (
            <>
              <ChangeList
                title="Added"
                items={strs.added}
                nameField="entity_name"
              />
              <ChangeList
                title="Removed"
                items={strs.removed}
                nameField="entity_name"
              />
              <ChangeList
                title="Modified"
                items={strs.modified}
                nameField="entity_name"
              />
            </>
          )}
        </>
      )}




      {decisionError && (
        <div className="alert alert-danger mt-4">{decisionError}</div>
      )}

      {change.status !== "pending" ? (
        <div className="alert alert-secondary mt-4">
          This request is {change.status}.
        </div>
      ) : (
        <div className="border-top pt-4 mt-4">
          {!inspected ? (
            <button
              type="button"
              className="btn btn-outline-primary"
              onClick={() => setInspected(true)}
            >
              I have inspected this change
            </button>
          ) : !confirmAction ? (
            <div className="d-flex gap-2">
              <button
                type="button"
                className="btn btn-success"
                disabled={
                  (action === "update" || action === "remove") &&
                  !change.current_data
                }
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
          ) : (
            <div className="alert alert-warning mb-0">
              <p>
                Are you sure you want to {confirmAction} this request?
              </p>

              <button
                type="button"
                className={
                  confirmAction === "approve"
                    ? "btn btn-success me-2"
                    : "btn btn-danger me-2"
                }
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

          {(action === "update" || action === "remove") &&
            !change.current_data && (
              <p className="text-muted mt-2">
                Approval needs a fresh comparison with a saved panel snapshot.
              </p>
            )}
        </div>
      )}





    </div>
  );
}

export default ExternalChangeDetailsPage;