import { Link } from "react-router-dom";

const GROUPED_SOURCES = new Set(["GenCC", "ClinGen", "Ontario Health"]);
const PANEL_NAME_STYLE = { color: "#4B83B4" };

function SearchResults({ results, loading, error, hasSearched }) {
  if (loading) {
    return (
      <div className="mt-4 text-center">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <p className="mt-2">Searching...</p>
      </div>
    );
  }

  if (error) {
    return <div className="alert alert-danger mt-4">{error}</div>;
  }

  if (hasSearched && results.length === 0) {
    return <div className="alert alert-info mt-4">No results found.</div>;
  }

  if (!hasSearched) {
    return null;
  }

  return (
    <div className="mt-4">
      <div className="list-group">
        {results.map((panel, index) => {
          const records = Array.isArray(panel.records) ? panel.records : [];
          const recordCount = Number(panel.record_count ?? records.length);
          const shouldGroup =
            panel.isGrouped && GROUPED_SOURCES.has(panel.source);

          // Ontario Health: one record links directly to its panel details.
          if (
            shouldGroup &&
            panel.source === "Ontario Health" &&
            recordCount === 1 &&
            records[0]?.panel_id != null
          ) {
            const record = records[0];

            return (
              <Link
                key={record.panel_id}
                to={`/panels/${record.panel_id}`}
                className="list-group-item list-group-item-action"
              >
                <h5 className="mb-1" style={PANEL_NAME_STYLE}>{panel.panel_name}</h5>
                <p className="mb-1">
                  <strong style={{ color: "#256fa1" }}>Source:</strong> Ontario Health
                </p>
                <p className="mb-0 text-muted">
                  <strong style={{ color: "#256fa1" }} >Lab:</strong> {record.lab_name || "N/A"}
                  {" · "}
                  <strong style={{ color: "#256fa1" }}>Panel ID:</strong> {record.panel_id}
                </p>
              </Link>
            );
          }

          // Ontario Health: show each lab when a name has multiple records.
          if (shouldGroup && panel.source === "Ontario Health") {
            return (
              <div
                key={`${panel.source}-${panel.panel_name}-${index}`}
                className="list-group-item"
              >
                <h5 className="mb-1" style={PANEL_NAME_STYLE}>{panel.panel_name}</h5>
                <p className="mb-1">
                  <strong style={{ color: "#256fa1" }}>Source:</strong> {panel.source}
                </p>

                {recordCount > 1 ? (
                  <details>
                    <summary
                      className="text-muted"
                      style={{ cursor: "pointer" }}
                    >
                      <strong style={{ color: "#256fa1" }}>Records:</strong> {recordCount}
                    </summary>
                    <div className="list-group mt-2">
                      {records.map((record) => (
                        <Link
                          key={record.panel_id}
                          to={`/panels/${record.panel_id}`}
                          className="list-group-item list-group-item-action"
                        >
                          <strong>Lab:</strong> {record.lab_name || "N/A"}
                          {" · "}
                          <strong>Panel ID:</strong> {record.panel_id}
                        </Link>
                      ))}
                    </div>
                  </details>
                ) : (
                  records.map((record) => (
                    <Link
                      key={record.panel_id}
                      to={`/panels/${record.panel_id}`}
                      className="list-group-item list-group-item-action mt-2"
                    >
                      <strong>Lab:</strong> {record.lab_name || "N/A"}
                      {" · "}
                      <strong>Panel ID:</strong> {record.panel_id}
                    </Link>
                  ))
                )}
              </div>
            );
          }

          // GenCC and ClinGen: group matching names; a single record links
          // directly to its panel details.
          if (
            shouldGroup &&
            (panel.source === "GenCC" || panel.source === "ClinGen")
          ) {
            const singleRecord = records[0] || panel;

            if (recordCount === 1 && singleRecord.panel_id != null) {
              return (
                <Link
                  key={singleRecord.panel_id}
                  to={`/panels/${singleRecord.panel_id}`}
                  className="list-group-item list-group-item-action"
                >
                  <h5 className="mb-1" style={PANEL_NAME_STYLE}>{panel.panel_name}</h5>
                  <p className="mb-1">
                    <strong style={{ color: "#256fa1" }}>Source:</strong> {panel.source}
                  </p>
                </Link>
              );
            }

            return (
              <Link
                key={`${panel.source}-${panel.panel_name}-${index}`}
                to={`/grouped-disease/${encodeURIComponent(
                  panel.source
                )}/${encodeURIComponent(panel.panel_name)}`}
                className="list-group-item list-group-item-action"
              >
                <div className="d-flex justify-content-between align-items-start">
                  <div>
                    <h5 className="mb-1" style={PANEL_NAME_STYLE}>{panel.panel_name}</h5>
                    <p className="mb-1">
                      <strong style={{ color: "#256fa1" }}>Source:</strong> {panel.source}
                    </p>
                    {recordCount > 1 && (
                      <p className="mb-0 text-muted">
                        <strong style={{ color: "#256fa1" }}>Records:</strong> {recordCount}
                      </p>
                    )}
                  </div>
                  <span className="badge text-bg-secondary">View</span>
                </div>
              </Link>
            );
          }

          // Other sources link to each underlying panel, even if the search
          // response wraps the panel in a one-name group.
          const individualPanels =
            panel.isGrouped && Array.isArray(panel.records)
              ? panel.records
              : [panel];

          return individualPanels.map((record, recordIndex) => {
            if (record.panel_id == null) {
              return null;
            }

            return (
              <Link
                key={`${panel.source}-${record.panel_id}-${recordIndex}`}
                to={`/panels/${record.panel_id}`}
                className="list-group-item list-group-item-action"
              >
                <div className="d-flex justify-content-between align-items-start">
                  <div>
                    <h5 className="mb-1">
                      <span style={PANEL_NAME_STYLE}>
                        {record.panel_name || panel.panel_name}
                      </span>
                    </h5>

                    {panel.source === "Ontario Health" && (
                      <p className="mb-1 text-muted">
                        <strong>Lab:</strong> {record.lab_name || "N/A"}
                      </p>
                    )}

                    <p className="mb-1">
                      <strong style={{ color: "#256fa1" }}>Source:</strong>{" "}
                      {record.source || panel.source || "N/A"}
                    </p>

                    <p className="mb-0 text-muted">
                      <strong style={{ color: "#256fa1" }}>Disease Group:</strong>{" "}
                      {record.disease_group || panel.disease_group || "N/A"}
                    </p>
                  </div>
                  <span className="badge text-bg-secondary">View</span>
                </div>
              </Link>
            );
          });
        })}
      </div>
    </div>
  );
}

export default SearchResults;

 





