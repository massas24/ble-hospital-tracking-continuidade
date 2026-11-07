import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
// O Bootstrap é carregado antes do index.css para que as regras próprias
// prevaleçam sem recorrer a !important.
import "bootstrap/dist/css/bootstrap.min.css";
import "./index.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
