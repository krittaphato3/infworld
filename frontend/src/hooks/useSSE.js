import { useEffect, useRef, useCallback } from 'react';

export function useSSE(url, onEvent, onError) {
  const eventSourceRef = useRef(null);
  const onEventRef = useRef(onEvent);
  const onErrorRef = useRef(onError);

  onEventRef.current = onEvent;
  onErrorRef.current = onError;

  const connect = useCallback((prompt) => {
    const fullUrl = `${url}?prompt=${encodeURIComponent(prompt)}`;
    const es = new EventSource(fullUrl);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onEventRef.current(data);
      } catch (err) {
        onErrorRef.current(err);
      }
    };

    es.onerror = (err) => {
      es.close();
      onErrorRef.current(err);
    };

    return es;
  }, [url]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  return { connect, disconnect };
}
