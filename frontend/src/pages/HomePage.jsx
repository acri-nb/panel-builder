import { useRef, useState } from "react";
import SearchBar from "../components/SearchBar";
import api from "../services/api";
// import SearchResults from "../components/SearchResults";
import PanelGeneTable from "../components/PanelGeneTable";
import OrphanetResults from "../components/OrphanetResults";

const LAB_PANEL_FILTER_VALUE = "__lab_panels__";
const LAB_PANEL_SOURCE_NAMES = new Set([
  "laboratory",
  "laboratory panels",
  "lab panels",
]);

function isLabPanelSource(source) {
  return LAB_PANEL_SOURCE_NAMES.has(source?.trim().toLowerCase());
}

function HomePage() {
  const [searchTerm, setSearchTerm] = useState(
    sessionStorage.getItem("searchTerm") || ""
  );
  const latestSearch = useRef(0);

  const [totalGroups, setTotalGroups] = useState(
    Number(sessionStorage.getItem("searchTotal")) || 0
  );

  const [genePage, setGenePage] = useState(1);

  // const [listPage, setListPage] = useState(1);
  // const LIST_PAGE_SIZE = 20;
  const [genccPage, setGenccPage] = useState(1);

  const [searchType, setSearchType] = useState(
    sessionStorage.getItem("searchType") || "name"
  );

  const [results, setResults] = useState(() => {
    const savedResults = sessionStorage.getItem("searchResults");

    return savedResults ? JSON.parse(savedResults) : [];
  });

  const [hasSearched, setHasSearched] = useState(
    sessionStorage.getItem("hasSearched") === "true"
  );

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resultView, setResultView] = useState("genes");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [confidenceFilter, setConfidenceFilter] = useState("all");

  const [submittedSearch, setSubmittedSearch] = useState({
    type: sessionStorage.getItem("searchType") || "name",
    term: sessionStorage.getItem("searchTerm") || "",
  });

  const handleConfidenceFilterChange = (value) => {
    setConfidenceFilter(value);
    setGenePage(1);
    setGenccPage(1);
  };

  const handleSourceFilterChange = (value) => {
    setSourceFilter(value);
    setGenccPage(1);
    setGenePage(1);
  };

  const handleSearch = () => {
    //   setListPage(page);
    // setLoading(true);
    setGenePage(1);
    setGenccPage(1);
    setLoading(true);
    setError("");
    setResults([]);
    setHasSearched(true);
    setSourceFilter("all");
    const searchId = ++latestSearch.current;


    setSubmittedSearch({
      type: searchType,
      term: searchTerm.trim(),
    });



    api
      .get("/panels/search", {
        params: {
          [searchType]: searchTerm,
          // limit: LIST_PAGE_SIZE,
          // offset: (page - 1) * LIST_PAGE_SIZE,
        },
      })
      .then((response) => {
        if (searchId !== latestSearch.current) return;
        setResults(response.data);
        setTotalGroups(response.data.total);

        sessionStorage.setItem("searchTerm", searchTerm);
        sessionStorage.setItem("searchType", searchType);
        sessionStorage.setItem("searchTotal", String(response.data.total));

        try {
          sessionStorage.setItem(
            "searchResults",
            JSON.stringify(response.data)
          );
        } catch (error) {
          if (error.name === "QuotaExceededError") {
            sessionStorage.removeItem("searchResults");
          } else {
            throw error;
          }
        }
        // sessionStorage.setItem(
        //   "searchResults",
        //   JSON.stringify(response.data)
        // );


        sessionStorage.setItem("hasSearched", "true");
      })
      .catch((error) => {
        if (searchId !== latestSearch.current) return;

        console.error("Search error:", error);
        setError("Something went wrong while searching.");
      })
      .finally(() => {
        if (searchId === latestSearch.current) {
          setLoading(false);
        }
      });
  };

  const groupSearchResults = (results) => {
    const grouped = {};

    const ontarioCounts = {};

    results.forEach((panel) => {
      if (panel.source === "Ontario Health") {
        const name = panel.panel_name?.trim().toLowerCase();
        ontarioCounts[name] = (ontarioCounts[name] || 0) + 1;
      }
    });

    results.forEach((panel) => {



      const diseaseName =
        panel.panel_name?.trim().toLowerCase();

      const shouldGroup =
        panel.source === "GenCC" ||
        panel.source === "ClinGen" ||
        (
          panel.source === "Ontario Health" &&
          ontarioCounts[diseaseName] > 1
        );



      const key = `${panel.source}-${diseaseName}`;

      if (!grouped[key]) {
        grouped[key] = {
          source: panel.source,
          panel_name: panel.panel_name,
          isGrouped: true,
          records: [panel],
          record_count: 1,
        };
      } else {
        grouped[key].records.push(panel);
        grouped[key].record_count =
          grouped[key].records.length;
      }
    });

    return Object.values(grouped);
  };


  const safeResults = Array.isArray(results) ? results : [];

  const availableSources = [
    ...new Set(
      safeResults
        .map((panel) => panel.source)
        .filter((source) => source && !isLabPanelSource(source))
    ),
  ].sort();

  // const filteredResults =
  const sourceFilteredResults =
    sourceFilter === "all"
      ? safeResults
      : sourceFilter === LAB_PANEL_FILTER_VALUE
        ? safeResults.filter((panel) => isLabPanelSource(panel.source))
        : safeResults.filter((panel) => panel.source === sourceFilter);


  const confidenceAliases = {
    "1": "red",
    red: "red",
    "2": "yellow",
    amber: "yellow",
    orange: "yellow",
    yellow: "yellow",
    "3": "green",
    green: "green",
    definitive: "green",
    strong: "green",
    moderate: "green",
    limited: "red",
    disputed: "red",
    refuted: "red",
  };

  const filteredResults = sourceFilteredResults.filter((panel) => {
    if (
      searchType !== "gene" ||
      submittedSearch.type !== "gene" ||
      confidenceFilter === "all"
    ) {
      return true;
    }

    const searchedGene = submittedSearch.term.toLowerCase();

    if (!searchedGene) return true;

    return (panel.genes || []).some((gene) => {
      const symbol = String(gene.gene_symbol || "").toLowerCase();

      const confidence = String(gene.confidence_level ?? "")
        .trim()
        .toLowerCase();

      return (
        symbol.includes(searchedGene) &&
        confidenceAliases[confidence] === confidenceFilter
      );
    });
  });


  const panelTableResults = filteredResults.filter(
    (panel) => panel.source !== "GenCC"
  );

  const genccTableResults = filteredResults.filter(
    (panel) => panel.source === "GenCC"
  );

  const activeResults =
    resultView === "gencc" ? genccTableResults : panelTableResults;



  const isOrphanetView = resultView === "orphanet";
  const orphanetTerm =
    hasSearched && ["name", "disease"].includes(submittedSearch.type)
      ? submittedSearch.term
      : "";


  // const groupedSearchResults = groupSearchResults(filteredResults);
  // // const totalListPages = Math.ceil(totalGroups / LIST_PAGE_SIZE);
  // // const visibleListResults = groupedSearchResults;

  // const totalListPages = Math.ceil(
  //   groupedSearchResults.length / LIST_PAGE_SIZE
  // );

  // const visibleListResults = groupedSearchResults.slice(
  //   (listPage - 1) * LIST_PAGE_SIZE,
  //   listPage * LIST_PAGE_SIZE
  // );






  return (
    <div className="container mt-5">

      <div className="text-center mb-4">
        <h1 style={{ color: "#256fa1" }}>PanelBuilder</h1>
        <p className="text-muted">
          Search by panel name, gene, or disease
        </p>
      </div>




      <SearchBar
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        searchType={searchType}
        setSearchType={(value) => {
          setSearchType(value);
          handleConfidenceFilterChange("all");
        }}
        showSourceFilter={resultView !== "gencc"}
        handleSearch={handleSearch}
        sourceFilter={sourceFilter}
        availableSources={availableSources}
        onSourceFilterChange={handleSourceFilterChange}
        confidenceFilter={confidenceFilter}
        onConfidenceFilterChange={handleConfidenceFilterChange}
      />



      <div className="mt-4">
        {hasSearched && (
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h4 className="mb-0">Search Results</h4>
            {!isOrphanetView && (
              <span className="text-muted">
                {activeResults.length} matching panel
                {activeResults.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        )}
        {/* <span className="text-muted">
              {activeResults.length} matching panel
              {activeResults.length !== 1 ? "s" : ""}
            </span>
          </div>
        )} */}


        <ul className="nav nav-tabs mb-3">
          <li className="nav-item">
            <button
              className={`nav-link ${resultView === "genes" ? "active" : ""}`}
              onClick={() => setResultView("genes")}
            >
              Panel Table
            </button>
          </li>

          <li className="nav-item">
            <button
              className={`nav-link ${resultView === "gencc" ? "active" : ""}`}
              onClick={() => {
                setResultView("gencc");
                handleSourceFilterChange("all");
              }}
            >
              GenCC Panel Table
            </button>
          </li>

          <li className="nav-item">
            <button
              type="button"
              className={`nav-link ${isOrphanetView ? "active" : ""}`}
              onClick={() => setResultView("orphanet")}
            >
              Orphanet Epidemiology
            </button>
          </li>



        </ul>












        {isOrphanetView && (
          <OrphanetResults key={orphanetTerm} term={orphanetTerm} />
        )}

        {!isOrphanetView && loading && (
          <p className="text-center">Searching...</p>
        )}

        {!isOrphanetView && !loading && error && (
          <div className="alert alert-danger">{error}</div>
        )}


        {!isOrphanetView && !loading && !error && hasSearched && (


          //   {/* { loading && <p className="text-center">Searching...</p>}

          // {!loading && error && (
          //   <div className="alert alert-danger">{error}</div>
          // )} */}

          // // {!loading && !error && hasSearched && (

          activeResults.length === 0 ? (
            <div className="alert alert-info">
              No results found in this tab.
            </div>
          ) : resultView === "genes" ? (
            <PanelGeneTable
              key="panel-table"
              results={panelTableResults}
              page={genePage}
              onPageChange={setGenePage}
            />
          ) : (
            <PanelGeneTable
              key="gencc-table"
              results={genccTableResults}
              page={genccPage}
              onPageChange={setGenccPage}
            />
          )

        )}
      </div>

    </div>
  );
}

export default HomePage;