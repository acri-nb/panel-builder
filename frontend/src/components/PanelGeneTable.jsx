import { useState, Fragment } from "react";
import { Link } from "react-router-dom";


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



// function AlphabeticalGenes({ genes, enabled, children }) {
//     if (!enabled) {
//         return genes.map(children);
//     }

//     const groups = {};

//     [...genes]
//         .sort((a, b) =>
//             (a.gene_symbol || "").localeCompare(
//                 b.gene_symbol || "",
//                 undefined,
//                 { sensitivity: "base", numeric: true }
//             )
//         )
//         .forEach((gene) => {
//             const firstLetter = (gene.gene_symbol || "")
//                 .trim()
//                 .charAt(0)
//                 .toUpperCase();

//             const letter = /^[A-Z]$/.test(firstLetter)
//                 ? firstLetter
//                 : "#";

//             (groups[letter] ??= []).push(gene);
//         });

//     return Object.entries(groups)
//         .sort(([a], [b]) => a.localeCompare(b))
//         .map(([letter, entries]) => (
//             <details key={letter} className="border rounded p-2 mb-2">
//                 <summary
//                     className="fw-semibold"
//                     style={{ cursor: "pointer", color: "#256fa1" }}
//                 >
//                     {letter} ({entries.length})
//                 </summary>

//                 <div className="mt-3">
//                     {entries.map(children)}
//                 </div>
//             </details>
//         ));
// }


function AlphabeticalGenes({
    genes,
    enabled,
    confidenceStyle,
    children,
}) {
    const [expandedLetter, setExpandedLetter] = useState(null);

    if (!enabled) {
        return genes.map(children);
    }

    const groups = {};

    [...genes]
        .sort((a, b) =>
            (a.gene_symbol || "").localeCompare(
                b.gene_symbol || "",
                undefined,
                { sensitivity: "base", numeric: true }
            )
        )
        .forEach((gene) => {
            const firstLetter = (gene.gene_symbol || "")
                .trim()
                .charAt(0)
                .toUpperCase();

            const letter = /^[A-Z]$/.test(firstLetter)
                ? firstLetter
                : "#";

            (groups[letter] ??= []).push(gene);
        });

    return (
        <>
            <div className="d-flex flex-wrap gap-2">
                {Object.keys(groups)
                    .sort()
                    .map((letter) => (
                        <button
                            key={letter}
                            type="button"
                            className="badge"
                            style={{
                                ...confidenceStyle,
                                cursor: "pointer",
                                padding: "7px 10px",
                                outline:
                                    expandedLetter === letter
                                        ? "2px solid currentColor"
                                        : "none",
                            }}
                            aria-expanded={expandedLetter === letter}
                            onClick={() =>
                                setExpandedLetter((current) =>
                                    current === letter ? null : letter
                                )
                            }
                        >
                            {letter} ({groups[letter].length})
                        </button>
                    ))}
            </div>

            {expandedLetter && groups[expandedLetter] && (
                <div className="mt-3">
                    {groups[expandedLetter].map(children)}
                </div>
            )}
        </>
    );
}











