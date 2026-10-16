/* scenes/subject.js: THIS film's data: the persistent subject, the camera shots, the input text and the code.
   A new film replaces this file and scenes/film.js; the kit stays as it is.

   World coordinates: the world layer is 1920x1080; a shot puts world point (cx, cy) at screen point (sx, sy).
   Keep text 96 px from the frame edges and out of the caption band (y > 900) in every shot (check the stills). */
window.FILM = {
  brand: { tag: 'LC 787', title: 'Cheapest Flights Within K Stops' },

  // Example 1: 4 cities, 5 priced one-way flights. Positions are in world pixels.
  graph: {
    r: 50,
    nodes: [
      { id: 0, x: 560, y: 560 },
      { id: 1, x: 960, y: 330 },
      { id: 2, x: 960, y: 790 },
      { id: 3, x: 1360, y: 560 },
    ],
    edges: [
      { from: 0, to: 1, w: 100 },
      { from: 1, to: 2, w: 100 },
      { from: 2, to: 0, w: 100 },
      { from: 1, to: 3, w: 600 },
      { from: 2, to: 3, w: 200 },
    ],
  },

  // Camera shots (tilt in degrees: the world is a tabletop seen from slightly above).
  shots: {
    title: { cx: 960, cy: 560, zoom: 0.8, sx: 960, sy: 640, tilt: 16 },
    inputs: { cx: 960, cy: 560, zoom: 0.8, sx: 960, sy: 664, tilt: 10 },
    ex1: { cx: 960, cy: 560, zoom: 0.86, sx: 880, sy: 636, tilt: 9 },   // node 1 clears the input panel
    ex1close: { cx: 960, cy: 545, zoom: 1.0, sx: 860, sy: 590, tilt: 7 },
    brute: { cx: 960, cy: 560, zoom: 0.68, sx: 480, sy: 590, tilt: 12 },
    q1: { cx: 960, cy: 560, zoom: 0.8, sx: 960, sy: 650, tilt: 9 },
    q2: { cx: 960, cy: 560, zoom: 0.68, sx: 560, sy: 650, tilt: 9 },
    ladder: { cx: 960, cy: 560, zoom: 0.56, sx: 392, sy: 580, tilt: 12 }, // big enough that the 32 px weight chips do not crowd
    code: { cx: 960, cy: 560, zoom: 0.55, sx: 1541, sy: 362, tilt: 6 },   // top of the column right of the code
    outro: { cx: 960, cy: 560, zoom: 0.8, sx: 960, sy: 640, tilt: 12 },
  },

  // The raw input as the problem states it (decoded on screen, entry by entry).
  input: [
    'n = 4    src = 0    dst = 3    k = 1',
    'flights = [[0,1,100],[1,2,100],[2,0,100],[1,3,600],[2,3,200]]',
  ],

  // Exactly the code compiled in the brief (only the spacing before trailing comments is tightened to fit; at 30 px
  // the panel soft-wraps line 6's comment onto an unnumbered continuation row, see film.js).
  code: `int findCheapestPrice(int n, vector<vector<int>>& flights,
                      int src, int dst, int k) {
    const int INF = 1e9;
    vector<int> dist(n, INF);
    dist[src] = 0;
    for (int round = 0; round <= k; ++round) { // k stops = k+1 flights
        vector<int> next = dist; // read old, write new
        for (auto& f : flights) {
            int u = f[0], v = f[1], w = f[2];
            if (dist[u] != INF && dist[u] + w < next[v])
                next[v] = dist[u] + w;
        }
        dist = next;
    }
    return dist[dst] == INF ? -1 : dist[dst];
}`,
};
