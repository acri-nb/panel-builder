import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../services/api";

function GroupedDiseasePage() {
  const { source, name } = useParams();

  const [groupedDisease, setGroupedDisease] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
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
    setLoading(true);
    setError("");

    api
      .get("/grouped-disease", {
        params: {
          source: source,
          name: name,
        },
      })
      .then((response) => {
        setGroupedDisease(response.data);
      })
      .catch((error) => {
        console.error("Grouped disease error:", error);
        setError("Could not load grouped disease.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [source, name]);

  if (loading) {
    return (
      <div className="container mt-5 text-center">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>

        <p className="mt-2">
          Loading disease...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mt-5">
        <div className="alert alert-danger">
          {error}
        </div>
      </div>
    );
  }

  if (!groupedDisease) {
    return null;
  }
  return (
    <div className="container mt-5">
      <div className="mb-4">
        <h2>{groupedDisease.panel_name}</h2>
        <p className="mb-1">
          <strong>Source:</strong> {groupedDisease.source}
        </p>
        <p className="text-muted">
          {groupedDisease.record_count} records
        </p>
      </div>

      <div className="table-responsive">
        <table className="table table-bordered align-middle">
          <thead className="table-light">
            <tr>
              <th>Panel metadata</th>
              <th>Gene</th>
              <th>Confidence</th>
              <th>MOI</th>
              {groupedDisease.source === "GenCC" && <th>Submitter</th>}
            </tr>
          </thead>

          <tbody>
            {groupedDisease.records.map((record) => {
              const genes = record.genes?.length ? record.genes : [null];

              return genes.map((gene, index) => (
                <tr key={`${record.panel_id}-${index}`}>
                  {index === 0 && (
                    <td rowSpan={genes.length}>
                      <details>
                        <summary style={{ cursor: "pointer" }}>
                          <strong>{record.panel_name}</strong>
                          <span className="text-muted">
                            {" "}· Panel ID: {record.panel_id}
                          </span>
                        </summary>

                        <div className="mt-3">
                          {/* <p>
                          <strong>Relevant diseases:</strong>{" "}
                          {Array.isArray(record.relevant_diseases)
                            ? record.relevant_diseases.join(", ") || "N/A"
                            : record.relevant_diseases || "N/A"}
                        </p> */}
                          <p>
                            <strong>Version:</strong>{" "}
                            {record.version ?? "N/A"}
                          </p>
                          <p className="mb-0">
                            <strong>Last updated:</strong>{" "}
                            {record.last_updated || "N/A"}
                          </p>
                        </div>
                      </details>
                    </td>
                  )}

                  {/* <td>{gene?.gene_symbol || "No genes"}</td> */}
                  <td>
                    {gene ? (
                      <span
                        className="badge"
                        style={getConfidenceStyle(gene.confidence_level)}
                      >
                        {gene.gene_symbol || "N/A"}
                      </span>
                    ) : (
                      <span className="text-muted">No genes</span>
                    )}
                  </td>
                  <td>{gene?.confidence_level || "N/A"}</td>
                  <td>{gene?.moi || "N/A"}</td>
                  {groupedDisease.source === "GenCC" && (
                    <td>{gene?.submitter || "N/A"}</td>
                  )}
                </tr>
              ));
            })}
          </tbody>
        </table>
      </div>
    </div>
  );

}

export default GroupedDiseasePage;





// return (
//   <div className="container mt-5">

//     <div className="mb-4">
//       <h2>{groupedDisease.panel_name}</h2>

//       <p className="mb-1">
//         <strong>Source:</strong>{" "}
//         {groupedDisease.source}
//       </p>

//       <p className="text-muted">
//         {groupedDisease.record_count} record
//         {groupedDisease.record_count !== 1 ? "s" : ""}
//       </p>
//     </div>

//     {groupedDisease.records.map((record) => (
//       <div
//         key={record.panel_id}
//         className="card mb-4"
//       >
//         <div className="card-header">
//           <strong>
//             Panel ID: {record.panel_id}
//           </strong>
//         </div>

//         <div className="card-body">

//           <p>
//             <strong>Disease Group:</strong>{" "}
//             {record.disease_group || "N/A"}
//           </p>

//           <p>
//             <strong>Disease Subgroup:</strong>{" "}
//             {record.disease_subgroup || "N/A"}
//           </p>

//           <p>
//             <strong>Relevant Diseases:</strong>{" "}
//             {record.relevant_diseases || "N/A"}
//           </p>

//           <p>
//             <strong>Version:</strong>{" "}
//             {record.version || "N/A"}
//           </p>

//           <p>
//             <strong>Last Updated:</strong>{" "}
//             {record.last_updated || "N/A"}
//           </p>

//           <h5 className="mt-4">
//             Genes
//           </h5>

//           {record.genes.length === 0 ? (
//             <p className="text-muted">
//               No genes
//             </p>
//           ) : (
//             <div className="table-responsive">
//               <table className="table table-sm table-bordered">

//                 <thead>
//                   <tr>
//                     <th>Gene</th>
//                     <th>Confidence</th>
//                     <th>Phenotypes</th>
//                     <th>MOI</th>

//                     {groupedDisease.source === "GenCC" && (
//                       <th>Submitter</th>
//                     )}
//                   </tr>
//                 </thead>

//                 <tbody>
//                   {record.genes.map((gene, index) => (
//                     <tr key={index}>
//                       <td>
//                         <strong>
//                           {gene.gene_symbol}
//                         </strong>
//                       </td>

//                       <td>
//                         {gene.confidence_level || "N/A"}
//                       </td>

//                       <td>
//                         {Array.isArray(gene.phenotypes)
//                           ? gene.phenotypes.join(", ")
//                           : gene.phenotypes || "N/A"}
//                       </td>

//                       <td>
//                         {gene.moi || "N/A"}
//                       </td>

//                       {groupedDisease.source === "GenCC" && (
//                         <td>
//                           {gene.submitter || "N/A"}
//                         </td>
//                       )}
//                     </tr>
//                   ))}
//                 </tbody>

//               </table>
//             </div>
//           )}

//         </div>
//       </div>
//     ))}

//   </div>
// );