// world.js: WHAT is in this film (the demo is LC 787 from examples/mini). A new film replaces this file and
// shots.js; the kit stays. Everything here is data plus kit constructors: no DOM, so tools/build.mjs can read the
// Theatre objects in node and compile the shots against them.
import { Stage } from '../kit/stage.js';
import { Graph } from '../kit/graph.js';
import { Decoder } from '../kit/decoder.js';
import { Table } from '../kit/table.js';
import { Ladder } from '../kit/ladder.js';
import { CodePanel } from '../kit/code.js';
import { QuestionCard } from '../kit/question.js';
import { TitleCard, ChapterCard, ChapterTag } from '../kit/cards.js';
import { Caption } from '../kit/caption.js';
import { Bursts } from '../kit/burst.js';

export const PROJECT_ID = 'Explainer'; // Theatre project id (also the name Studio shows)

// The C++ on screen must be the code you compiled (reflowed to <= ~52 columns so it fits beside the graph at 30 px).
export const CODE = `
int findCheapestPrice(int n,
    vector<vector<int>>& flights,
    int src, int dst, int k) {
  const int INF = 1e9;
  vector<int> dist(n, INF);
  dist[src] = 0;
  for (int round = 0; round <= k; ++round) {
    vector<int> next = dist;  // read old
    for (auto& f : flights) {
      int u = f[0], v = f[1], w = f[2];
      if (dist[u] != INF && dist[u] + w < next[v])
        next[v] = dist[u] + w;
    }
    dist = next;              // write new
  }
  return dist[dst] == INF ? -1 : dist[dst];
}`.trim();

export default function world(T) {
  const stage = new Stage({ backdrop: 'skyline', floor: true });
  // the persistent subject: Example 1's flight map (positions are layer pixels at rest; the camera moves the layer)
  const graph = new Graph({
    // badgeAt: where a node's value badge sits, clear of its edges' weights and of the panels beside the graph
    nodes: [{ id: 0, x: 730, y: 470 }, { id: 1, x: 1100, y: 250 }, { id: 2, x: 1100, y: 700, badgeAt: 'br' }, { id: 3, x: 1490, y: 470, badgeAt: 'above' }],
    edges: [
      { from: 0, to: 1, w: 100, bend: -0.1 }, { from: 1, to: 2, w: 100, bend: -0.16 }, { from: 2, to: 0, w: 100, bend: -0.1 },
      { from: 1, to: 3, w: 600, bend: -0.1 }, { from: 2, to: 3, w: 200, bend: 0.1 },
    ],
    tokens: 3,
  });
  const decoder = new Decoder({
    graph, x: 110, y: 182,
    rows: [
      { text: 'n = 4' },
      { text: 'flights = [' },
      // each price lifts off its row and lands on its arrow as that edge's weight
      { text: '  [0, 1, 100],', chip: '100', to: { edge: '0-1' } },
      { text: '  [1, 2, 100],', chip: '100', to: { edge: '1-2' } },
      { text: '  [2, 0, 100],', chip: '100', to: { edge: '2-0' } },
      { text: '  [1, 3, 600],', chip: '600', to: { edge: '1-3' } },
      { text: '  [2, 3, 200]', chip: '200', to: { edge: '2-3' } },
      { text: ']' },
      { text: 'src = 0', chip: 'src', to: { node: 0 } },
      { text: 'dst = 3', chip: 'dst', to: { node: 3 } },
      { text: 'k = 1' },
    ],
  });
  const rows = new Table({
    id: 'Rows', x: 110, y: 380, title: 'one round', cols: ['0', '1', '2', '3'],
    rows: [
      { label: 'OLD', steps: [[0, '∞', '∞', '∞'], [0, '∞', '∞', '∞']] },
      { label: 'NEW', steps: [[0, '∞', '∞', '∞'], [0, 100, '∞', '∞']] },
    ],
  });
  const table = new Table({
    id: 'Table', x: 110, y: 640, title: 'dry run · dist', cols: ['0', '1', '2', '3'],
    rows: [{ label: 'dist', steps: [[0, '∞', '∞', '∞'], [0, 100, '∞', '∞'], [0, 100, 200, 700]] }],
  });
  const ladder = new Ladder({
    x: 920, y: 170, w: 940,
    rungs: [
      { name: 'Brute-force DFS', time: 'O(n^(k+1))', space: 'O(k)', cost: 1 },
      { name: 'DFS + memo', time: 'O(k·E)', space: 'O(n·k)', cost: 0.45 },
      { name: 'Bellman-Ford, k+1 rounds', time: 'O(k·E)', space: 'O(n)', cost: 0.3 },
    ],
    pick: 2,
  });
  // the desk in chapter 5: graph above the dry-run table on the left, the code on the right (30 px, 17 lines fit)
  const code = new CodePanel({ code: CODE, x: 698, y: 100, fontSize: 30, lineHeight: 1.25 });
  // the question card sits right of the chapter tag (top left) so the two never touch
  const question = new QuestionCard({ T, x: 1120, y: 168, w: 1080 });
  const title = new TitleCard({ title: T.title, subtitle: 'LeetCode 787 · graphs · shortest path with a hop limit', badge: 'LEETCODE 787' });
  const bursts = new Bursts({ slots: 2 });
  const chapter = new ChapterCard({ T });
  const tag = new ChapterTag({ T });
  const caption = new Caption({ T });
  // mount order = paint order inside a layer
  const components = [stage, decoder, rows, table, graph, ladder, code, question, title, tag, bursts, chapter, caption];
  return { stage, graph, decoder, rows, table, ladder, code, question, title, bursts, chapter, tag, caption, components };
}
