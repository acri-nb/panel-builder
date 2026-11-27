import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";
import LabChangeComparison from "../components/LabChangeComparison";

function LabPanelChangesPage() {
  const { panelId } = useParams();

  const [changes, setChanges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadChanges() {
      setLoading(true);
      setError("");
      setMessage("");

      try {
        const response = await api.get(
          `/panels/${panelId}/changes`
        );

        if (!cancelled) {
          setChanges(response.data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail = err.response?.data?.detail;

          setError(
            typeof detail === "string"
              ? detail
              : "Unable to load change requests."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadChanges();

    return () => {
      cancelled = true;
    };
  }, [panelId]);

  async function reviewChange(changeId, action) {
    const confirmed = window.confirm(
      action === "approve"
        ? "Approve this request and create a new panel version?"
        : "Reject this request? The panel will remain unchanged."
    );

    if (!confirmed || busy) return;

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const response = await api.post(
        `/changes/${changeId}/${action}`
      );

      setChanges((current) =>
        current.map((change) =>
          change.change_id === changeId
            ? { ...change, status: response.data.status }
            : change
        )
      );

      setMessage(
        action === "approve"
          ? `Change approved. Version ${response.data.version_number} created.`
          : "Change rejected. The panel remains unchanged."
      );
    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : "Unable to review this request."
      );
    } finally {
      setBusy(false);
    }
  }

  function displayPhenotypes(values) {
    return Array.isArray(values)
      ? values.join("; ") || "N/A"
      : values || "N/A";
  }

  return (
    <div className="container mt-4 mb-5"  >
      <h2>Laboratory Change Requests</h2>

     

      {error && (
        <div className="alert alert-danger">{error}</div>
      )}

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      {loading ? (
        <p>Loading change requests...</p>
      ) : (
        <>
          {!error && changes.length === 0 && (
            <div className="alert alert-info">
              No change requests for this panel.
            </div>
          )}

          {changes.map((change) => {
            const proposed = change.proposed_data || {};
            const genes = proposed.genes || [];
            const strs = proposed.strs || [];

            return (
              <div className="card mb-3" key={change.change_id}>
                <div className="card-body" style={{ border: "1px solid #256fa1" }}>
                  <div className="d-flex justify-content-between align-items-start">
                    <h5 style={{ color: "#005c99" }}>
                      Request #{change.change_id}
                    </h5>

                    <span
                      className={`badge ${
                        change.status === "pending"
                          ? "text-bg-warning"
                          : change.status === "approved"
                            ? "text-bg-success"
                            : "text-bg-danger"
                      }`}
                    >
                      {change.status}
                    </span>
                  </div>

                  <p className="text-muted mb-2">
                    Submitted:{" "}
                    {change.created_at
                      ? new Date(change.created_at).toLocaleString()
                      : "N/A"}
                  </p>

                  <details className="mb">
                    <summary className="mb-3" style={{ color: "#007f95" }}>
                      View proposed panel
                    </summary>

                    <p>
                      <strong >Panel name:</strong>{" "}
                      {proposed.panel_name || "N/A"}
                    </p>

                    <p>
                      <strong>Disease group:</strong>{" "}
                      {proposed.disease_group || "N/A"}
                    </p>

                    <p>
                      <strong>Disease subgroup:</strong>{" "}
                      {proposed.disease_subgroup || "N/A"}
                    </p>

                    <p>
                      <strong>Relevant diseases:</strong>{" "}
                      {proposed.relevant_diseases || "N/A"}
                    </p>

                    <p>
                      <strong>Last updated:</strong>{" "}
                      {proposed.last_updated || "N/A"}
                    </p>

                    <h5 style={{ color: "#007f95" }}>Proposed genes ({genes.length})</h5>

                    {genes.length === 0 ? (
                      <p>No genes in the proposal.</p>
                    ) : (
                      <div className="table-responsive" >
                        <table className="table table-bordered table-sm"  >
                          <thead>
                            <tr>
                              <th>Gene</th>
                              <th>Confidence</th>
                              <th>Phenotypes</th>
                            </tr>
                          </thead>
                          <tbody>
                            {genes.map((gene, index) => (
                              <tr key={index}>
                                <td>{gene.gene_symbol}</td>
                                <td>
                                  {gene.confidence_level ?? "N/A"}
                                </td>
                                <td>
                                  {displayPhenotypes(gene.phenotypes)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    <h5 style={{ color: "#007f95" }}>Proposed STRs ({strs.length})</h5>

                    {strs.length === 0 ? (
                      <p>No STRs in the proposal.</p>
                    ) : (
                      <div className="table-responsive">
                        <table className="table table-bordered table-sm">
                          <thead>
                            <tr>
                              <th>Entity</th>
                              <th>Gene</th>
                              <th>Confidence</th>
                              <th>Phenotypes</th>
                              <th>Repeated sequence</th>
                            </tr>
                          </thead>
                          <tbody>
                            {strs.map((str, index) => (
                              <tr key={index}>
                                <td>{str.entity_name}</td>
                                <td>{str.gene_symbol}</td>
                                <td>
                                  {str.confidence_level ?? "N/A"}
                                </td>
                                <td>
                                  {displayPhenotypes(str.phenotypes)}
                                </td>
                                <td>
                                  {str.repeated_sequence || "N/A"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </details>

                  <LabChangeComparison
                    panelId={panelId}
                    change={change}
                  />

                  {change.status === "pending" && (
                    <div className="d-flex gap-2 ms-auto">
                      <button
                        type="button"
                        className="btn btn-success btn-sm"
                        disabled={busy}
                        onClick={() =>
                          reviewChange(change.change_id, "approve")
                        }
                      >
                        Approve
                      </button>

                      <button
                        type="button"
                        className="btn btn-outline-danger btn-sm"
                        disabled={busy}
                        onClick={() =>
                          reviewChange(change.change_id, "reject")
                        }
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </>
      )}

       <div className="d-flex gap-3 mb-3">
        <Link to="/lab-panels" className="btn btn-outline-secondary" >Back to laboratory panels</Link>
        <Link to={`/panels/${panelId}`} className="btn btn-outline-secondary" >View current panel</Link>
      </div>

    </div>
  );
}

export default LabPanelChangesPage;