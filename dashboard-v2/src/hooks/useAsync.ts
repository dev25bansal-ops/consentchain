// Custom hook for data fetching with loading and error states

import { useState, useEffect, useCallback, useRef } from "react";
import type { AsyncState } from "../types";

interface UseAsyncOptions<T> {
  immediate?: boolean;
  initialData?: T | null;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

interface UseAsyncResult<T, P extends unknown[]> extends AsyncState<T> {
  execute: (...params: P) => Promise<T | null>;
  reset: () => void;
}

export function useAsync<T, P extends unknown[] = []>(
  asyncFunction: (...params: P) => Promise<T>,
  options: UseAsyncOptions<T> = {},
): UseAsyncResult<T, P> {
  const { immediate = false, initialData = null, onSuccess, onError } = options;

  const [state, setState] = useState<AsyncState<T>>({
    data: initialData,
    isLoading: immediate,
    error: null,
  });

  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const execute = useCallback(
    async (...params: P): Promise<T | null> => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        const result = await asyncFunction(...params);

        if (isMountedRef.current) {
          setState({ data: result, isLoading: false, error: null });
          onSuccess?.(result);
        }

        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));

        if (isMountedRef.current) {
          setState((prev) => ({
            ...prev,
            isLoading: false,
            error: { hasError: true, message: error.message },
          }));
          onError?.(error);
        }

        return null;
      }
    },
    [asyncFunction, onSuccess, onError],
  );

  const reset = useCallback(() => {
    setState({ data: initialData, isLoading: false, error: null });
  }, [initialData]);

  return { ...state, execute, reset };
}

// Hook for debounced values
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Hook for local storage with SSR safety
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === "undefined") return initialValue;

    try {
      const item = window.localStorage.getItem(key);
      return item ? (JSON.parse(item) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      const valueToStore =
        value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);

      if (typeof window !== "undefined") {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    },
    [key, storedValue],
  );

  return [storedValue, setValue];
}

// Hook for media queries
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined") return;

    const mediaQuery = window.matchMedia(query);
    const handler = (event: MediaQueryListEvent) => setMatches(event.matches);

    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, [query]);

  return matches;
}

// Responsive breakpoint hooks
export function useIsMobile(): boolean {
  return useMediaQuery("(max-width: 639px)");
}

export function useIsTablet(): boolean {
  return useMediaQuery("(min-width: 640px) and (max-width: 1023px)");
}

export function useIsDesktop(): boolean {
  return useMediaQuery("(min-width: 1024px)");
}

// Hook for click outside detection
export function useClickOutside(
  ref: React.RefObject<HTMLElement>,
  handler: () => void,
): void {
  useEffect(() => {
    const listener = (event: MouseEvent | TouchEvent) => {
      if (!ref.current || ref.current.contains(event.target as Node)) {
        return;
      }
      handler();
    };

    document.addEventListener("mousedown", listener);
    document.addEventListener("touchstart", listener);

    return () => {
      document.removeEventListener("mousedown", listener);
      document.removeEventListener("touchstart", listener);
    };
  }, [ref, handler]);
}

// Hook for previous value
export function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T>();

  useEffect(() => {
    ref.current = value;
  }, [value]);

  return ref.current;
}

// Hook for interval
export function useInterval(callback: () => void, delay: number | null): void {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delay === null) return;

    const id = setInterval(() => savedCallback.current(), delay);
    return () => clearInterval(id);
  }, [delay]);
}

// Hook for document title
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = `${title} | ConsentChain`;

    return () => {
      document.title = previousTitle;
    };
  }, [title]);
}
