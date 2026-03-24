#include "sudoku.h"
#include <vector>
#include <algorithm>
using namespace std;
int findIdx(PGraph& pg, int id) {
    for (int i = 0; i < (int)pg.plist.size(); i++)
        if (pg.plist[i].id == id) return i;
    return -1;
}

void addPlayer(PGraph& pg, Player p) {
    pg.plist.push_back(p);
    pg.adj.push_back(vector<Edge>());
}

void addEdge(PGraph& pg, int id1, int id2) {
    int i1 = findIdx(pg, id1);
    int i2 = findIdx(pg, id2);
    if (i1 == -1 || i2 == -1) return;

    bool found = false;
    for (int i = 0; i < (int)pg.adj[i1].size(); i++) {
        if (pg.adj[i1][i].to == id2) {
            pg.adj[i1][i].wt++;
            found = true;
            break;
        }
    }
    if (!found) {
        Edge e;
        e.to = id2;
        e.wt = 1;
        pg.adj[i1].push_back(e);
    }

    found = false;
    for (int i = 0; i < (int)pg.adj[i2].size(); i++) {
        if (pg.adj[i2][i].to == id1) {
            pg.adj[i2][i].wt++;
            found = true;
            break;
        }
    }
    if (!found) {
        Edge e;
        e.to = id1;
        e.wt = 1;
        pg.adj[i2].push_back(e);
    }
}

vector<Player> recommend(PGraph& pg, int pid, int topN) {
    int si = findIdx(pg, pid);
    if (si == -1) return vector<Player>();

    int total = (int)pg.plist.size();
    vector<bool> skip(total, false);
    skip[si] = true;
    for (int i = 0; i < (int)pg.adj[si].size(); i++) {
        int fi = findIdx(pg, pg.adj[si][i].to);
        if (fi != -1) skip[fi] = true;
    }

    vector<int> score(total, 0);
    for (int i = 0; i < (int)pg.adj[si].size(); i++) {
        int fi = findIdx(pg, pg.adj[si][i].to);
        if (fi == -1) continue;
        for (int j = 0; j < (int)pg.adj[fi].size(); j++) {
            int ci = findIdx(pg, pg.adj[fi][j].to);
            if (ci != -1 && !skip[ci])
                score[ci]++;
        }
    }

    vector<pair<int,int>> ranked;
    for (int i = 0; i < total; i++)
        if (score[i] > 0) ranked.push_back(make_pair(i, score[i]));

    sort(ranked.begin(), ranked.end(),
        [](pair<int,int> a, pair<int,int> b) {
            return a.second > b.second;
        });

    vector<Player> res;
    for (int i = 0; i < (int)ranked.size() && i < topN; i++)
        res.push_back(pg.plist[ranked[i].first]);

    return res;
}

void printPGraph(PGraph& pg) {
    for (int i = 0; i < (int)pg.plist.size(); i++) {
        cout << "Player [" << pg.plist[i].id << "] "
                  << pg.plist[i].name
                  << " wins=" << pg.plist[i].wins
                  << " loss=" << pg.plist[i].loss << "\n  -> ";
        for (int j = 0; j < (int)pg.adj[i].size(); j++)
            cout << pg.adj[i][j].to << "(wt=" << pg.adj[i][j].wt << ") ";
        cout << "\n";
    }
}
