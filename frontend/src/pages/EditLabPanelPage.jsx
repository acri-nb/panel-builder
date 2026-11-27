import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";

function EditLabPanelPage() {
  const { panelId } = useParams();

  const [panel, setPanel] = useState({
    panel_name: "",
    disease_group: "",
    disease_subgroup: "",
    relevant_diseases: "",
    // last_updated: ""
  });
  const [genes, setGenes] = useState([]);
  const [strs, setStrs] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitted, setSubmitted] = useState(false);


  useEffect(() => {
    let cancelled = false;

    async function loadPanel() {
      setLoading(true);
      setError("");
      setSubmitted(false);

      try {
        const [panelResponse, genesResponse, strsResponse] =
          await Promise.all([
            api.get(`/panels/${panelId}`),
            api.get(`/panels/${panelId}/genes`),
            api.get(`/panels/${panelId}/strs`)
          ]);

        const current = panelResponse.data;

        if (current.source !== "Laboratory") {
          throw new Error("Only laboratory panels can be edited here.");
        }

        if (
          !Array.isArray(genesResponse.data) ||
          !Array.isArray(strsResponse.data)
        ) {
          throw new Error("The genes or STRs response is invalid.");
        }

        if (
          strsResponse.data.some((str) => !str.gene_symbol)
        ) {
          throw new Error(
            "The STR endpoint must return gene_symbol before this panel can be edited."
          );
        }

        if (cancelled) return;

        setPanel({
          panel_name: current.panel_name ?? "",
          disease_group: current.disease_group ?? "",
          disease_subgroup: current.disease_subgroup ?? "",
          relevant_diseases: current.relevant_diseases ?? "",
          // last_updated: current.last_updated?.slice(0, 10) ?? ""
        });

        // setGenes(
        //   genesResponse.data.map((gene) => ({
        //     gene_symbol: gene.gene_symbol ?? "",
        //     confidence_level: String(gene.confidence_level ?? ""),
        //     phenotypes: (gene.phenotypes ?? []).join("\n")
        //   }))
        // );



        setGenes(
          genesResponse.data.map((gene) => ({
            gene_symbol: gene.gene_symbol ?? "",
            confidence_level: String(gene.confidence_level ?? ""),
            phenotypes: (gene.phenotypes ?? []).join("\n"),
            moi: gene.moi ?? null,
            lab_entry_id: gene.lab_entry_id ?? null,
          }))
        );


        setStrs(
          strsResponse.data.map((str) => ({
            entity_name: str.entity_name ?? "",
            gene_symbol: str.gene_symbol ?? "",
            confidence_level: String(str.confidence_level ?? ""),
            repeated_sequence: str.repeated_sequence ?? "",
            phenotypes: (str.phenotypes ?? []).join("\n"),
            lab_entry_id: str.lab_entry_id ?? null,
          }))
        );
      } catch (err) {
        if (!cancelled) {
          const detail = err.response?.data?.detail;

          setError(
            typeof detail === "string"
              ? detail
              : err.message || "Unable to load the panel."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadPanel();

    return () => {
      cancelled = true;
    };
  }, [panelId]);

  function updatePanel(event) {
    setPanel({
      ...panel,
      [event.target.name]: event.target.value
    });
  }

  function updateGene(index, field, value) {
    setGenes((current) =>
      current.map((gene, i) =>
        i === index ? { ...gene, [field]: value } : gene
      )
    );
  }

  function updateStr(index, field, value) {
    setStrs((current) =>
      current.map((str, i) =>
        i === index ? { ...str, [field]: value } : str
      )
    );
  }

  function splitPhenotypes(text) {
    return text
      .split("\n")
      .map((value) => value.trim())
      .filter(Boolean);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (saving || loading || submitted) return;

    if (
      !panel.panel_name.trim() ||
      genes.some((gene) => !gene.gene_symbol.trim()) ||
      strs.some(
        (str) => !str.entity_name.trim() || !str.gene_symbol.trim()
      )
    ) {
      setError("Please fill in all required names and gene symbols.");
      return;
    }

    setSaving(true);
    setError("");

    const data = {
      panel_name: panel.panel_name.trim(),
      disease_group: panel.disease_group.trim() || null,
      disease_subgroup: panel.disease_subgroup.trim() || null,
      relevant_diseases: panel.relevant_diseases.trim() || null,
      // last_updated: panel.last_updated,



      // genes: genes.map((gene) => ({
      //   gene_symbol: gene.gene_symbol.trim(),
      //   confidence_level: gene.confidence_level.trim() || null,
      //   phenotypes: splitPhenotypes(gene.phenotypes)
      // })),



      genes: genes.map((gene) => ({
        gene_symbol: gene.gene_symbol.trim(),
        confidence_level: gene.confidence_level.trim() || null,
        phenotypes: splitPhenotypes(gene.phenotypes),
        moi: gene.moi ?? null,
        lab_entry_id: gene.lab_entry_id ?? null,
      })),




      strs: strs.map((str) => ({
        entity_name: str.entity_name.trim(),
        gene_symbol: str.gene_symbol.trim(),
        confidence_level: str.confidence_level.trim() || null,
        phenotypes: splitPhenotypes(str.phenotypes),
        repeated_sequence: str.repeated_sequence.trim() || null,
        lab_entry_id: str.lab_entry_id ?? null,
      }))
    };

    try {
      await api.post(`/panels/${panelId}/changes`, data);
      setSubmitted(true);
    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail
              .map((item) => `${item.loc.join(".")}: ${item.msg}`)
              .join("; ")
            : "Unable to submit the changes. Please try again."
      );
    } finally {
      setSaving(false);
    }
  }




  if (loading) {
    return (
      <div className="container mt-4">
        <p>Loading laboratory panel...</p>
      </div>
    );
  }

  if (error && !panel.panel_name) {
    return (
      <div className="container mt-4">
        <div className="alert alert-danger">{error}</div>
        <Link to="/lab-panels">Back to laboratory panels</Link>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="container mt-4">
        <div className="alert alert-success">
          Changes submitted for approval. The current panel
          remains unchanged until approval.
        </div>

        <Link to="/lab-panels" className="btn btn-secondary">
          Back to laboratory panels
        </Link>
      </div>
    );
  }


  return (
    <div className="container mt-4 mb-5">
      <h2 style={{ color: "#256FA1" }} >Modify Laboratory Panel</h2>
      <p className="text-muted">
        Your changes will be submitted for approval.
      </p>

      {error && (
        <div className="alert alert-danger">{error}</div>
      )}

      <form onSubmit={handleSubmit}>
        <fieldset disabled={saving}>
          <div className="mb-3">
            <label htmlFor="panel-name" className="form-label">
              Panel name *
            </label>
            <input
              id="panel-name"
              name="panel_name"
              className="form-control"
              value={panel.panel_name}
              onChange={updatePanel}
              required
            />
          </div>

          <div className="row">
            <div className="col-md-6 mb-3">
              <label htmlFor="disease-group" className="form-label">
                Disease group
              </label>
              <input
                id="disease-group"
                name="disease_group"
                className="form-control"
                value={panel.disease_group}
                onChange={updatePanel}
              />
            </div>

            <div className="col-md-6 mb-3">
              <label htmlFor="disease-subgroup" className="form-label">
                Disease subgroup
              </label>
              <input
                id="disease-subgroup"
                name="disease_subgroup"
                className="form-control"
                value={panel.disease_subgroup}
                onChange={updatePanel}
              />
            </div>
          </div>

          <div className="mb-3">
            <label htmlFor="relevant-diseases" className="form-label">
              Relevant diseases
            </label>
            <textarea
              id="relevant-diseases"
              name="relevant_diseases"
              className="form-control"
              value={panel.relevant_diseases}
              onChange={updatePanel}
              rows={2}
            />
          </div>

          {/* <div className="mb-4">
            <label htmlFor="last-updated" className="form-label">
              Last updated *
            </label>
            <input
              id="last-updated"
              type="date"
              name="last_updated"
              className="form-control"
              value={panel.last_updated}
              onChange={updatePanel}
              required
            />
          </div> */}

          <h4 style={{ color: "#256FA1" }} >Genes</h4>

          {genes.map((gene, index) => (
            <div className=" rounded p-3 mb-3" style={{ border: "1px solid #256fa1" }} key={index}>
              <label className="form-label d-block">
                Gene symbol *
                <input
                  className="form-control"
                  value={gene.gene_symbol}
                  onChange={(event) =>
                    updateGene(index, "gene_symbol", event.target.value)
                  }
                  required
                />
              </label>

              <label className="form-label d-block">
                Confidence level
                <input
                  className="form-control"
                  value={gene.confidence_level}
                  onChange={(event) =>
                    updateGene(index, "confidence_level", event.target.value)
                  }
                />
              </label>

              <label className="form-label d-block">
                Phenotypes — one per line
                <textarea
                  className="form-control"
                  value={gene.phenotypes}
                  onChange={(event) =>
                    updateGene(index, "phenotypes", event.target.value)
                  }
                />
              </label>

              <button
                type="button"
                className="btn btn-outline-danger btn-sm"
                onClick={() =>
                  setGenes((current) =>
                    current.filter((_, i) => i !== index)
                  )
                }
              >
                Remove gene
              </button>
            </div>
          ))}

          <button
            type="button"
            className="btn btn-outline-dark mb-4"
            onClick={() =>
              setGenes((current) => [
                ...current,
                {
                  gene_symbol: "",
                  confidence_level: "",
                  phenotypes: ""
                }
              ])
            }
          >
            Add gene
          </button>

          <h4 style={{ color: "#256FA1" }} >STRs</h4>

          {strs.map((str, index) => (
            <div className="rounded p-3 mb-3" style={{ border: "1px solid #256fa1" }} key={index}>
              <label className="form-label d-block">
                Entity name *
                <input
                  className="form-control"
                  value={str.entity_name}
                  onChange={(event) =>
                    updateStr(index, "entity_name", event.target.value)
                  }
                  required
                />
              </label>

              <label className="form-label d-block">
                Gene symbol *
                <input
                  className="form-control"
                  value={str.gene_symbol}
                  onChange={(event) =>
                    updateStr(index, "gene_symbol", event.target.value)
                  }
                  required
                />
              </label>

              <label className="form-label d-block">
                Confidence level
                <input
                  className="form-control"
                  value={str.confidence_level}
                  onChange={(event) =>
                    updateStr(index, "confidence_level", event.target.value)
                  }
                />
              </label>

              <label className="form-label d-block">
                Repeated sequence
                <input
                  className="form-control"
                  value={str.repeated_sequence}
                  onChange={(event) =>
                    updateStr(index, "repeated_sequence", event.target.value)
                  }
                />
              </label>

              <label className="form-label d-block">
                Phenotypes — one per line
                <textarea
                  className="form-control"
                  value={str.phenotypes}
                  onChange={(event) =>
                    updateStr(index, "phenotypes", event.target.value)
                  }
                />
              </label>

              <button
                type="button"
                className="btn btn-outline-danger btn-sm"
                onClick={() =>
                  setStrs((current) =>
                    current.filter((_, i) => i !== index)
                  )
                }
              >
                Remove STR
              </button>
            </div>
          ))}

          <button
            type="button"
            className="btn btn-outline-dark mb-4"
            onClick={() =>
              setStrs((current) => [
                ...current,
                {
                  entity_name: "",
                  gene_symbol: "",
                  confidence_level: "",
                  repeated_sequence: "",
                  phenotypes: ""
                }
              ])
            }
          >
            Add STR
          </button>

          <div className="d-flex gap-2">
            <button type="submit" className="btn btn-success">
              {saving ? "Submitting..." : "Submit for approval"}
            </button>

            {!saving && (
              <Link to="/lab-panels" className="btn btn-outline-secondary">
                Cancel
              </Link>
            )}
          </div>
        </fieldset>
      </form>
    </div>
  );
}

export default EditLabPanelPage;