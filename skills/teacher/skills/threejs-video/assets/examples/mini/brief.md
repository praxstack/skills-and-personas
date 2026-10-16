# LC 787: Cheapest Flights Within K Stops

## Topic
LeetCode 787, Cheapest Flights Within K Stops (medium, graphs / shortest path with a hop limit).

## Audience
An experienced engineer refreshing DSA recall before interviews. Knows Dijkstra and BFS by name,
is rusty on details, and often needs the problem statement itself decoded before any approach.

## Format
dsa-5part: 0 intro, 1 Problem (decode every input, the output, each example), 2 Brute force (short),
3 Intuition (questions with a pause to think, each answered on screen), 4 Every approach with time/space and how
the intuition improves each, 5 C++ solution with a dry run of Example 1. Target about 70 seconds (a smoke test of the pipeline, not a lesson). Captions burned in.

## Persistent subject
The Example 1 flight map: 4 city nodes, 5 priced one-way arrows. It stays on screen the whole film, moves to a
corner for the code chapter, and lights up as routes are flown and as the dist/next rows change.

## Style
Dark editorial: background #0B0B0D, ink #F2EDE4, one accent (signal orange #FF5B2E) for the thing being looked
at, mint #7BE3B5 for valid/answer, rose #FF4F6E for illegal/wrong. Inter Display for titles, Inter for captions,
JetBrains Mono (ligatures off) for code and numbers. Eased motion only (cubic/expo out), no linear slides.

## Facts
Verified: the C++ below was compiled with g++ -std=c++17 and run on every example.
- Example 1: n=4, flights=[[0,1,100],[1,2,100],[2,0,100],[1,3,600],[2,3,200]], src=0, dst=3, k=1 -> 700.
  0->1->3 costs 700 with 1 stop (allowed). 0->1->2->3 costs 400 with 2 stops (not allowed). k=2 -> 400, k=0 -> -1.
- Example 2: n=3, flights=[[0,1,100],[1,2,100],[0,2,500]], src=0, dst=2, k=1 -> 200.
- Example 3: Example 2 with k=0 -> 500.
- Bellman-Ford dry run on Example 1 (INF = unreachable):
  start [0, INF, INF, INF]; round 0 [0, 100, INF, INF]; round 1 [0, 100, 200, 700] (2->3 skipped: old dist[2] is INF).
  In-place (wrong) round 0 gives [0, 100, 200, 400].
- Complexities: brute DFS O(n^(k+1)) time, O(k) space; DFS + memo O(k*E), O(n*k); BFS by levels O(k*E), O(n+E);
  Dijkstra with stops in the state O(E*k*log(E*k)), O(n*k); Bellman-Ford k+1 rounds O(k*E), O(n) (the interview pick).
  Plain Dijkstra fails: it settles city 3 at 400 using 3 flights when k = 1.

```cpp
int findCheapestPrice(int n, vector<vector<int>>& flights, int src, int dst, int k) {
    const int INF = 1e9;
    vector<int> dist(n, INF);
    dist[src] = 0;
    for (int round = 0; round <= k; ++round) {      // k stops = k+1 flights
        vector<int> next = dist;                    // read old, write new
        for (auto& f : flights) {
            int u = f[0], v = f[1], w = f[2];
            if (dist[u] != INF && dist[u] + w < next[v])
                next[v] = dist[u] + w;
        }
        dist = next;
    }
    return dist[dst] == INF ? -1 : dist[dst];
}
```

## Output
1920x1080, 30 fps, H.264 + AAC, natural voice baked in (Kokoro af_heart), soft synthesized music ducked under
the voice, captions burned in plus captions.srt. Deliver to deliver/ in the project (or the folder the person names).
