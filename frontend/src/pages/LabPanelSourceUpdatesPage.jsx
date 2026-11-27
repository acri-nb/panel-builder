import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";






function displayValue(value) {
  if (value == null || value === "") return "N/A";
  if (Array.isArray(value)) return value.join(", ") || "None";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
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



function EntityChanges({ title, changes, kind, source, showOrigin }) {
  const isStr = kind === "strs";
  const asEntries = (value) =>
    Array.isArray(value) ? value : value ? [value] : [];

  const rows = [
    ...(changes?.added ?? []).map((entry) => ({
      status: "Added", old: [], current: [entry],
    })),
    ...(changes?.removed ?? []).map((entry) => ({
      status: "Removed", old: [entry], current: [],
    })),
    ...(changes?.modified ?? []).map((item) => ({
      status: "Modified",
      old: asEntries(item.old),
      current: asEntries(item.new),
    })),
  ];

  const [showAll, setShowAll] = useState(false);
  const previewLimit = 5;

  if (!rows.length) return null;

  function renderEntries(entries) {
    if (!entries.length) {
      return <span className="text-muted">—</span>;
    }

    return entries.map((entry, index) => (
      <div key={index} className={index ? "border-top mt-2 pt-2" : ""}>
        <span
          className="badge"
          style={getConfidenceStyle(entry.confidence_level)}
          title={`Confidence: ${displayValue(entry.confidence_level)}`}
        >
          {displayValue(isStr ? entry.entity_name : entry.gene_symbol)}
        </span>

        {isStr && (
          <div className="small text-muted">
            {displayValue(entry.gene_symbol)} ·{" "}
            {displayValue(entry.repeated_sequence)}
          </div>
        )}

        {entry.phenotypes?.length > 0 && (
          <div className="small text-muted">
            {displayValue(entry.phenotypes)}
          </div>
        )}

        {source === "ClinGen" && entry.moi && (
          <div className="small text-muted">MOI: {entry.moi}</div>
        )}

        {showOrigin && entry.origin_panel_id != null && (
          <div className="small text-muted">
            Origin panel ID: {entry.origin_panel_id}
          </div>
        )}
      </div>
    ));
  }













  return (
    <section className="mt-3">
      <h3 className="h5">{title}</h3>
      <div className="table-responsive">
        <table className="table table-bordered table-sm align-top mb-0">
          <thead className="table-light">
            <tr>
              <th scope="col">Change</th>
              <th scope="col" style={{ width: "44%" }}>Old Panel</th>
              <th scope="col" style={{ width: "44%" }}>Updated Panel</th>
            </tr>
          </thead>
          <tbody>
            {(showAll ? rows : rows.slice(0, previewLimit)).map((row, index) => (
              <tr key={index}>
                <th scope="row">{row.status}</th>
                <td>{renderEntries(row.old)}</td>
                <td>{renderEntries(row.current)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > previewLimit && (
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm mt-2"
          aria-expanded={showAll}
          onClick={() => setShowAll((current) => !current)}
        >
          {showAll ? "Show less" : `Show ${rows.length - previewLimit} more`}
        </button>
      )}
    </section>
  );
}


















function getSelectableKeys(updates, prefix = "") {
  const keys = [];

  for (const item of updates?.proposals ?? []) {
    if (item.action === "remove") {
      keys.push(
        item.match_by_name
          ? `remove-by-name:${item.base_version_gene_id}`
          : `${prefix}remove:${item.lab_entry_id}`
      );
    }

    if (item.action === "update") {
      for (const [field, change] of Object.entries(item.fields ?? {})) {
        if (["update_available", "conflict"].includes(change.status)) {
          keys.push(`${prefix}update:${item.lab_entry_id}:${field}`);
        }
      }
    }
  }

  (updates?.new_source_entries ?? []).forEach((group, groupIndex) => {
    if (group.requires_manual_matching) return;

    group.entries.forEach((_, entryIndex) => {
      keys.push(`${prefix}add:${groupIndex}:${entryIndex}`);
    });
  });

  return keys;
}


// function LabGeneProposals({ updates, selected, onToggle }) {

function LabEntityProposals({
  updates,
  selected,
  onToggle,
  kind = "genes",
}) {
  const isStr = kind === "strs";
  const prefix = isStr ? "str:" : "";
  const nameField = isStr ? "entity_name" : "gene_symbol";
  const proposals = updates?.proposals || [];
  const additions = updates?.new_source_entries || [];
  const warnings = updates?.warnings || [];
  const removed = proposals.filter((item) => item.action === "remove");
  const modified = proposals.filter((item) => item.action === "update");

  const [expandedGroups, setExpandedGroups] = useState({});
  const previewLimit = 5;

  function visibleEntries(group, entries) {
    return expandedGroups[group] ? entries : entries.slice(0, previewLimit);
  }


  const addedEntries = additions.flatMap((group, groupIndex) =>
    group.entries.map((entry, entryIndex) => ({
      group,
      groupIndex,
      entry,
      entryIndex,
    }))
  );
  function renderShowMore(group, count) {
    if (count <= previewLimit) return null;

    const expanded = Boolean(expandedGroups[group]);









    return (
      <button
        type="button"
        className="btn btn-outline-secondary btn-sm mt-2"
        aria-expanded={expanded}
        onClick={() =>
          setExpandedGroups((current) => ({
            ...current,
            [group]: !current[group],
          }))
        }
      >
        {expanded ? "Show less" : `Show ${count - previewLimit} more`}
      </button>
    );
  }

  if (!proposals.length && !additions.length && !warnings.length) {
    return null;
  }

  function entryBadge(name, confidence) {
    return (
      <span className="badge" style={getConfidenceStyle(confidence)}>
        {name}
      </span>
    );
  }

  function phenotypeText(phenotypes) {
    return phenotypes?.length ? (
      <span className="small text-muted">
        {displayValue(phenotypes)}
      </span>
    ) : null;
  }




  return (
    <section className="card mb-4">
      <div
        className="card-header"
        style={{ backgroundColor: "#C7DDF0" }}
      >
        <h2 className="h5 mb-0">	Proposed laboratory {isStr ? "STR" : "gene"} updates</h2>
      </div>

      <div className="card-body">
        <p className="small text-muted">
          Select the changes you want to include in a laboratory
          change request. Nothing is selected automatically.
        </p>

        {!proposals.length && !additions.length && (
          <p>No laboratory {isStr ? "STR" : "gene"} updates proposed.</p>
        )}














        {addedEntries.length > 0 && (
          <section className="mb-3">
            <h3 className="h6">Added Entries</h3>

            {visibleEntries("additions", addedEntries).map(
              ({ group, groupIndex, entry, entryIndex }) => {

                const key = `${prefix}add:${groupIndex}:${entryIndex}`;
                const matchingNames = isStr
                  ? group.matching_lab_entities
                  : group.matching_lab_symbols;

                return (
                  <div key={key} className="border-bottom py-2">
                    <label className="d-flex flex-wrap align-items-baseline gap-2">
                      <input
                        type="checkbox"
                        checked={Boolean(selected[key])}
                        disabled={group.requires_manual_matching}
                        onChange={() => onToggle(key)}
                      />

                      {entryBadge(entry[nameField], entry.confidence_level)}

                      {/* <span className="small text-muted"> Added</span> */}
                      {/* {phenotypeText(entry.phenotypes)} */}
                      {isStr && entry.repeated_sequence && (
                        <span className="small text-muted">
                          Repeat: {entry.repeated_sequence}
                        </span>
                      )}
                    </label>

                    {matchingNames?.length > 0 && (
                      <div className="small text-muted ms-4">
                        An entry with this name already exists in the lab.
                        Check its origin before adding another.
                      </div>
                    )}

                    {group.requires_manual_matching && (
                      <div className="small text-danger ms-4">
                        Repeated source entries require manual matching.
                      </div>
                    )}
                  </div>
                );
              }

            )}

            {renderShowMore("additions", addedEntries.length)}
          </section>
        )}

        {
          removed.length > 0 && (
            <section className="mb-3">
              <h3 className="h6">Removed Entries</h3>

              {visibleEntries("removed", removed).map((item) => {
                const key = item.match_by_name
                  ? `remove-by-name:${item.base_version_gene_id}`
                  : `${prefix}remove:${item.lab_entry_id}`;



                return (
                  <label
                    key={key}
                    className="d-flex flex-wrap align-items-baseline gap-2 border-bottom py-2"
                  >
                    <input
                      type="checkbox"
                      checked={Boolean(selected[key])}
                      onChange={() => onToggle(key)}
                    />

                    {/* <span>
                    {isStr ? "Remove " : "Remove "}
                  </span> */}


                    {item.match_by_name && (
                      <span className="small text-muted">Matched by name</span>
                    )}




                    {entryBadge(item[nameField], item.current_lab?.confidence_level)}
                    {/* {phenotypeText(item.current_lab?.phenotypes)} */}
                  </label>
                );
              })}
              {renderShowMore("removed", removed.length)}

            </section>
          )
        }

        {
          modified.length > 0 && (
            <section className="mb-3">
              <h3 className="h6">Modified Entries</h3>

              {visibleEntries("modified", modified).map((item) => {
                const fields = Object.entries(item.fields || {});
                const fieldKey = (field) =>
                  `${prefix}update:${item.lab_entry_id}:${field}`;

                const selectableKeys = fields
                  .filter(([, change]) =>
                    ["update_available", "conflict"].includes(change.status)
                  )
                  .map(([field]) => fieldKey(field));

                const allSelected =
                  selectableKeys.length > 0 &&
                  selectableKeys.every((key) => selected[key]);

                const hasConflict = fields.some(
                  ([, change]) => change.status === "conflict"
                );

                return (
                  <div key={item.lab_entry_id} className="border-bottom py-2">
                    <label className="d-flex flex-wrap align-items-baseline gap-2">
                      <input
                        type="checkbox"
                        disabled={!selectableKeys.length}
                        checked={allSelected}
                        onChange={(event) => {
                          const checked = event.target.checked;

                          selectableKeys.forEach((key) => {
                            if (Boolean(selected[key]) !== checked) onToggle(key);
                          });
                        }}
                      />

                      {entryBadge(
                        item[nameField],
                        item.fields?.confidence_level?.new_source
                      )}

                      {/* <span className="small text-muted"> Modified</span> */}


                      {/* {phenotypeText(item.fields?.phenotypes?.new_source)} */}
                      {hasConflict && (
                        <span className="badge text-bg-warning">
                          Replaces a lab edit
                        </span>
                      )}
                    </label>


                  </div>
                );
              })}
              {renderShowMore("modified", modified.length)}
            </section>
          )
        }


        {
          warnings.length > 0 && (
            <div className="alert alert-warning mt-3">
              <strong>Entries requiring review</strong>
              <ul className="mb-0 mt-2">
                {warnings.map((warning, index) => (
                  <li key={index}>
                    {warning[nameField]}: {warning.reason}
                  </li>
                ))}
              </ul>
            </div>
          )
        }




        <p className="small text-muted mt-3 mb-0">
          {Object.entries(selected).filter(([key, checked]) =>
            checked &&
            (isStr ? key.startsWith("str:") : !key.startsWith("str:"))
          ).length} change(s) selected.
        </p>
      </div >
    </section >
  );
}




















function LabPanelSourceUpdatesPage() {
  const { panelId } = useParams();

  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedChanges, setSelectedChanges] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [submittedChangeId, setSubmittedChangeId] = useState(null);
  const [markingReviewed, setMarkingReviewed] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [reviewSuccess, setReviewSuccess] = useState("");

  function toggleSelectedChange(key) {
    setSelectedChanges((current) => ({
      ...current,
      [key]: !current[key],
    }));
  }

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError("");
    setReport(null);
    setSelectedChanges({});
    setSubmittedChangeId(null);
    setSubmitError("");
    setReviewError("");
    setReviewSuccess("");

    async function loadUpdates() {
      try {
        const response = await api.get(
          `/lab-panels/${panelId}/source-updates`
        );

        if (!cancelled) setReport(response.data);
      } catch (requestError) {
        if (!cancelled) {
          const detail = requestError.response?.data?.detail;

          setError(
            typeof detail === "string"
              ? detail
              : "Unable to load source updates."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadUpdates();

    return () => {
      cancelled = true;
    };
  }, [panelId]);








  async function submitSelectedUpdates() {
    if (!report || submitting || markingReviewed || submittedChangeId) return;

    const selectedKeys = Object.keys(selectedChanges).filter(
      (key) => selectedChanges[key]
    );

    if (!selectedKeys.length) return;

    setSubmitting(true);
    setSubmitError("");

    try {
      const response = await api.post(
        `/lab-panels/${panelId}/source-updates/changes`,
        {
          laboratory_version_id: report.laboratory_version_id,
          review_token: report.review_token,
          selected_keys: selectedKeys,
        }
      );

      setSubmittedChangeId(response.data.change_id);
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;

      setSubmitError(
        typeof detail === "string"
          ? detail
          : "Unable to submit the laboratory change request."
      );
    } finally {
      setSubmitting(false);
    }
  }


  async function markSourceUpdatesReviewed() {
    if (!report?.review_token || submitting || markingReviewed) return;

    const confirmed = window.confirm(
      "Mark all displayed source changes as reviewed? " +
      "This updates the comparison baseline, including changes " +
      "you chose not to apply. Your laboratory panel will stay unchanged."
    );

    if (!confirmed) return;

    setMarkingReviewed(true);
    setReviewError("");
    setReviewSuccess("");

    try {
      const response = await api.post(
        `/lab-panels/${panelId}/source-updates/review`,
        {
          review_token: report.review_token,
        }
      );

      setReport(response.data.report);
      setSelectedChanges({});
      setSubmittedChangeId(null);
      setSubmitError("");
      setReviewSuccess("Source baseline updated successfully.");
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;

      setReviewError(
        typeof detail === "string"
          ? detail
          : "Unable to mark source updates as reviewed."
      );
    } finally {
      setMarkingReviewed(false);
    }
  }








  const selectableKeys = [
    ...getSelectableKeys(report?.lab_gene_updates),
    ...getSelectableKeys(report?.lab_str_updates, "str:"),
  ];

  const allEntriesSelected =
    selectableKeys.length > 0 &&
    selectableKeys.every((key) => selectedChanges[key]);

  function toggleAllEntries() {
    setSelectedChanges((current) => ({
      ...current,
      ...Object.fromEntries(
        selectableKeys.map((key) => [key, !allEntriesSelected])
      ),
    }));
  }













  return (
    <div className="container mt-4 mb-5">






      <header className="mb-4">
        <p className="small fw-semibold text-uppercase text-muted mb-1">
          Source updates
        </p>

        {report?.results?.map((result) => (
          <div
            key={result.original_panel_id}
            className="d-flex flex-wrap align-items-center gap-2 mb-2"
          >
            <h2 className="h3 mb-0" style={{ color: "#256FA1" }}>
              {result.panel_name}
            </h2>
            <span
              className="badge rounded-pill"
              style={{ backgroundColor: "#EAF2F8", color: "#256FA1" }}
            >
              {result.source}
            </span>
          </div>
        ))}
      </header>




      {loading && <p>Loading source updates...</p>}

      {error && (
        <div className="alert alert-danger">{error}</div>
      )}

      {report && (
        <>




          <fieldset
            disabled={
              submitting ||
              markingReviewed ||
              submittedChangeId !== null
            }
          >
            {selectableKeys.length > 0 && (
              <button
                type="button"
                className="btn btn-sm btn-outline-primary mb-3"
                onClick={toggleAllEntries}
              >
                {allEntriesSelected ? "Deselect all entries" : "Select all entries"}
              </button>
            )}



            <LabEntityProposals
              kind="genes"
              updates={report.lab_gene_updates}
              selected={selectedChanges}
              onToggle={toggleSelectedChange}
            />

            <LabEntityProposals
              kind="strs"
              updates={report.lab_str_updates}
              selected={selectedChanges}
              onToggle={toggleSelectedChange}
            />
          </fieldset>








          <details className=" mb-3">
            <summary className="fw-semibold" style={{ cursor: "pointer" }}>
              Full comparison
            </summary>

            <div className="mt-3">




              {report.results
                .filter((result) => result.status !== "unchanged")
                .map((result) => (
                  <div
                    key={result.original_panel_id}
                    className="card mb-4"
                    style={{ border: "1px solid #256fa1" }}
                  >
                    <div className="card-header" style={{ backgroundColor: "#C7DDF0", border: "1px solid #256fa1" }} >
                      <h2 className="h5 mb-2">
                        {result.panel_name}
                      </h2>

                      <span className="text-muted">
                        {result.source}
                      </span>


                      <span className="badge text-bg-info ms-3">
                        {result.status}
                      </span>
                    </div>

                    <div className="card-body">
                      {result.status === "removed" && (
                        <div className="alert alert-warning">
                          The original source panel is no longer active
                          or available.
                        </div>
                      )}

                      {Object.keys(result.metadata_changes || {}).length > 0 && (
                        <>
                          <h3 className="h5">Metadata changes</h3>

                          <div className="table-responsive">
                            <table className="table table-bordered">
                              <thead>
                                <tr>
                                  <th>Field</th>
                                  <th>Old Panel</th>
                                  <th>Updated Panel</th>
                                </tr>
                              </thead>

                              <tbody>
                                {Object.entries(result.metadata_changes).map(
                                  ([field, values]) => (
                                    <tr key={field}>
                                      <td>{field.replaceAll("_", " ")}</td>
                                      <td>{displayValue(values.old)}</td>
                                      <td>{displayValue(values.new)}</td>
                                    </tr>
                                  )
                                )}
                              </tbody>
                            </table>
                          </div>
                        </>
                      )}

                      <EntityChanges
                        title="Gene changes"
                        changes={result.gene_changes}
                        kind="genes"
                        source={result.source}
                        showOrigin={
                          [result.baseline, result.current_source].some(
                            (snapshot) =>
                              Array.isArray(snapshot?.child_panel_ids) &&
                              snapshot.child_panel_ids.length > 0
                          )
                        }
                      />

                      <EntityChanges
                        title="STR changes"
                        changes={result.str_changes}
                        kind="strs"
                        source={result.source}
                        showOrigin={
                          [result.baseline, result.current_source].some(
                            (snapshot) =>
                              Array.isArray(snapshot?.child_panel_ids) &&
                              snapshot.child_panel_ids.length > 0
                          )
                        }
                      />
                    </div>
                  </div>
                ))}

            </div>
          </details>







          {submitError && (
            <div className="alert alert-danger">{submitError}</div>
          )}

          {submittedChangeId !== null ? (
            <div className="alert alert-success">
              Change request #{submittedChangeId} submitted.
              {" "}
              <Link to={`/lab-panels/${panelId}/changes`}>
                Review laboratory changes
              </Link>
            </div>
          ) : (
            <button
              type="button"
              className="btn btn-primary mb-4"
              style={{
                backgroundColor: "#256FA1",
                borderColor: "#256FA1",
              }}
              disabled={
                submitting ||
                !report.review_token ||
                !Object.values(selectedChanges).some(Boolean)
              }
              onClick={submitSelectedUpdates}
            >
              {submitting
                ? "Submitting..."
                : "Submit laboratory change request"}
            </button>
          )}





          <div className="mb-4">
            <button
              type="button"
              className="btn btn-outline-primary"
              disabled={
                submitting ||
                markingReviewed ||
                !report.review_token ||
                submittedChangeId !== null ||
                Object.values(selectedChanges).some(Boolean)
              }
              onClick={markSourceUpdatesReviewed}
            >
              {markingReviewed
                ? "Updating baseline..."
                : "Mark source updates as reviewed"}
            </button>

            <p className="small text-muted mt-2 mb-0">
              After selecting and submitting the updates you want to apply to your lab panel, click Mark source updates as reviewed. This saves the latest source version as the starting point for future comparisons. It also marks any updates you chose to skip as reviewed, so they won’t appear again unless the source changes further.

              This button only updates the comparison baseline. Your lab panel changes when the submitted request is approved.
            </p>
          </div>

          {reviewError && (
            <div className="alert alert-danger">{reviewError}</div>
          )}

          {reviewSuccess && (
            <div className="alert alert-success">{reviewSuccess}</div>
          )}





        </>

      )
      }





      <div className="d-flex flex-wrap gap-2 mb-4">


        <Link
          to="/lab-panels"
          className="btn btn-outline-secondary"
        >
          Back to laboratory panels
        </Link>

        <Link
          to={`/panels/${panelId}`}
          className="btn btn-outline-secondary"
        >
          View laboratory panel
        </Link>
      </div>
    </div >
  );
}

export default LabPanelSourceUpdatesPage;



