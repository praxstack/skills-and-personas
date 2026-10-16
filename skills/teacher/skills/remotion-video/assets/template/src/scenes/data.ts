// The film's facts as data: the subject's layout, the raw input text, the code. Replace these for a new film.
// Pure data with no imports from React, so node scripts can import it too (Node 22 strips TS types).
import type {GraphData, Place} from '../kit/Graph';
import type {InputSpec} from '../kit/InputDecoder';

// Example 1: n = 4, flights = [[0,1,100],[1,2,100],[2,0,100],[1,3,600],[2,3,200]], src 0, dst 3, k 1 -> 700
export const MAP: GraphData = {
  W: 1000, H: 600, R: 52,
  nodes: [
    {id: '0', x: 110, y: 300},
    {id: '1', x: 500, y: 92, valueSide: 'top', badgeSide: 'top'},
    {id: '2', x: 500, y: 508, badgeSide: 'bottom'},
    {id: '3', x: 890, y: 300},
  ],
  edges: [
    {id: 'e01', from: '0', to: '1', w: 100, bend: -42},
    {id: 'e12', from: '1', to: '2', w: 100, bend: -64},
    {id: 'e20', from: '2', to: '0', w: 100, bend: -42},
    {id: 'e13', from: '1', to: '3', w: 600, bend: -42},
    {id: 'e23', from: '2', to: '3', w: 200, bend: 42},
  ],
};
/** which input entry becomes which edge (decode recipe) */
export const ENTRY_EDGE: Record<string, string> = {f0: 'e01', f1: 'e12', f2: 'e20', f3: 'e13', f4: 'e23'};

// Where the graph sits in the world in each part of the film (x, y = centre; s = scale; o = opacity)
export const PLACE: Record<string, Place> = {
  hidden: {x: 1250, y: 520, s: 0.9, o: 0},
  decode: {x: 1260, y: 515, s: 0.95, o: 1},
  center: {x: 960, y: 505, s: 1.08, o: 1},
  left: {x: 580, y: 520, s: 0.78, o: 1},
  question: {x: 960, y: 655, s: 0.7, o: 1},
  question2: {x: 520, y: 665, s: 0.62, o: 1},
  ladder: {x: 1505, y: 560, s: 0.58, o: 1},
  code: {x: 1562, y: 342, s: 0.5, o: 1}, // right column above the dry-run table; tags stay 30 px (Graph minPx)
  outro: {x: 640, y: 500, s: 0.86, o: 1},
};

export const INPUT: InputSpec = {
  title: 'input · example 1',
  fs: 36,
  lines: [
    'n = {{n|4}}',
    'flights = [{{f0|[0,1,100]}},',
    '           {{f1|[1,2,100]}},',
    '           {{f2|[2,0,100]}},',
    '           {{f3|[1,3,600]}},',
    '           {{f4|[2,3,200]}}]',
    'src = {{src|0}}',
    'dst = {{dst|3}}',
    'k = {{k|1}}',
  ],
};

// The exact solution that was compiled and run in the brief (comments moved onto their own lines to fit).
export const CPP = `int findCheapestPrice(int n, vector<vector<int>>& flights,
                      int src, int dst, int k) {
    const int INF = 1e9;
    vector<int> dist(n, INF);
    dist[src] = 0;
    // k stops = k+1 flights
    for (int round = 0; round <= k; ++round) {
        // read old, write new
        vector<int> next = dist;
        for (auto& f : flights) {
            int u = f[0], v = f[1], w = f[2];
            if (dist[u] != INF && dist[u] + w < next[v])
                next[v] = dist[u] + w;
        }
        dist = next;
    }
    return dist[dst] == INF ? -1 : dist[dst];
}`;
/** 0-based line numbers in CPP the narration points at */
export const CODE_LINE = {init: [3, 4], round: [6, 6], copy: [8, 8], relax: [11, 12], swap: [14, 14], ret: [16, 16]} as const;
