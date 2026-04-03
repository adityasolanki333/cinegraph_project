export function useWebSocket() {
  return {
    isConnected: false,
    reconnect: () => {},
  };
}
