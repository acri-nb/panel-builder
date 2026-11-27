import { useEffect, useState } from "react";
import api from "../services/api";

const metadataFields = [
  "panel_name",
  "disease_group",
  "disease_subgroup",
  "relevant_diseases",
  "last_updated"
];

const geneFields = [
  "gene_symbol",
  "confidence_level",
  "phenotypes"
];

const strFields = [
  "entity_name",
  "gene_symbol",
  "confidence_level",
  "phenotypes",
  "repeated_sequence"
];

function normalize(value, field) {
  if (field === "phenotypes") {
    const values = Array.isArray(value)
      ? value
      : value
        ? [value]
        : [];

    return JSON.stringify(
      [...new Set(values.map((item) => item.trim()).filter(Boolean))]
        .sort()
    );
  }

  return String(value ?? "").trim();
}

function display(value) {
  if (Array.isArray(value)) {
    return value.join("; ") || "—";
  }

  return value === null || value === undefined || value === ""
    ? "—"
    : String(value);
}

function fieldLabel(field) {
  return field.replaceAll("_", " ");
}

// Build an index without silently overwriting duplicate entries.
function indexItems(items, getKey, label) {
  const result = new Map();

  for (const item of items) {
    const key = getKey(item);

    if (result.has(key)) {
      throw new Error(
        `Duplicate ${label} identity found. Check the panel data before comparing.`
      );
    }

    result.set(key, item);
  }

  return result;
}

function compareItems(oldItems, newItems, getKey, fields, label) {
  const oldMap = indexItems(oldItems, getKey, label);
  const newMap = indexItems(newItems, getKey, label);
  const keys = [...new Set([...oldMap.keys(), ...newMap.keys()])].sort();

  const rows = [];

  for (const key of keys) {
    const oldItem = oldMap.get(key);
    const newItem = newMap.get(key);
    const item = newItem || oldItem;

    const itemName =
      label === "gene"
        ? item.gene_symbol
        : `${item.entity_name} (${item.gene_symbol || "No gene"})`;

    const status = !oldItem
      ? "Added"
      : !newItem
        ? "Removed"
        : "Modified";

    for (const field of fields) {
      const oldValue = oldItem?.[field];
      const newValue = newItem?.[field];

      if (
        status !== "Modified" ||
        normalize(oldValue, field) !== normalize(newValue, field)
      ) {
        rows.push({
          item: itemName,
          status,
          field,
          oldValue,
          newValue
        });
      }
    }
  }

  return rows;
}

function buildComparison(base, proposed) {
  const metadata = metadataFields
    .filter(
      (field) =>
        normalize(base[field], field) !==
        normalize(proposed[field], field)
    )
    .map((field) => ({
      item: "Panel",
      status: "Modified",
      field,
      oldValue: base[field],
      newValue: proposed[field]
    }));

  const genes = compareItems(
    base.genes || [],
    proposed.genes || [],
    (gene) => gene.gene_symbol,
    geneFields,
    "gene"
  );

  const strs = compareItems(
    base.strs || [],
    proposed.strs || [],
    (str) => JSON.stringify([str.entity_name, str.gene_symbol]),
    strFields,
    "STR"
  );

  return { metadata, genes, strs };
}

function DifferenceTable({ title, rows }) {
  return (
    <div className="mb-3">
      <h6>{title}</h6>

      {rows.length === 0 ? (
        <p className="text-muted">No changes.</p>
      ) : (
        <div className="table-responsive">
          <table className="table table-bordered table-sm">
            <thead>
              <tr>
                <th>Item</th>
                <th>Change</th>
                <th>Field</th>
                <th>Old</th>
                <th>Proposed</th>
              </tr>
            </thead>

            <tbody>
              {rows.map((row, index) => (
                <tr
                  key={index}
                  className={
                    row.status === "Added"
                      ? "table-success"
                      : row.status === "Removed"
                        ? "table-danger"
                        : "table-warning"
                  }
                >
                  <td>{row.item}</td>
                  <td>{row.status}</td>
                  <td>{fieldLabel(row.field)}</td>
                  <td style={{ whiteSpace: "pre-wrap" }}>
                    {display(row.oldValue)}
                  </td>
                  <td style={{ whiteSpace: "pre-wrap" }}>
                    {display(row.newValue)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function LabChangeComparison({ panelId, change }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [comparison, setComparison] = useState(null);
  const [baseVersion, setBaseVersion] = useState(null);

  const baseId = change.change_version_id;
  const proposed = change.proposed_data;

  useEffect(() => {
    if (!open) return;

    let cancelled = false;

    async function loadComparison() {
      setLoading(true);
      setError("");
      setComparison(null);

      try {
        // Resolve the database version ID to its version number.
        const versionsResponse = await api.get(
          `/panels/${panelId}/versions`
        );

        const base = versionsResponse.data.find(
          (version) =>
            String(version.panel_version_id) === String(baseId)
        );

        if (!base) {
          throw new Error("The original version for this request was not found.");
        }

        // Retrieve that exact version, including genes and STRs.
        const response = await api.get(
          `/panels/${panelId}/versions/${base.version_number}`
        );

        if (
          String(response.data.panel_version_id) !== String(baseId)
        ) {
          throw new Error("The returned version does not match this request.");
        }

        if (!proposed || !Array.isArray(proposed.genes) ||
            !Array.isArray(proposed.strs)) {
          throw new Error("The request does not contain complete proposed data.");
        }

        const differences = buildComparison(response.data, proposed);

        if (!cancelled) {
          setBaseVersion(base.version_number);
          setComparison(differences);
        }
      } catch (err) {
        if (!cancelled) {
          const detail = err.response?.data?.detail;

          setError(
            typeof detail === "string"
              ? detail
              : err.message || "Unable to compare this request."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadComparison();

    return () => {
      cancelled = true;
    };
  }, [open, panelId, baseId, proposed]);

  return (
    <div className="mb-3">
      <button
        type="button"
         className="btn btn-sm" 
  style={{ backgroundColor: '#256fa1', borderColor: '#256fa1', color: '#ffffff' }}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {open ? "Hide comparison" : "Compare changes"}
      </button>



      {open && (
        <div className="border rounded p-3 mt-2">
          {loading && <p>Loading comparison...</p>}

          {error && (
            <div className="alert alert-danger">{error}</div>
          )}

          {!loading && !error && comparison && (
            <>
              <p>
                <strong>Base version {baseVersion} → proposed data</strong>
              </p>

              <DifferenceTable
                title="Metadata"
                rows={comparison.metadata}
              />

              <DifferenceTable
                title="Genes"
                rows={comparison.genes}
              />

              <DifferenceTable
                title="STRs"
                rows={comparison.strs}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default LabChangeComparison;