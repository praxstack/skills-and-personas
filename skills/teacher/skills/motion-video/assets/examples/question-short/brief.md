# LC 787 question Short (9:16)

## Topic
LeetCode 787, Cheapest Flights Within K Stops, Example 1 asked as a single multiple-choice question, then
answered, then the one idea behind the answer (k stops = k + 1 flights, so k + 1 Bellman-Ford rounds).

## Audience
Someone scrolling Shorts who knows what a graph is. They get three seconds of countdown to answer first.

## Format
general, 9:16 (1080x1920), about 50 s. Chapters: Question, Think, Answer, Why. Captions burned in, karaoke.
Everything sits above the bottom 430 px and left of the right 120 px (the platform draws its buttons there).

## Persistent subject
The Example 1 flight map: 4 cities, 5 priced one-way flights. It is on screen from the second shot to the end
of the answer, holds its place while the question appears under it, and flies the wrong route (red, 2 stops)
and the right one (green, 1 stop).

## Style
motion-video "ink" look (dark): one accent for what is being looked at, green for the answer, red for the trap.
Fraunces for headlines, Inter for everything else, JetBrains Mono for the price row. Brand "Kai Mori", tag
"LC 787 · daily".

## Facts
Verified: the C++ below was compiled with g++ -std=c++17 and run.
- n=4, flights=[[0,1,100],[1,2,100],[2,0,100],[1,3,600],[2,3,200]], src=0, dst=3, k=1 -> 700 (0->1->3).
- 0->1->2->3 costs 400 but has 2 stops (cities 1 and 2): not allowed when k=1. With k=2 the answer is 400.
- Bellman-Ford with k+1 rounds, each reading last round's prices:
  round 1: [0, 100, inf, inf]; round 2: [0, 100, 200, 700]. O(k*E) time, O(n) space.

```cpp
int findCheapestPrice(int n, vector<vector<int>>& flights, int src, int dst, int k) {
    const int INF = INT_MAX;
    vector<int> dist(n, INF);
    dist[src] = 0;
    for (int round = 1; round <= k + 1; round++) {
        vector<int> prev = dist;                       // read last round, write this one
        for (auto& f : flights)
            if (prev[f[0]] != INF && prev[f[0]] + f[2] < dist[f[1]]) dist[f[1]] = prev[f[0]] + f[2];
    }
    return dist[dst] == INF ? -1 : dist[dst];
}
```

Program output: `k=1 -> 700` (rounds `0 100 inf inf`, `0 100 200 700`); `k=2 -> 400`.

## Output
1080x1920 at 30 fps, H.264 + AAC, -16 LUFS. Deliver to explainers/motion/.
