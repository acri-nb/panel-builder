function SearchBar({
  searchTerm,
  setSearchTerm,
  searchType,
  setSearchType,
  handleSearch,
  sourceFilter = "all",
  availableSources = [],
  showSourceFilter = true,
  // onSourceFilterChange = () => { }
  onSourceFilterChange = () => { },
  confidenceFilter = "all",
  onConfidenceFilterChange = () => { }
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    handleSearch();
  };

  return (
    <div className="card p-4 shadow-sm">
      <h4 className="mb-3">Search Panels</h4>

      <form onSubmit={handleSubmit}>
        <div className="row g-2">

          <div className="col-md-3">
            <select
              className="form-select"
              value={searchType}
              onChange={(e) => setSearchType(e.target.value)}
            >
              <option value="name">Panel Name</option>
              <option value="gene">Gene</option>
              <option value="disease">Disease / HP</option>
            </select>
          </div>

          <div className="col-md-7">
            <input
              type="text"
              className="form-control"
              placeholder="Enter search term..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="col-md-2">
            <button
              type="submit"
              className="btn btn-primary w-100"
              // #25ADD7
              style={{ backgroundColor: "#477DAB", borderColor: "#1E646B" }}
            >
              Search
            </button>
          </div>

        </div>

        {showSourceFilter && (
          <fieldset className="mt-2">
            <legend className="form-label small mb-1">Filter by source</legend>

            <div className="d-flex flex-nowrap gap-3 overflow-auto pb-1">
              {[
                { label: "All sources", value: "all" },
                { label: "Laboratory", value: "__lab_panels__" },
                ...availableSources
                  .filter((source) => source !== "GenCC")
                  .map((source) => ({
                    label: source,
                    value: source,
                  })),

                // ...availableSources.map((source) => ({
                //   label: source,
                //   value: source,
                // })),
              ].map((option, index) => (
                <div
                  className="form-check form-check-inline mb-0 flex-shrink-0"
                  key={option.value}
                >
                  <input
                    className="form-check-input"
                    type="radio"
                    name="sourceFilter"
                    id={`source-filter-${index}`}
                    value={option.value}
                    checked={sourceFilter === option.value}
                    onChange={() => onSourceFilterChange(option.value)}
                  />
                  <label
                    className="form-check-label"
                    htmlFor={`source-filter-${index}`}
                  >
                    {option.label}
                  </label>
                </div>
              ))}
            </div>
          </fieldset>
          )}

          {searchType === "gene" && (
          <fieldset className="mt-3">
            <legend className="form-label small mb-1">
              Filter searched gene by confidence
            </legend>

            <div className="d-flex flex-wrap gap-2">
              {[
                { label: "All", value: "all", style: "secondary" },
                { label: "Green", value: "green", style: "success" },
                { label: "Amber", value: "yellow", style: "warning" },
                { label: "Red", value: "red", style: "danger" },
              ].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`btn btn-sm btn-${confidenceFilter === option.value ? "" : "outline-"
                    }${option.style}`}
                  aria-pressed={confidenceFilter === option.value}
                  onClick={() =>
                    onConfidenceFilterChange(option.value)
                  }
                >
                  {option.label}
                </button>
              ))}
            </div>
          </fieldset>
        )}
      </form>
    </div>
  );
}

export default SearchBar;















