import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api";


function groupCopySearchResults(results) {
  const groups = new Map();

  results.forEach((panel) => {
    const shouldGroup =
      panel.source === "GenCC" || panel.source === "ClinGen";

    const key = shouldGroup
      ? `${panel.source}-${panel.panel_name?.trim().toLowerCase()}`
      : `panel-${panel.panel_id}`;

    if (!groups.has(key)) {
      groups.set(key, {
        ...panel,
        resultKey: key,
        records: [],
      });
    }

    groups.get(key).records.push(panel);
  });

  return Array.from(groups.values()).map((group) => ({
    ...group,
    record_count: group.records.length,
    isGrouped:
      ["GenCC", "ClinGen"].includes(group.source) &&
      group.records.length > 1,
  }));
}


function CopyLabPanelPage() {

  const [copySearchType, setCopySearchType] = useState("name");
  const [copySearchTerm, setCopySearchTerm] = useState("");
  const [copyResults, setCopyResults] = useState([]);
  const [copyLoading, setCopyLoading] = useState(false);
  const [copyError, setCopyError] = useState("");
  const [copyHasSearched, setCopyHasSearched] = useState(false);
  const [selectedSourcePanel, setSelectedSourcePanel] = useState(null);
  const [copyDraft, setCopyDraft] = useState(null);
  const [copyDetailsLoading, setCopyDetailsLoading] = useState(false);
  const latestCopySelection = useRef(0);
  const latestCopySearch = useRef(0);
  const navigate = useNavigate();
  const [copySaving, setCopySaving] = useState(false);
  const copySaveInProgress = useRef(false);


  async function handleCopySearch(event) {
    event.preventDefault();

    const term = copySearchTerm.trim();

    if (!term) {
      setCopyError("Enter a panel name, gene, or disease/HP term.");
      return;
    }

    const searchId = ++latestCopySearch.current;

    setCopyLoading(true);
    setCopyError("");
    setCopyResults([]);
    setCopyHasSearched(true);
    setSelectedSourcePanel(null);

    latestCopySelection.current += 1;
    setCopyDraft(null);
    setCopyDetailsLoading(false);

    try {
      const response = await api.get("/panels/search", {
        params: {
          [copySearchType]: term,
        },
      });

      if (searchId !== latestCopySearch.current) return;

      const rows = Array.isArray(response.data)
        ? response.data
        : response.data?.data;

      if (!Array.isArray(rows)) {
        throw new Error("Unexpected search response");
      }

      const externalSources = new Set([
        "PanelApp UK",
        "PanelApp AUS",
        "Blueprint Genetics",
        "Ontario Health",
        "ClinGen",
        // "GenCC",
      ]);

      setCopyResults(
        rows.filter((panel) => externalSources.has(panel.source))
      );
    } catch {
      if (searchId === latestCopySearch.current) {
        setCopyError("Unable to search external panels.");
      }
    } finally {
      if (searchId === latestCopySearch.current) {
        setCopyLoading(false);
      }
    }
  }






  async function handleSelectSourcePanel(sourcePanel) {
    const selectionId = ++latestCopySelection.current;

    setSelectedSourcePanel(sourcePanel);
    setCopyDraft(null);
    setCopyError("");
    setCopyDetailsLoading(true);

    try {
      const records = sourcePanel.isGrouped
        ? sourcePanel.records
        : [sourcePanel];

      const loadedRecords = await Promise.all(
        records.map(async (record) => {
          const [metadataResponse, genesResponse, strsResponse] =
            await Promise.all([
              api.get(`/panels/${record.panel_id}`),
              api.get(`/panels/${record.panel_id}/genes`),
              api.get(`/panels/${record.panel_id}/strs`),
            ]);

          return {
            metadata: metadataResponse.data,
            genes: genesResponse.data,
            strs: strsResponse.data,
          };
        })
      );

      if (selectionId !== latestCopySelection.current) return;

      const metadata = loadedRecords[0].metadata;

      setCopyDraft({
        panel_name: sourcePanel.panel_name ?? "",
        disease_group: metadata.disease_group ?? "",
        disease_subgroup: metadata.disease_subgroup ?? "",
        relevant_diseases: Array.isArray(metadata.relevant_diseases)
          ? metadata.relevant_diseases.join(", ")
          : metadata.relevant_diseases ?? "",

        source_record_panel_ids: loadedRecords.map(
          (record) => record.metadata.panel_id
        ),

        genes: loadedRecords.flatMap((record) =>
          record.genes.map((gene, index) => ({
            ...gene,
            draftKey: `gene-${record.metadata.panel_id}-${index}`,
            source_record_panel_id: record.metadata.panel_id,
            selected: true,
            gene_symbol: gene.gene_symbol ?? "",
            confidence_level: String(gene.confidence_level ?? ""),
            phenotypes: (gene.phenotypes ?? []).join("\n"),
          }))
        ),

        strs: loadedRecords.flatMap((record) =>
          record.strs.map((str, index) => ({
            ...str,
            draftKey: `str-${record.metadata.panel_id}-${index}`,
            source_record_panel_id: record.metadata.panel_id,
            selected: true,
            entity_name: str.entity_name ?? "",
            gene_symbol: str.gene_symbol ?? "",
            confidence_level: String(str.confidence_level ?? ""),
            phenotypes: (str.phenotypes ?? []).join("\n"),
            repeated_sequence: str.repeated_sequence ?? "",
          }))
        ),
      });
    } catch {
      if (selectionId === latestCopySelection.current) {
        setCopyError("Unable to load all selected panel records.");
      }
    } finally {
      if (selectionId === latestCopySelection.current) {
        setCopyDetailsLoading(false);
      }
    }
  }

  // async function handleSelectSourcePanel(sourcePanel) {
  //   const selectionId = ++latestCopySelection.current;

  //   setSelectedSourcePanel(sourcePanel);
  //   setCopyDraft(null);
  //   setCopyError("");
  //   setCopyDetailsLoading(true);

  //   try {
  //     const [metadataResponse, genesResponse, strsResponse] =
  //       await Promise.all([
  //         api.get(`/panels/${sourcePanel.panel_id}`),
  //         api.get(`/panels/${sourcePanel.panel_id}/genes`),
  //         api.get(`/panels/${sourcePanel.panel_id}/strs`),
  //       ]);

  //     if (selectionId !== latestCopySelection.current) return;

  //     const metadata = metadataResponse.data;

  //     setCopyDraft({
  //       panel_name: metadata.panel_name ?? "",
  //       disease_group: metadata.disease_group ?? "",
  //       disease_subgroup: metadata.disease_subgroup ?? "",
  //       relevant_diseases: Array.isArray(metadata.relevant_diseases)
  //         ? metadata.relevant_diseases.join(", ")
  //         : metadata.relevant_diseases ?? "",

  //       genes: genesResponse.data.map((gene, index) => ({
  //         ...gene,
  //         draftKey: `gene-${index}`,
  //         selected: true,
  //         gene_symbol: gene.gene_symbol ?? "",
  //         confidence_level: String(gene.confidence_level ?? ""),
  //         phenotypes: (gene.phenotypes ?? []).join("\n"),
  //       })),

  //       strs: strsResponse.data.map((str, index) => ({
  //         ...str,
  //         draftKey: `str-${index}`,
  //         selected: true,
  //         entity_name: str.entity_name ?? "",
  //         gene_symbol: str.gene_symbol ?? "",
  //         confidence_level: String(str.confidence_level ?? ""),
  //         phenotypes: (str.phenotypes ?? []).join("\n"),
  //         repeated_sequence: str.repeated_sequence ?? "",
  //       })),
  //     });
  //   } catch {
  //     if (selectionId === latestCopySelection.current) {
  //       setCopyError("Unable to load the selected panel.");
  //     }
  //   } finally {
  //     if (selectionId === latestCopySelection.current) {
  //       setCopyDetailsLoading(false);
  //     }
  //   }
  // }



  function updateCopyMetadata(field, value) {
    setCopyDraft((current) => ({
      ...current,
      [field]: value,
    }));
  }




  function updateCopyEntry(collection, draftKey, field, value) {
    setCopyDraft((current) => ({
      ...current,
      [collection]: current[collection].map((entry) =>
        entry.draftKey === draftKey
          ? { ...entry, [field]: value }
          : entry
      ),
    }));
  }




  function selectAllCopyEntries(collection, selected) {
    setCopyDraft((current) => ({
      ...current,
      [collection]: current[collection].map((entry) => ({
        ...entry,
        selected,
      })),
    }));
  }




  function getConfidenceColor(confidence) {
    switch (String(confidence ?? "").trim().toLowerCase()) {
      case "3":
      case "green":
      case "definitive":
      case "strong":
      case "moderate":
        return "green";

      case "2":
      case "amber":
      case "orange":
      case "yellow":
        return "amber";

      case "1":
      case "red":
      case "limited":
      case "disputed":
      case "refuted":
        return "red";

      case "0":
      case "no list":
      case "no known disease relationship":
        return "grey";

      default:
        return null;
    }
  }

  function selectCopyEntriesByColor(collection, color) {
    setCopyDraft((current) => {
      if (!current) return current;

      return {
        ...current,
        [collection]: current[collection].map((entry) => ({
          ...entry,
          selected:
            entry.selected ||
            getConfidenceColor(entry.confidence_level) === color,
        })),
      };
    });
  }













  const groupedCopyResults = groupCopySearchResults(copyResults);

  async function handleCreateCopy() {
    if (!copyDraft || copySaveInProgress.current) return;

    const panelName = copyDraft.panel_name.trim();

    const selectedGenes = copyDraft.genes.filter(
      (gene) => gene.selected
    );

    const selectedStrs = copyDraft.strs.filter(
      (str) => str.selected
    );

    if (!panelName) {
      setCopyError("Enter a name for the laboratory panel.");
      return;
    }

    if (selectedGenes.length === 0 && selectedStrs.length === 0) {
      setCopyError("Select at least one gene or STR.");
      return;
    }

    if (
      selectedGenes.some((gene) => gene.panel_gene_id == null) ||
      selectedStrs.some((str) => str.panel_str_id == null)
    ) {
      setCopyError(
        "Some entries are missing their association IDs. " +
        "Select the source panel again after updating the API."
      );
      return;
    }

    const splitPhenotypes = (text) =>
      text
        .split("\n")
        .map((value) => value.trim())
        .filter(Boolean);

    const data = {
      source_record_panel_ids: copyDraft.source_record_panel_ids,

      track_clingen_group:
        selectedSourcePanel.source === "ClinGen",

      panel_name: panelName,
      disease_group: copyDraft.disease_group.trim() || null,
      disease_subgroup: copyDraft.disease_subgroup.trim() || null,
      relevant_diseases: copyDraft.relevant_diseases.trim() || null,

      genes: selectedGenes.map((gene) => ({
        panel_gene_id: gene.panel_gene_id,
        confidence_level: gene.confidence_level.trim() || null,
        phenotypes: splitPhenotypes(gene.phenotypes),
      })),

      strs: selectedStrs.map((str) => ({
        panel_str_id: str.panel_str_id,
        confidence_level: str.confidence_level.trim() || null,
        phenotypes: splitPhenotypes(str.phenotypes),
        repeated_sequence: str.repeated_sequence.trim() || null,
      })),
    };

    copySaveInProgress.current = true;
    setCopySaving(true);
    setCopyError("");

    try {
      const response = await api.post("/lab-panels/copy", data);

      navigate(`/panels/${response.data.panel_id}`);
    } catch (error) {
      const detail = error.response?.data?.detail;

      setCopyError(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail
              .map((item) => `${item.loc.join(".")}: ${item.msg}`)
              .join("; ")
            : "Unable to create the laboratory copy."
      );
    } finally {
      copySaveInProgress.current = false;
      setCopySaving(false);
    }
  }


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
      case "no known disease relationship":
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

















  return (

    <div className="container mt-4 mb-5">
      <h2 style={{ color: "#256fa1" }}>Copy from external panels</h2>

      <fieldset disabled={copySaving}>
        <div className="card p-3 mb-4" >

          <h4 style={{ color: "#2095C7" }}></h4>

          <form onSubmit={handleCopySearch}>
            <div className="row g-2">
              <div className="col-md-3">
                <select
                  className="form-select"
                  aria-label="External panel search type"
                  value={copySearchType}
                  onChange={(event) => setCopySearchType(event.target.value)}
                >
                  <option value="name">Panel name</option>
                  <option value="gene">Gene</option>
                  <option value="disease">Disease / HP</option>
                </select>
              </div>

              <div className="col-md-7">
                <input
                  type="search"
                  className="form-control"
                  placeholder="Search external panels..."
                  aria-label="External panel search term"
                  value={copySearchTerm}
                  onChange={(event) => setCopySearchTerm(event.target.value)}
                  required
                />
              </div>

              <div className="col-md-2">
                <button
                  type="submit"
                  className="btn btn-primary w-100"
                   style={{ backgroundColor: "#256FA1", borderColor: "#256FA1" }}
                  disabled={copyLoading}
                >
                  {copyLoading ? "Searching..." : "Search"}
                </button>
              </div>
            </div>
          </form>

          {copyError && (
            <div className="alert alert-danger mt-3">{copyError}</div>
          )}

          {!copyLoading &&
            !copyError &&
            copyHasSearched &&
            copyResults.length === 0 && (
              <p className="text-muted mt-3 mb-0">
                No external panels found.
              </p>
            )}

          {!copyLoading && copyResults.length > 0 && (
            <div
              className="list-group mt-3"
              style={{ maxHeight: "400px", overflowY: "auto" }}
            >

















              {groupedCopyResults.map((panel) => (
                <div key={panel.resultKey} className="list-group-item">
                  <div className="d-flex justify-content-between align-items-center gap-3">
                    <div>
                      <strong style={{ color: "#256fa1" }}>
                        {panel.panel_name}
                      </strong>

                      <div className="small text-muted">
                        {panel.source}
                        {panel.lab_name && ` · ${panel.lab_name}`}
                      </div>



                    </div>
                    {panel.isGrouped && (
                      <div className="small text-muted">
                        Records: {panel.record_count}
                      </div>
                    )}



                    <button
                      type="button"
                      className="btn btn-outline-primary btn-sm"
                      style={{ backgroundColor: "#ffffff", borderColor: "#256FA1",color: "#256FA1", }}
                      // disabled={panel.isGrouped}
                      onClick={() => handleSelectSourcePanel(panel)}
                    >
                      Select panel
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {selectedSourcePanel && (
            <div className="alert alert-info mt-3 mb-0">
              Selected: <strong>{selectedSourcePanel.panel_name}</strong>
              {" "}({selectedSourcePanel.source})
            </div>
          )}


          {copyDetailsLoading && (
            <p className="mt-3">Loading panel contents...</p>
          )}

          {copyDraft && !copyDetailsLoading && (
            <div className="mt-4">
              <h4>Review laboratory copy</h4>

              <div className="row g-3 mb-4">
                {[
                  ["panel_name", "Panel name"],
                  ["disease_group", "Disease group"],
                  ["disease_subgroup", "Disease subgroup"],
                  ["relevant_diseases", "Relevant diseases"],
                ].map(([field, label]) => (
                  <div className="col-md-6" key={field}>
                    <label className="form-label d-block">
                      {label}
                      <input
                        className="form-control mt-1"
                        value={copyDraft[field]}
                        onChange={(event) =>
                          updateCopyMetadata(field, event.target.value)
                        }
                      />
                    </label>
                  </div>
                ))}
              </div>

              {[
                { collection: "genes", title: "Genes" },
                { collection: "strs", title: "STRs" },
              ].map(({ collection, title }) => {
                const entries = copyDraft[collection];
                const selectedCount = entries.filter(
                  (entry) => entry.selected
                ).length;











                return (

                  <section key={collection} className="mb-4">
                    <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
                      <h5 className="mb-0">
                        {title}: {selectedCount} / {entries.length} selected
                      </h5>

                      <button
                        type="button"
                        className="btn btn-outline-primary btn-sm"
                        onClick={() => selectAllCopyEntries(collection, true)}
                      >
                        Select all
                      </button>

                      <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm"
                        onClick={() => selectAllCopyEntries(collection, false)}
                      >
                        Clear selection
                      </button>

                      {["green", "amber", "red","grey"].map((color) => (
                        <button
                          key={color}
                          type="button"
                          className="btn btn-sm"
                          style={getConfidenceStyle(color)}
                          onClick={() => selectCopyEntriesByColor(collection, color)}
                        >
                          Select {color}
                        </button>
                      ))}
                    </div>

                    {entries.length === 0 ? (
                      <p className="text-muted">No {title.toLowerCase()}.</p>
                    ) : (
                      <div
                        className="table-responsive"
                        style={{ maxHeight: "450px", overflowY: "auto" }}
                      >
                        <table className="table table-bordered align-middle">
                          <thead>
                            <tr>
                              <th>Select</th>
                              {collection === "strs" && <th>Entity</th>}
                              <th>Gene</th>

                              {collection === "genes" &&
                                selectedSourcePanel?.source === "ClinGen" && (
                                  <th>MOI</th>
                                )}

                              <th>Confidence</th>
                              <th>Phenotypes — one per line</th>
                              {collection === "strs" && (
                                <th>Repeated sequence</th>
                              )}
                              <th>Origin panel</th>
                            </tr>
                          </thead>

                          <tbody>
                            {entries.map((entry) => (
                              <tr key={entry.draftKey}>
                                <td>
                                  <input
                                    type="checkbox"
                                    className="form-check-input"
                                    aria-label={`Select ${entry.entity_name || entry.gene_symbol
                                      }`}
                                    checked={entry.selected}
                                    onChange={(event) =>
                                      updateCopyEntry(
                                        collection,
                                        entry.draftKey,
                                        "selected",
                                        event.target.checked
                                      )
                                    }
                                  />
                                </td>

                                {collection === "strs" && (
                                  <td>{entry.entity_name}</td>
                                )}

                                <td>{entry.gene_symbol || "N/A"}</td>

                                {collection === "genes" &&
                                  selectedSourcePanel?.source === "ClinGen" && (
                                    <td>{entry.moi || "N/A"}</td>
                                  )}


                                <td>
                                  <input
                                    className="form-control form-control-sm"
                                    aria-label="Confidence"
                                    value={entry.confidence_level}
                                    disabled={!entry.selected}
                                    onChange={(event) =>
                                      updateCopyEntry(
                                        collection,
                                        entry.draftKey,
                                        "confidence_level",
                                        event.target.value
                                      )
                                    }
                                  />
                                </td>

                                <td>
                                  <textarea
                                    className="form-control form-control-sm"
                                    aria-label="Phenotypes"
                                    rows={2}
                                    value={entry.phenotypes}
                                    disabled={!entry.selected}
                                    onChange={(event) =>
                                      updateCopyEntry(
                                        collection,
                                        entry.draftKey,
                                        "phenotypes",
                                        event.target.value
                                      )
                                    }
                                  />
                                </td>

                                {collection === "strs" && (
                                  <td>
                                    <input
                                      className="form-control form-control-sm"
                                      aria-label="Repeated sequence"
                                      value={entry.repeated_sequence}
                                      disabled={!entry.selected}
                                      onChange={(event) =>
                                        updateCopyEntry(
                                          collection,
                                          entry.draftKey,
                                          "repeated_sequence",
                                          event.target.value
                                        )
                                      }
                                    />
                                  </td>
                                )}

                                <td className="small">
                                  {entry.origin_panel_name ?? "N/A"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </section>

                );
              })}



              <div className="mt-3">
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ backgroundColor: "#256fa1" }}
                  disabled={copySaving}
                  onClick={handleCreateCopy}
                >
                  {copySaving ? "Creating..." : "Create laboratory panel"}
                </button>
              </div>


            </div>
          )}


        </div>
      </fieldset>



      {!copySaving && (
        <Link to="/lab-panels" className="btn btn-outline-secondary mt-3">
          Back to laboratory panels
        </Link>
      )}
    </div>
  );





}

export default CopyLabPanelPage;
