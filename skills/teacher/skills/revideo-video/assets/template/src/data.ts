// Film data: the facts the scenes draw. Replace this file (and film.tsx) for a new film.
// Everything here must match brief.md's Facts (the code is the exact code that was compiled and run).
import {C} from './kit/theme';
import type {GraphSpec, Rung} from './kit';

export const KICKER = 'LC 787';

// The persistent subject: Example 1's flight map. Positions are in world coordinates (centre = 0, 0).
export const FLIGHTS: [number, number, number][] = [[0, 1, 100], [1, 2, 100], [2, 0, 100], [1, 3, 600], [2, 3, 200]];
export const GRAPH: GraphSpec = {
  nodes: [
    {id: 0, x: -380, y: 10},
    {id: 1, x: 0, y: -200},
    {id: 2, x: 0, y: 220},
    {id: 3, x: 380, y: 10},
  ],
  edges: FLIGHTS.map(([u, v, w]) => ({u, v, w})),
};
export const SRC = 0, DST = 3, K = 1;

// The C++ solution exactly as compiled (brief.md, Facts), wrapped to 58 columns so it fits at 30 px beside the
// dry run: the signature breaks after `flights,` and the long trailing comment sits on its own line (same tokens).
export const CPP = `int findCheapestPrice(int n, vector<vector<int>>& flights,
                      int src, int dst, int k) {
    const int INF = 1e9;
    vector<int> dist(n, INF);
    dist[src] = 0;
    // k stops = k+1 flights
    for (int round = 0; round <= k; ++round) {
        vector<int> next = dist;  // read old, write new
        for (auto& f : flights) {
            int u = f[0], v = f[1], w = f[2];
            if (dist[u] != INF && dist[u] + w < next[v])
                next[v] = dist[u] + w;
        }
        dist = next;
    }
    return dist[dst] == INF ? -1 : dist[dst];
}`;
// line numbers (0-based) the narration points at
export const CODE_LINES = {init: 3, loop: 6, copy: 7, relax: 10, write: 11, swap: 13, ret: 15};

// Dry run of Example 1 (program output): start, after round 0, after round 1.
export const DRY = [
  ['0', '∞', '∞', '∞'],
  ['0', '100', '∞', '∞'],
  ['0', '100', '200', '700'],
];

export const RUNGS: Rung[] = [
  {name: 'Brute-force DFS', time: ['n', 'k+1'], space: 'O(k)', cost: 1.0, color: C.rose},
  {name: 'DFS + memo (city, flights)', time: ['k·E'], space: 'O(n·k)', cost: 0.42},
  {name: 'Bellman-Ford, k + 1 rounds', time: ['k·E'], space: 'O(n)', cost: 0.34},
];
