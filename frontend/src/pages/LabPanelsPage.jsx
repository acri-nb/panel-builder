import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";


function LabPanelsPage() {
  const [panels, setPanels] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [searchName, setSearchName] = useState("");
  const limit = 20;
  const [sourceChecks, setSourceChecks] = useState({});

  useEffect(() => {
    let cancelled = false;

    async function loadPanels() {
      setLoading(true);
      setError("");

      try {
        const response = await api.get("/panels", {
          params: {
            source_id: 7,
            name: searchName || undefined,
            limit,
            offset
          }
        });

        if (!cancelled) {
          setPanels(response.data.data);
          setTotal(response.data.total);
        }
      } catch {
        if (!cancelled) {
          setError("Unable to load laboratory panels.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadPanels();

    return () => {
      cancelled = true;
    };
  }, [offset, searchName]);








  async function checkSourceUpdates(panelId) {
    setSourceChecks((current) => ({
      ...current,
      [panelId]: { loading: true, data: null, error: "" },
    }));

    try {
      const response = await api.get(
        `/lab-panels/${panelId}/source-updates`
      );

      setSourceChecks((current) => ({
        ...current,
        [panelId]: {
          loading: false,
          data: response.data,
          error: "",
        },
      }));
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;

      setSourceChecks((current) => ({
        ...current,
        [panelId]: {
          loading: false,
          data: null,
          error:
            typeof detail === "string"
              ? detail
              : "Unable to check updates.",
        },
      }));
    }
  }






  async function handleDelete(panel) {
    const confirmed = window.confirm(
      `Delete "${panel.panel_name}"?`
    );

    if (!confirmed) return;

    try {
      await api.delete(`/panels/${panel.panel_id}`);

      setPanels((current) =>
        current.filter((item) => item.panel_id !== panel.panel_id)
      );

      setTotal((current) => current - 1);
    } catch {
      window.alert("Unable to delete the panel. Please try again.");
    }
  }



  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h1 className="mb-0" style={{ color: "#256fa1" }}>Laboratory Panels</h1>


      </div>



      <form
        className="d-flex gap-2 mb-3"
        onSubmit={(event) => {
          event.preventDefault();
          setOffset(0);
          setSearchName(searchInput.trim());
        }}
      >
        <input
          type="search"
          className="form-control"
          placeholder="Search laboratory panels by name..."
          aria-label="Laboratory panel name"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
        />

        <button type="submit" className="btn btn-primary"
          style={{ backgroundColor: "#477DAB", borderColor: "#1E646B" }}
        >
          Search
        </button>

        <button
          type="button"
          className="btn btn-outline-secondary"
          onClick={() => {
            setSearchInput("");
            setSearchName("");
            setOffset(0);
          }}
        >
          Clear
        </button>
      </form>











      {loading ? (
        <p>Loading laboratory panels...</p>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : (
        <>
          <p className="text-muted">{total} laboratory panels</p>

          {panels.length === 0 ? (
            <div className="alert alert-info">
              No laboratory panels on this page.
            </div>
          ) : (
            <div className="list-group">


              {panels.map((panel) => (
                <div
                  key={panel.panel_id}
                  className="list-group-item"
                >
                  <div className="d-flex justify-content-between align-items-start gap-3">
                    <div>
                      <Link
                        to={`/panels/${panel.panel_id}`}
                        className="text-decoration-none"
                      >
                        {/* #4B83B4 */}
                        <h5 className="mb-1" style={{ color: "#256fa1" }}>{panel.panel_name}</h5>
                      </Link>

                      <p className="mb-0 text-muted">
                        <strong>Relevant diseases:</strong>{" "}
                        {Array.isArray(panel.relevant_diseases)
                          ? panel.relevant_diseases.join(", ") || "N/A"
                          : panel.relevant_diseases || "N/A"}
                      </p>

                      {panel.is_copied && (
                        <div className="mt-2" aria-live="polite">
                          {sourceChecks[panel.panel_id]?.error && (
                            <div className="small text-danger">
                              {sourceChecks[panel.panel_id].error}
                            </div>
                          )}

                          {sourceChecks[panel.panel_id]?.data && (
                            <span
                              className={`badge ${sourceChecks[panel.panel_id].data.has_updates
                                ? "text-bg-success"
                                : "text-bg-secondary"
                                }`}
                            >
                              {sourceChecks[panel.panel_id].data.has_updates
                                ? "Updates available"
                                : "No updates"}
                            </span>
                          )}
                        </div>
                      )}


                    </div>

                    {/* <div className="d-flex gap-2"> */}
                    <div className="d-flex flex-wrap justify-content-end gap-2">




                      {panel.is_copied && (
                        <button
                          type="button"
                          className="btn btn-outline-success btn-sm"
                          // style={{ borderColor: "#365dca", color: "#365dca" }}
                          disabled={sourceChecks[panel.panel_id]?.loading}
                          onClick={() => checkSourceUpdates(panel.panel_id)}
                        >
                          {sourceChecks[panel.panel_id]?.loading
                            ? "Checking..."
                            : "Check updates"}
                        </button>

                      )}



                      {panel.is_copied &&
                        sourceChecks[panel.panel_id]?.data?.has_updates && (
                          <Link
                            to={`/lab-panels/${panel.panel_id}/source-updates`}
                            className="btn btn-outline-info btn-sm"
                          >
                            View updates
                          </Link>
                        )}

                      {/*  btn btn-outline-primary btn-sm*/}
                      <Link
                        to={`/lab-panels/${panel.panel_id}/edit`}
                        className="btn btn-outline-primary btn-sm"
                        // style={{ borderColor: "#36bdca", color: "#36bdca", backgroundColor: "transparent" }}
                      >
                        Modify
                      </Link>
                      <Link
                        to={`/lab-panels/${panel.panel_id}/changes`}
                        className="btn btn-outline-secondary btn-sm"
                      >
                        Review changes
                      </Link>

                      <button
                        type="button"
                        className="btn btn-outline-danger btn-sm"
                        onClick={() => handleDelete(panel)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}


            </div>
          )}
        </>
      )}






      <div className="d-flex gap-2 mt-3">
        <button
          className="btn btn-outline-secondary"
          disabled={loading || offset === 0}
          onClick={() => setOffset(Math.max(0, offset - limit))}
        >
          Previous
        </button>

        <button
          className="btn btn-outline-secondary"
          disabled={loading || Boolean(error) || offset + limit >= total}
          onClick={() => setOffset(offset + limit)}
        >
          Next
        </button>

        <Link to="/lab-panels/create" className="btn btn-primary ms-auto"
          style={{ backgroundColor: "#477DAB", borderColor: "#1E646B" }}
        >
          Create panel
        </Link>

        <Link to="/lab-panels/copy" className="btn btn-primary"
          style={{ backgroundColor: "#477DAB", borderColor: "#1E646B" }}>
          Copy panels
        </Link>






      </div>

    </div >


  );
}

export default LabPanelsPage;