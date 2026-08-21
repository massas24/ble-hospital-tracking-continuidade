
import { Navigate } from "react-router-dom";

export default function RequireAuth({ children }) {
  const username = localStorage.getItem("username");
  if (!username) {
    
    return <Navigate to="/login" replace />;
  }
  
  return children;
}
