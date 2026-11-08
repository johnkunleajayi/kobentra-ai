import { createContext, useContext } from "react";

export const AuthContext = createContext(false);

export function useAuthenticated(): boolean {
  return useContext(AuthContext);
}
