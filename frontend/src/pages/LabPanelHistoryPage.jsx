import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";

function LabPanelHistoryPage() {
  const { panelId } = useParams();

  const [versions, setVersions] = useState([]);
  const [selectedNumber, setSelectedNumber] = useState(null);
  const [selectedVersion, setSelectedVersion] = useState(null);

  const [loading, setLoading] = useState(true);
  const [versionLoading, setVersionLoading] = useState(false);
  const [error, setError] = useState("");
  const [versionError, setVersionError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      setLoading(true);
      setError("");
      setVersions([]);
      setSelectedNumber(null);
      setSelectedVersion(null);

      try {
        const response = await api.get(
          `/panels/${panelId}/versions`
        );

        if (!cancelled) {
          setVersions(
            [...response.data].sort(
              (a, b) => b.version_number - a.version_number
            )
          );
        }
      } catch (err) {
        if (!cancelled) {
          const detail = err.response?.data?.detail;

          setError(
            typeof detail === "string"
              ? detail
              : "Unable to load version history."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadHistory();

    return () => {
      cancelled = true;
    };
  }, [panelId]);

  useEffect(() => {
    if (selectedNumber === null) return;

    let cancelled = false;

    async function loadVersion() {
      setVersionLoading(true);
      setVersionError("");
      setSelectedVersion(null);

      try {
        const response = await api.get(
          `/panels/${panelId}/versions/${selectedNumber}`
        );

        if (!cancelled) {
          setSelectedVersion(response.data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail = err.response?.data?.detail;

          setVersionError(
            typeof detail === "string"
              ? detail
              : "Unable to load this version."
          );
        }
      } finally {
        if (!cancelled) setVersionLoading(false);
      }
    }

    loadVersion();

    return () => {
      cancelled = true;
    };
  }, [panelId, selectedNumber]);

  function display(value) {
    if (Array.isArray(value)) {
      return value.join("; ") || "N/A";
    }

    return value === null || value === undefined || value === ""
      ? "N/A"
      : String(value);
  }

  return (
    <div className="container mt-4 mb-5">
      <h2>Laboratory Panel Version History</h2>
      <p className="text-muted">Panel ID: {panelId}</p>

     

      {loading ? (
        <p>Loading version history...</p>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : versions.length === 0 ? (
        <div className="alert alert-info">No versions found.</div>
      ) : (
        <div className="table-responsive">
          <table className="table table-bordered">
            <thead>
              <tr>
                <th>Version</th>
                <th>Panel name</th>
                <th>Last updated</th>
                <th>Details</th>
              </tr>
            </thead>

            <tbody>
              {versions.map((version, index) => (
                <tr key={version.panel_version_id}>
                  <td>
                    {version.version_number}
                    {index === 0 && (
                      <span className="badge text-bg-info ms-2">
                        Latest
                      </span>
                    )}
                  </td>

                  <td>{version.panel_name}</td>
                  <td>{display(version.last_updated)}</td>

                  <td>
                    <button
                      type="button"
                      className="btn btn-outline-light btn-sm"
                      style={{ backgroundColor: "#477DAB", borderColor: "#1E646B" }}
                      disabled={versionLoading}
                      onClick={() =>
                        setSelectedNumber(version.version_number)
                      }
                    >
                      View version
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}





 



      {versionLoading && <p>Loading selected version...</p>}

      {versionError && (
        <div className="alert alert-danger">{versionError}</div>
      )}

      {selectedVersion && (
        <div className="card mt-4" style={{ border: "1px solid #256fa1" }}>
          <div className="card-header" style={{ backgroundColor: "#C7DDF0", border: "1px solid #256fa1" }}>
            <h4 className="mb-0" style={{ color: "#256FA1" }}>
              Version {selectedVersion.version}
            </h4>
          </div>

          <div className="card-body">
            <p>
              <strong>Panel name:</strong>{" "}
              {display(selectedVersion.panel_name)}
            </p>
            <p>
              <strong>Disease group:</strong>{" "}
              {display(selectedVersion.disease_group)}
            </p>
            <p>
              <strong>Disease subgroup:</strong>{" "}
              {display(selectedVersion.disease_subgroup)}
            </p>
            <p>
              <strong>Relevant diseases:</strong>{" "}
              {display(selectedVersion.relevant_diseases)}
            </p>
            <p>
              <strong>Last updated:</strong>{" "}
              {display(selectedVersion.last_updated)}
            </p>

            <h5 style={{ color: "#256FA1" }}>  Genes ({selectedVersion.genes.length})</h5>

            {selectedVersion.genes.length === 0 ? (
              <p>No genes in this version.</p>
            ) : (
              <div className="table-responsive">
                <table className="table table-striped">
                  <thead>
                    <tr>
                      <th>Gene</th>
                      <th>Confidence</th>
                      <th>Phenotypes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedVersion.genes.map((gene, index) => (
                      <tr key={index}>
                        <td>{display(gene.gene_symbol)}</td>
                        <td>{display(gene.confidence_level)}</td>
                        <td>{display(gene.phenotypes)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <h5 style={{ color: "#256FA1" }}>STRs ({selectedVersion.strs.length})</h5>

            {selectedVersion.strs.length === 0 ? (
              <p>No STRs in this version.</p>
            ) : (
              <div className="table-responsive">
                <table className="table table-striped">
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
                    {selectedVersion.strs.map((str, index) => (
                      <tr key={index}>
                        <td>{display(str.entity_name)}</td>
                        <td>{display(str.gene_symbol)}</td>
                        <td>{display(str.confidence_level)}</td>
                        <td>{display(str.phenotypes)}</td>
                        <td>{display(str.repeated_sequence)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      
      <div className="d-flex gap-3 mb-3">
        <Link to="/lab-panels"  className="btn btn-outline-dark" >Back to laboratory panels</Link>
        <Link to={`/panels/${panelId}`}  className="btn btn-outline-dark" >View current panel</Link>
      </div>

    </div>
  );
}

export default LabPanelHistoryPage;