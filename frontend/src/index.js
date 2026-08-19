import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
// Bootstrap loads BEFORE our own stylesheet, so index.css's rules win the
// cascade naturally (later wins at equal specificity) - previously this was
// backwards, which is why nearly every rule in index.css needed !important
// just to apply at all. That !important was blunt enough to also override
// Bootstrap's own .btn-danger/.btn-info/etc. variants (all forced to the
// same primary blue) - fixed alongside this reordering, see index.css.
import "bootstrap/dist/css/bootstrap.min.css";
import "./index.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
