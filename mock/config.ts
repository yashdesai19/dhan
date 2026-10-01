// Dev controls for the mock repositories (spec §13). No network is ever used.
export const mockConfig: {
  /** Simulated latency range in ms. */
  latency: [number, number];
  /** Make the next repository call reject (exercise error states). */
  failNext: boolean;
  /** Pretend the device is offline: reads from reports fail. */
  offline: boolean;
} = {
  latency: [300, 600],
  failNext: false,
  offline: false,
};
