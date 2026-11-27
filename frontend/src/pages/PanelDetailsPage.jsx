import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";





function hasChildPanelEntries(panel, genes = [], strs = []) {
  if (!["PanelApp UK", "PanelApp AUS"].includes(panel.source)) {
    return false;
  }

  if (
    Array.isArray(panel.child_panel_ids) &&
    panel.child_panel_ids.length > 0
  ) {
    return true;
  }

  return (
    panel.source_panel_id != null &&
    [...genes, ...strs].some(
      (entry) =>
        entry.origin_panel_id != null &&
        String(entry.origin_panel_id) !== String(panel.source_panel_id)
    )
  );
}


function PanelDetailsPage() {
  const { panelId } = useParams();

  const [panel, setPanel] = useState(null);
  const [genes, setGenes] = useState([]);
  const [strs, setStrs] = useState([]);

  const getConfidenceStyle = (confidence) => {
    switch (String(confidence).toLowerCase()) {
      case "3":
      case "green":
        return {
          backgroundColor: "#d1e7dd",
          color: "#0f5132",
          border: "1px solid #badbcc",
        };

      case "2":
      case "amber":
      case "orange":
      case "yellow":
        return {
          backgroundColor: "#fff3cd",
          color: "#664d03",
          border: "1px solid #ffecb5",
        };

      case "1":
      case "red":
        return {
          backgroundColor: "#f8d7da",
          color: "#842029",
          border: "1px solid #f5c2c7",
        };

      case "definitive":
        return {
          backgroundColor: "#b7dfc8",
          color: "#14532d",
          border: "1px solid #95c9aa",
        };

      case "strong":
        return {
          backgroundColor: "#d2eadb",
          color: "#24613d",
          border: "1px solid #b8dcc6",
        };

      case "moderate":
        return {
          backgroundColor: "#e4f2e9",
          color: "#376c4b",
          border: "1px solid #cfe5d7",
        };

      case "supportive":
        return {
          backgroundColor: "#dbeafe",
          color: "#1e4f7a",
          border: "1px solid #bfd9f2",
        };

      case "limited":
        return {
          backgroundColor: "#fbe3e5",
          color: "#8a3e45",
          border: "1px solid #f3cdd1",
        };

      case "disputed":
        return {
          backgroundColor: "#f4c8cc",
          color: "#7a2931",
          border: "1px solid #eab3b9",
        };

      case "refuted":
        return {
          backgroundColor: "#e9aeb5",
          color: "#641c25",
          border: "1px solid #dc929b",
        };

      default:
        return {
          backgroundColor: "#e9ecef",
          color: "#495057",
          border: "1px solid #dee2e6",
        };
    }
  };

  useEffect(() => {
    Promise.all([
      api.get(`/panels/${panelId}`),
      api.get(`/panels/${panelId}/genes`),
      api.get(`/panels/${panelId}/strs`),
    ])
      .then(([panelResponse, genesResponse, strsResponse]) => {
        console.log("Panel:", panelResponse.data);
        console.log("Genes:", genesResponse.data);
        console.log("STRs:", strsResponse.data);

        setPanel(panelResponse.data);
        setGenes(genesResponse.data);
        setStrs(strsResponse.data);
      })
      .catch((error) => {
        console.error("Error loading panel details:", error);
      });
  }, [panelId]);

  if (!panel) {
    return (
      <div className="container mt-4">
        <p>Loading panel...</p>
      </div>
    );
  }

  const showOriginPanel =
    ["PanelApp UK", "PanelApp AUS"].includes(panel.source) &&
    (
      hasChildPanelEntries(panel, genes, strs) ||
      [...genes, ...strs].some(
        (entry) =>
          entry.origin_panel_name &&
          entry.origin_panel_name !== panel.panel_name
      )
      // genes.some(
      //   (gene) =>
      //     gene.origin_panel_name &&
      //     gene.origin_panel_name !== panel.panel_name
      // )
    );






  const showMoi =
    panel.source === "ClinGen" ||
    panel.source === "GenCC" ||
    genes.some((gene) => gene.moi);





  return (
    <div className="container mt-4">

      {/* <h1 className="mb-4">{panel.panel_name}</h1> */}

      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <h1 className="mb-0"  >{panel.panel_name}</h1>

        {panel.source === "Laboratory" && (
          <Link
            to={`/lab-panels/${panel.panel_id}/history`}
            className="btn btn-outline-dark"
          >
            View versions
          </Link>
        )}
      </div>


      

      {/* PANEL METADATA */}
      <div className="card mb-4"
        style={{ border: "1px solid #256fa1" }}>
        <div className="card-header"
          style={{ backgroundColor: "#C7DDF0", border: "1px solid #256fa1" }}>
          <h4 className="mb-0" style={{ color: "#256FA1" }} >Panel Information</h4>
        </div>

        <div className="card-body">
          <p>
            <strong>Panel ID:</strong> {panel.panel_id}
          </p>

          <p>
            <strong>Source:</strong> {panel.source || "N/A"}
            {panel.source === "Laboratory" && (
              panel.copied_from_group ? (
                <div className="mb-3">
                  <Link
                    to={`/grouped-disease/${encodeURIComponent(
                      panel.copied_from_group.source
                    )}/${encodeURIComponent(panel.copied_from_group.panel_name)}`}
                    className="text-decoration-none"
                    style={{ color: "#00a6c3" }}
                  >
                    Copied Laboratory Panel - See Original
                  </Link>
                </div>
              ) : (
                panel.copied_from?.map((original) => (
                  <div key={original.panel_id} className="mb-3">
                    {original.is_active ? (
                      <Link
                        to={`/panels/${original.panel_id}`}
                        className="text-decoration-none"
                        style={{ color: "#00aac8" }}
                      >
                        Copied Laboratory Panel - See Original
                      </Link>
                    ) : (
                      <span className="text-muted">
                        Copied from — removed from source
                      </span>
                    )}
                  </div>
                ))
              )
            )}
          </p>





          <p>
            <strong>Disease Group:</strong>{" "}
            {panel.disease_group || "N/A"}
          </p>

          <p>
            <strong>Disease Subgroup:</strong>{" "}
            {panel.disease_subgroup || "N/A"}
          </p>

          <p>
            <strong>Relevant Diseases:</strong>{" "}
            {panel.relevant_diseases || "N/A"}
          </p>

          <p>
            <strong>Version:</strong> {panel.version || "N/A"}
          </p>

          <p>
            <strong>Last Updated:</strong>{" "}
            {panel.last_updated || "N/A"}
          </p>
        </div>
      </div>

      {/* GENES */}
      <div className="card mb-4"
        style={{ border: "1px solid #255fa1" }}>
        <div className="card-header"
          style={{ backgroundColor: "#B9D4EC", border: "1px solid #256fa1" }}>
          <h4 className="mb-0" style={{ color: "#256FA1" }}>
            Genes ({genes.length})
          </h4>
        </div>

        <div className="card-body">
          {genes.length === 0 ? (
            <p>No genes found.</p>
          ) : (
            <div className="table-responsive">
              <table className="table table-striped">

                <thead>
                  <tr>
                    <th>Gene</th>
                    {showOriginPanel && <th>Origin panel</th>}
                    <th>Confidence</th>
                    <th>Phenotypes</th>

                    {panel.source === "GenCC" && <th>Submitter</th>}

                    {/* {(panel.source === "GenCC" || panel.source === "ClinGen") && (
                      <th>MOI</th> 
                    )} */}

                    {showMoi && <th>MOI</th>}


                  </tr>
                </thead>

                <tbody>
                  {genes.map((gene, index) => (
                    <tr key={gene.gene_id || index}>
                      <td>
                        <span
                          className="badge"
                          style={getConfidenceStyle(gene.confidence_level)}
                        >
                          {gene.gene_symbol}
                        </span>
                      </td>

                      {showOriginPanel && (
                        <td>{gene.origin_panel_name ?? "N/A"}</td>
                      )}

                      <td>
                        {gene.confidence_level || "N/A"}
                      </td>

                      <td>
                        {Array.isArray(gene.phenotypes)
                          ? gene.phenotypes.join(", ")
                          : gene.phenotypes || "N/A"}
                      </td>

                      {panel.source === "GenCC" && (
                        <td>{gene.submitter || "N/A"}</td>
                      )}

                      {/* {(panel.source === "GenCC" || panel.source === "ClinGen") && (
                        <td>{gene.moi || "N/A"}</td>
                      )} */}
                      {showMoi && <td>{gene.moi || "N/A"}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>




      {/* STRs */}
      <div className="card mb-4" style={{ border: "1px solid #255fa1" }}>
        <div className="card-header" style={{ backgroundColor: "#B9D4EC", border: "1px solid #256fa1" }}>
          <h4 className="mb-0" style={{ color: "#256FA1" }}>
            STRs ({strs.length})
          </h4>
        </div>

        <div className="card-body">
          {strs.length === 0 ? (
            <p>No STRs found.</p>
          ) : (
            <div className="table-responsive">
              <table className="table table-striped">
                <thead>
                  <tr>
                    <th>Entity</th>

                    {showOriginPanel && <th>Origin panel</th>}

                    <th>Gene</th>
                    <th>Confidence</th>
                    <th>Phenotypes</th>
                    <th>Repeated Sequence</th>
                  </tr>
                </thead>

                <tbody>
                  {strs.map((str) => (
                    <tr key={str.str_id}>
                      <td>{str.entity_name || "N/A"}</td>


                      {showOriginPanel && (
                        <td>{str.origin_panel_name ?? "N/A"}</td>
                      )}

                      <td>{str.gene_symbol || "N/A"}</td>

                      <td>{str.confidence_level || "N/A"}</td>

                      <td>
                        {Array.isArray(str.phenotypes)
                          ? str.phenotypes.join(", ")
                          : str.phenotypes || "N/A"}
                      </td>

                      <td>{str.repeated_sequence || "N/A"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}

export default PanelDetailsPage;
