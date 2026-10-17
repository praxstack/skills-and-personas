// Film data for the demo (LC 787, Example 1). A new film replaces this file and the chapter files.
import type {GraphEdgeSpec, GraphNodeSpec, InputRow, Rung} from '../kit';

export const SHOW = 'LEETCODE 787  ·  CHEAPEST FLIGHTS WITHIN K STOPS';

// The persistent subject: Example 1's flight map (world coordinates; the graph sits at the world origin).
export const NODES: GraphNodeSpec[] = [
  {id: 0, x: -330, y: 0, valueSide: 'bottom'},
  {id: 1, x: 0, y: -160, valueSide: 'top'},
  {id: 2, x: 0, y: 160, valueSide: 'bottom'},
  {id: 3, x: 330, y: 0, valueSide: 'right'},
];
export const EDGES: GraphEdgeSpec[] = [
  {from: 0, to: 1, w: 100},
  {from: 1, to: 2, w: 100, pillSide: 1},
  {from: 2, to: 0, w: 100},
  {from: 1, to: 3, w: 600},
  {from: 2, to: 3, w: 200},
];

export const INPUT: InputRow[] = [
  {name: 'flights', list: true, parts: ['[0,1,100]', '[1,2,100]', '[2,0,100]', '[1,3,600]', '[2,3,200]']},
  {assign: [['n', '4'], ['src', '0'], ['dst', '3'], ['k', '1']]},
];

export const RUNGS: Rung[] = [
  {name: 'Brute-force DFS', note: 'every route, up to k + 1 flights', time: 'O(n^(k+1))', space: 'O(k)', cost: 1.0},
  {name: 'DFS + memo', note: 'state (city, flights used) once', time: 'O(k·E)', space: 'O(n·k)', cost: 0.42},
  {name: 'Bellman-Ford, k + 1 rounds', note: 'row i + 1 from row i: read old, write new', time: 'O(k·E)', space: 'O(n)', cost: 0.4},
];

// Exactly the code that was compiled for the brief (the signature is wrapped so that no line is longer than
// 56 characters: at 30 px that is 1008 px, the width of the panel's text area).
export const CPP = `int findCheapestPrice(int n,
        vector<vector<int>>& flights,
        int src, int dst, int k) {
    const int INF = 1e9;
    vector<int> dist(n, INF);
    dist[src] = 0;
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
// line numbers (0-based) the dry run points at
export const CODE = {init: [3, 5] as [number, number], loop: 6, copy: 7, relax: [8, 12] as [number, number], commit: 13, ret: 15};
