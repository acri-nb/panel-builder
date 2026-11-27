import { useEffect, useState } from "react";
import api from "../services/api";

const PAGE_SIZE = 25;
const PREVALENCE_TYPES = new Set([
  "point prevalence",
  "birth prevalence",
  "lifelong prevalence",
  "lifetime prevalence",
]);

function OrphanetResults({ term }) {
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const offset = (page - 1) * PAGE_SIZE;

  useEffect(() => {
    if (!term) return;

    const controller = new AbortController();

    api
      .get("/orphanet/diseases", {
        params: { q: term, limit: PAGE_SIZE, offset },
        signal: controller.signal,
      })
      .then(({ data }) => {
        if (!controller.signal.aborted) setResult(data);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setError("Unable to load Orphanet results.");
        }
      });

    return () => controller.abort();
  }, [term, offset]);

  function changePage(nextPage) {
    setResult(null);
    setError("");
    setPage(nextPage);
  }

  if (!term) {
    return <p className="text-muted">Search by disease or panel name to see Orphanet results.</p>;
  }

  if (error) return <div className="alert alert-danger">{error}</div>;
  if (!result) return <p role="status">Searching Orphanet...</p>;

  if (result.items.length === 0) {
    return <div className="alert alert-info">No Orphanet diseases found for “{term}”.</div>;
  }

  const totalPages = Math.ceil(result.total / PAGE_SIZE);

  return (
    <>
      <p className="text-muted">
        {result.total} matching {result.total === 1 ? "disease" : "diseases"}
      </p>

      <div className="table-responsive">
        <table className="table table-hover align-middle">
          <thead>
            <tr>
              <th scope="col">Source</th>
              <th scope="col">Disease</th>
              <th scope="col">Prevalence</th>
              <th scope="col">Age at onset</th>
              <th scope="col">Inheritance</th>
            </tr>
          </thead>
          <tbody>
            {result.items.map((disease) => {
              const prevalence = disease.epidemiology.filter((record) =>
                PREVALENCE_TYPES.has(record.prevalence_type?.trim().toLowerCase())
              );

              return (
                <tr key={disease.orpha_code}>
                  <td>{disease.source}</td>
                  <th scope="row" className="fw-normal">
                    {disease.orphanet_url ? (
                      <a href={disease.orphanet_url} target="_blank" rel="noreferrer">
                        {disease.disease_name}
                      </a>
                    ) : (
                      disease.disease_name
                    )}
                    <div className="small text-muted">ORPHA:{disease.orpha_code}</div>
                  </th>
                  <td>
                    {prevalence.length === 1 ? (
                      <>
                        {prevalence[0].prevalence_class ??
                          prevalence[0].reported_value ??
                          "Not available"}
                        <div className="small text-muted">
                          {[
                            prevalence[0].prevalence_type,
                            prevalence[0].prevalence_geography,
                          ].filter(Boolean).join(" · ")}
                        </div>
                      </>
                    ) : prevalence.length > 1 ? (
                      `${prevalence.length} prevalence records`
                    ) : (
                      "Not available"
                    )}

                    {disease.epidemiology.length > 0 && (
                      <details className="mt-2">
                        <summary>Epidemiology details</summary>
                        <ul className="small mt-2 mb-0 ps-3">
                          {disease.epidemiology.map((record) => (
                            <li key={record.epidemiology_id} className="mb-2">
                              <strong>{record.prevalence_type || "Measure unspecified"}</strong>
                              <div>
                                {[
                                  record.reported_value,
                                  record.prevalence_class,
                                  record.prevalence_qualification,
                                  record.prevalence_geography,
                                ].filter((value) => value != null && value !== "").join(" · ")}
                              </div>
                              {record.reference && <div>Reference: {record.reference}</div>}
                              {record.validation_status && <div>{record.validation_status}</div>}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </td>
                  <td>{disease.age_at_onset?.join(", ") || "Not available"}</td>
                  <td>{disease.inheritance?.join(", ") || "Not available"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="d-flex justify-content-center align-items-center gap-3 my-4">
          <button
            type="button"
            className="btn btn-outline-secondary"
            disabled={page === 1}
            onClick={() => changePage(page - 1)}
          >
            Previous
          </button>
          <span>Page {page} of {totalPages}</span>
          <button
            type="button"
            className="btn btn-outline-secondary"
            disabled={page >= totalPages}
            onClick={() => changePage(page + 1)}
          >
            Next
          </button>
        </div>
      )}
    </>
  );
}

export default OrphanetResults;