function PanelGeneTable({ results = [], page = 1, onPageChange = () => { }, pageSize = 20 }) {
    const [expandedGroup, setExpandedGroup] = useState(null);
    // const [expandedGroups, setExpandedGroups] = useState({});
    const [expandedStrs, setExpandedStrs] = useState(null);
    // const [expandedMetadata, setExpandedMetadata] = useState(null);


    const groupGenesByConfidence = (genes) => {
        return genes.reduce((groups, gene) => {
            const confidence = gene.confidence_level || "Unknown";

            if (!groups[confidence]) {
                groups[confidence] = [];
            }

            groups[confidence].push(gene);

            return groups;
        }, {});
    };

    const handleGroupClick = (panelId, confidence) => {
        const groupKey = `${panelId}-${confidence}`;

        if (expandedGroup === groupKey) {
            setExpandedGroup(null);
        } else {
            setExpandedGroup(groupKey);
        }
    };


    // const handleGroupClick = (panelId, confidence) => {
    //     const groupKey = `${panelId}-${confidence}`;

    //     setExpandedGroups((current) => ({
    //         ...current,
    //         [groupKey]: !current[groupKey],
    //     }));
    // };



    const handleStrClick = (panelId) => {
        if (expandedStrs === panelId) {
            setExpandedStrs(null);
        } else {
            setExpandedStrs(panelId);
        }
    };

    // const handleMetadataClick = (panelId) => {
    //     setExpandedMetadata((currentPanelId) =>
    //         currentPanelId === panelId ? null : panelId
    //     );
    // };

    // const formatMetadataValue = (value) => {
    //     if (Array.isArray(value)) {
    //         return value.length > 0 ? value.join(", ") : "N/A";
    //     }

    //     return value || "N/A";
    // };

    const getConfidenceOrder = (confidence) => {
        const label = String(getConfidenceLabel(confidence)).toLowerCase();
        const order = { red: 0, green: 1, yellow: 2 };
        return order[label] ?? 3;
    };



    const getConfidenceLabel = (confidence) => {
        switch (String(confidence ?? "").trim().toLowerCase()) {
            case "3":
            case "green":
                return "Green";

            case "2":
            case "amber":
            case "orange":
            case "yellow":
                return "Amber";

            case "1":
            case "red":
                return "Red";

            case "0":
            case "no list":
            case "no known disease relationship":
                return "Unknown";

            default:
                return confidence;
        }
    };

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

            case "0":
            case "no list":
                return {
                    backgroundColor: "#e9ecef",
                    color: "#495057",
                    border: "1px solid #dee2e6",
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
            case "disputed evidence":
                return {
                    backgroundColor: "#f4c8cc",
                    color: "#7a2931",
                    border: "1px solid #eab3b9",
                };

            case "refuted":
            case "refuted evidence":
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


    const groupDiseasePanels = (results) => {
        const grouped = {};

        results.forEach((item) => {
            const records =
                item.isGrouped && Array.isArray(item.records)
                    ? item.records
                    : [item];

            records.forEach((record) => {
                const panel = {
                    ...record,
                    source: record.source || item.source,
                    panel_name: record.panel_name || item.panel_name,
                };

                const shouldGroup =
                    panel.source === "GenCC" ||
                    panel.source === "ClinGen";

                const rowKey = shouldGroup
                    ? `${panel.source}-${panel.panel_name?.trim().toLowerCase()}`
                    : `panel-${panel.panel_id}`;

                if (!grouped[rowKey]) {
                    grouped[rowKey] = {
                        ...panel,
                        rowKey,
                        records: [],
                        genes: [],
                        strs: [],
                    };
                }

                grouped[rowKey].records.push(panel);
                grouped[rowKey].genes.push(...(panel.genes || []));
                grouped[rowKey].strs.push(...(panel.strs || []));
            });
        });

        return Object.values(grouped).map((panel) => ({
            ...panel,
            record_count: panel.records.length,
            isGrouped:
                (panel.source === "GenCC" ||
                    panel.source === "ClinGen") &&
                panel.records.length > 1,
        }));
    };



    const displayedResults = groupDiseasePanels(results);

    const totalPages = Math.ceil(displayedResults.length / pageSize);
    const currentPage = Math.min(Math.max(page, 1), totalPages || 1);
    const paginatedResults = displayedResults.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize
    );

    if (results.length === 0) {
        return null;
    }






    return (
        <div>
            <div className="table-responsive">
                <table className="table table-bordered align-middle">

                    <thead>
                        <tr>
                            <th>Source</th>
                            <th>Panel</th>
                            <th>Gene Groups</th>
                            <th>STRs</th>
                        </tr>
                    </thead>

                    <tbody>
                        {paginatedResults.map((panel) => {
                            const groupedGenes =
                                groupGenesByConfidence(panel.genes || []);


                            const panelLink = panel.isGrouped
                                ? `/grouped-disease/${encodeURIComponent(
                                    panel.source
                                )}/${encodeURIComponent(panel.panel_name)}`
                                : `/panels/${panel.panel_id}`;

                            const showOriginPanel = hasChildPanelEntries(
                                panel,
                                panel.genes || [],
                                panel.strs || []
                            );



                            return (
                                // <Fragment key={panel.panel_id}>
                                <Fragment key={panel.rowKey}>

                                    <tr>
                                        <td>
                                            {panel.source || "N/A"}
                                        </td>

                                        <td>
                                            {/* <Link to={`/panels/${panel.panel_id}`} */}
                                            <Link to={panelLink}
                                                className="text-decoration-none">
                                                <strong style={{ color: "#256fa1" }}>
                                                    {panel.panel_name}
                                                </strong>
                                            </Link>

                                            {panel.isGrouped && (
                                                <div className="small text-muted mt-1">
                                                    Records: {panel.record_count}
                                                </div>
                                            )}
                                            <div>


                                            </div>
                                            {panel.source === "Ontario Health" && (
                                                <div className="small text-muted mt-1">
                                                    <strong>Lab:</strong> {panel.lab_name || "N/A"}
                                                </div>
                                            )}
                                        </td>

                                        <td>
                                            {Object.keys(groupedGenes).length === 0 ? (
                                                <span className="text-muted">
                                                    No genes
                                                </span>
                                            ) : (
                                                Object.entries(groupedGenes)
                                                    .sort(([confidenceA], [confidenceB]) =>
                                                        getConfidenceOrder(confidenceA) -
                                                        getConfidenceOrder(confidenceB)
                                                    )
                                                    .map(
                                                        ([confidence, genes]) => {
                                                            return (
                                                                <button
                                                                    key={confidence}
                                                                    className="btn btn-sm me-2 mb-1"
                                                                    style={getConfidenceStyle(confidence)}
                                                                    onClick={() =>
                                                                        handleGroupClick(
                                                                            // panel.panel_id,
                                                                            panel.rowKey,
                                                                            confidence
                                                                        )
                                                                    }
                                                                >
                                                                    {getConfidenceLabel(confidence)} ({genes.length})
                                                                </button>
                                                            );
                                                        }
                                                    )
                                            )}
                                        </td>

                                        <td>
                                            {panel.strs && panel.strs.length > 0 ? (

                                                <button
                                                    className="btn btn-sm btn-outline-secondary"
                                                    onClick={() => handleStrClick(panel.rowKey)}
                                                >
                                                    STRs ({panel.strs.length})
                                                </button>
                                            ) : (
                                                <span className="text-muted">
                                                    No STRs
                                                </span>
                                            )}
                                        </td>

                                    </tr>

                                    {/* {expandedMetadata === panel.panel_id && (
                                    <tr>
                                        <td colSpan="4">
                                            <div className="row g-2">
                                                <div className="col-md-4">
                                                    <strong>Source:</strong> {formatMetadataValue(panel.source)}
                                                </div>
                                                <div className="col-md-4">
                                                    <strong>Panel ID:</strong> {formatMetadataValue(panel.panel_id)}
                                                </div>
                                                <div className="col-md-4">
                                                    <strong>Disease Group:</strong> {formatMetadataValue(panel.disease_group)}
                                                </div>
                                                <div className="col-md-4">
                                                    <strong>Disease Subgroup:</strong> {formatMetadataValue(panel.disease_subgroup)}
                                                </div>
                                                <div className="col-md-8">
                                                    <strong>Relevant Diseases:</strong> {formatMetadataValue(panel.relevant_diseases)}
                                                </div>
                                                {panel.lab_name && (
                                                    <div className="col-md-4">
                                                        <strong>Lab:</strong> {panel.lab_name}
                                                    </div>
                                                )}
                                                {panel.version && (
                                                    <div className="col-md-4">
                                                        <strong>Version:</strong> {panel.version}
                                                    </div>
                                                )}
                                                {panel.last_updated && (
                                                    <div className="col-md-4">
                                                        <strong>Last Updated:</strong> {formatMetadataValue(panel.last_updated)}
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                )} */}

                                    {Object.entries(groupedGenes).map(
                                        ([confidence, genes]) => {
                                            const groupKey =
                                                `${panel.rowKey}-${confidence}`;

                                            if (expandedGroup !== groupKey) {
                                                return null;
                                            }

                                            // if (!expandedGroups[groupKey]) {
                                            //     return null;
                                            // }


                                            return (
                                                <tr key={`${groupKey}-expanded`}>
                                                    <td colSpan="4">

                                                        <strong>
                                                            {getConfidenceLabel(confidence)} genes
                                                        </strong>

                                                        <div className="mt-2">
                                                            {/* {genes.map((gene, index) => ( */}
                                                            <AlphabeticalGenes
                                                                genes={genes}
                                                                enabled={(panel.genes?.length || 0) > 100}
                                                                confidenceStyle={getConfidenceStyle(confidence)}
                                                            >
                                                                {(gene, index) => (

                                                                    <div
                                                                        key={index}
                                                                        className="d-inline-block me-3 mb-3"
                                                                    >
                                                                        {/* <div
                                                                        className="badge"
                                                                        style={getConfidenceStyle(confidence)}
                                                                    >
                                                                        {gene.gene_symbol}
                                                                    </div> */}

                                                                        {showOriginPanel ? (
                                                                            <details
                                                                                className="badge"
                                                                                style={{
                                                                                    ...getConfidenceStyle(confidence),
                                                                                    whiteSpace: "normal",
                                                                                    textAlign: "left",
                                                                                }}
                                                                            >
                                                                                <summary
                                                                                    style={{
                                                                                        cursor: "pointer",
                                                                                        display: "list-item",
                                                                                        listStylePosition: "inside",
                                                                                    }}
                                                                                >
                                                                                    {gene.gene_symbol}
                                                                                </summary>

                                                                                <div className="mt-1" style={{ fontWeight: 400 }}>
                                                                                    {gene.origin_panel_name ?? "N/A"}
                                                                                </div>
                                                                            </details>
                                                                        ) : (
                                                                            <div className="badge" style={getConfidenceStyle(confidence)}>
                                                                                {gene.gene_symbol}
                                                                            </div>
                                                                        )}

                                                                        {/* {showOriginPanel && (
                                                                        <details className="small mt-1">
                                                                            <summary style={{ cursor: "pointer", color: "#1b2024" }}>
                                                                                Origin panel
                                                                            </summary>
                                                                            <div className="text-muted mt-1">
                                                                                {gene.origin_panel_name ?? "N/A"}
                                                                            </div>
                                                                        </details>
                                                                    )} */}



                                                                        {panel.source === "GenCC" && (
                                                                            <div className="small text-muted mt-1">
                                                                                <div>
                                                                                    MOI: {gene.moi || "N/A"}
                                                                                </div>

                                                                                <div>
                                                                                    Submitter: {gene.submitter || "N/A"}
                                                                                </div>
                                                                            </div>
                                                                        )}

                                                                        {panel.source === "ClinGen" && (
                                                                            <div className="small text-muted mt-1">
                                                                                MOI: {gene.moi || "N/A"}
                                                                            </div>
                                                                        )}
                                                                    </div>

                                                                )}
                                                            </AlphabeticalGenes>
                                                        </div>

                                                    </td>
                                                </tr>
                                            );
                                        }
                                    )}



                                    {expandedStrs === panel.rowKey &&
                                        panel.strs &&
                                        panel.strs.length > 0 && (
                                            <tr>
                                                <td colSpan="4">
                                                    <strong>STRs</strong>

                                                    <div className="mt-2">
                                                        {panel.strs.map((str, index) => (
                                                            <div
                                                                key={str.str_id ?? index}
                                                                className="d-inline-block me-3 mb-3"
                                                            >
                                                                {/* <div
                                                                    className="badge"
                                                                    style={getConfidenceStyle(str.confidence_level)}
                                                                >
                                                                    {str.entity_name || "N/A"}
                                                                </div> */}


                                                                {showOriginPanel ? (
                                                                    <details
                                                                        className="badge"
                                                                        style={{
                                                                            ...getConfidenceStyle(str.confidence_level),
                                                                            whiteSpace: "normal",
                                                                            textAlign: "left",
                                                                        }}
                                                                    >
                                                                        <summary
                                                                            style={{
                                                                                cursor: "pointer",
                                                                                display: "list-item",
                                                                                listStylePosition: "inside",
                                                                            }}
                                                                        >
                                                                            {str.entity_name}
                                                                        </summary>

                                                                        <div className="mt-1" style={{ fontWeight: 400 }}>
                                                                            {str.origin_panel_name ?? "N/A"}
                                                                        </div>
                                                                    </details>
                                                                ) : (
                                                                    <div className="badge" style={getConfidenceStyle(str.confidence_level)}>
                                                                        {str.entity_name}
                                                                    </div>
                                                                )}




                                                                {/* {showOriginPanel && (
                                                                    <details className="small mt-1">
                                                                        <summary
                                                                            style={{
                                                                                cursor: "pointer",
                                                                                color: "#1b2024",
                                                                            }}
                                                                        >
                                                                            Origin panel
                                                                        </summary>
                                                                        <div className="text-muted mt-1">
                                                                            {str.origin_panel_name ?? "N/A"}
                                                                        </div>
                                                                    </details>
                                                                )} */}
                                                            </div>
                                                        ))}
                                                    </div>
                                                </td>
                                            </tr>
                                        )}

                                    {/* {expandedStrs === panel.rowKey &&
                                        panel.strs &&
                                        panel.strs.length > 0 && (
                                            <tr>
                                                <td colSpan="4">

                                                    <strong>STRs</strong>

                                                    <div className="table-responsive mt-2">
                                                        <table className="table table-sm table-bordered mb-0">
                                                            <thead>
                                                                <tr>
                                                                    <th>Entity</th>
                                                                    <th>Gene</th>
                                                                    <th>Confidence</th>
                                                                    <th>Phenotypes</th>
                                                                    <th>Repeated Sequence</th>
                                                                </tr>
                                                            </thead>

                                                            <tbody>
                                                                {panel.strs.map((str, index) => (
                                                                    <tr key={str.str_id || index}>
                                                                        <td>
                                                                            {str.entity_name || "N/A"}
                                                                        </td>

                                                                        <td>
                                                                            {str.gene_symbol || "N/A"}
                                                                        </td>

                                                                        <td>
                                                                            {str.confidence_level || "N/A"}
                                                                        </td>

                                                                        <td>
                                                                            {Array.isArray(str.phenotypes)
                                                                                ? str.phenotypes.join(", ")
                                                                                : str.phenotypes || "N/A"}
                                                                        </td>

                                                                        <td>
                                                                            {str.repeated_sequence || "N/A"}
                                                                        </td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>

                                                </td>
                                            </tr>
                                        )} */}







                                </Fragment>
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
                        disabled={currentPage === 1}
                        onClick={() => onPageChange(currentPage - 1)}
                    >
                        Previous
                    </button>

                    <span>
                        Page {currentPage} of {totalPages}
                    </span>

                    <button
                        type="button"
                        className="btn btn-outline-secondary"
                        disabled={currentPage === totalPages}
                        onClick={() => onPageChange(currentPage + 1)}
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    );
}

export default PanelGeneTable;



