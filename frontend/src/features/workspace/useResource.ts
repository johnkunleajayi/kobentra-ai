import { useEffect, useState } from "react";
import { workspaceRequest } from "./api";

export function useResource<T>(path: string) {
  const [state, setState] = useState<{
    path: string;
    data?: T;
    error?: string;
  }>({ path });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    workspaceRequest<T>(path)
      .then((data) => {
        if (active) setState({ path, data });
      })
      .catch((error) => {
        if (active)
          setState({
            path,
            error: error instanceof Error ? error.message : "Unable to load.",
          });
      });
    return () => {
      active = false;
    };
  }, [path, attempt]);
  const current = state.path === path ? state : { path };
  return {
    ...current,
    retry: () => {
      setState({ path });
      setAttempt((n) => n + 1);
    },
  };
}
