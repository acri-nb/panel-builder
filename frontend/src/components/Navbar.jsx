import { Link } from "react-router-dom";

function Navbar() {
  return (
    //  #25ADD7 #4B83B4 #1E646B #256fa1 #3E6C95
     <nav
       className="navbar navbar-expand-lg navbar-dark"
      style={{ backgroundColor: "#256fa1" }}
     >
      <div className="container">

        <Link className="navbar-brand" to="/">
          PanelBuilder
        </Link>

        <div className="navbar-nav">
          <Link className="nav-link" to="/">
            Panels
          </Link>

          <Link className="nav-link" to="/lab-panels">
            Laboratory Panels
          </Link>

          <Link className="nav-link" to="/external-updates">
            Pending Updates
          </Link>
        </div>

      </div>
    </nav>
  );
}

export default Navbar;

