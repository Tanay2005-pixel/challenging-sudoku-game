#include "sudoku.h"
#include <vector>
using namespace std;
SGraph buildGraph(vector<vector<int>>& b, Cfg& cfg) {
    int n    = cfg.n;
    int bsiz = cfg.bsiz;
    SGraph g = makeGraph(cfg);

    for (int r = 0; r < n; r++) {
        for (int c = 0; c < n; c++) {
            int idx        = r * n + c;
            g.nodes[idx].row   = r;
            g.nodes[idx].col   = c;
            g.nodes[idx].color = b[r][c];
            g.nodes[idx].nbrs.clear();
        }
    }

    for (int r = 0; r < n; r++) {
        for (int c = 0; c < n; c++) {
            int idx = r * n + c;

            vector<bool> added(n * n, false);

            for (int cc = 0; cc < n; cc++) {
                if (cc != c) {
                    int nb = r * n + cc;
                    if (!added[nb]) {
                        g.nodes[idx].nbrs.push_back(nb);
                        added[nb] = true;
                    }
                }
            }

            for (int rr = 0; rr < n; rr++) {
                if (rr != r) {
                    int nb = rr * n + c;
                    if (!added[nb]) {
                        g.nodes[idx].nbrs.push_back(nb);
                        added[nb] = true;
                    }
                }
            }

            int br = (r / bsiz) * bsiz;
            int bc = (c / bsiz) * bsiz;
            for (int rr = br; rr < br + bsiz; rr++) {
                for (int cc = bc; cc < bc + bsiz; cc++) {
                    if (rr != r || cc != c) {
                        int nb = rr * n + cc;
                        if (!added[nb]) {
                            g.nodes[idx].nbrs.push_back(nb);
                            added[nb] = true;
                        }
                    }
                }
            }
        }
    }

    return g;
}

bool isValidColor(vector<vector<int>>& b, Cfg& cfg) {
    int n    = cfg.n;
    int bsiz = cfg.bsiz;

    vector<bool> seen(n + 1, false);

    for (int r = 0; r < n; r++) {
        for (int i = 0; i <= n; i++) seen[i] = false;
        for (int c = 0; c < n; c++) {
            int v = b[r][c];
            if (v == 0) continue;
            if (seen[v]) return false;
            seen[v] = true;
        }
    }

    for (int c = 0; c < n; c++) {
        for (int i = 0; i <= n; i++) seen[i] = false;
        for (int r = 0; r < n; r++) {
            int v = b[r][c];
            if (v == 0) continue;
            if (seen[v]) return false;
            seen[v] = true;
        }
    }

    for (int br = 0; br < n; br += bsiz) {
        for (int bc = 0; bc < n; bc += bsiz) {
            for (int i = 0; i <= n; i++) seen[i] = false;
            for (int r = br; r < br + bsiz; r++) {
                for (int c = bc; c < bc + bsiz; c++) {
                    int v = b[r][c];
                    if (v == 0) continue;
                    if (seen[v]) return false;
                    seen[v] = true;
                }
            }
        }
    }

    return true;
}

void printGraph(SGraph& g) {
    int total = (int)g.nodes.size();
    for (int i = 0; i < total; i++) {
        Cell& nd = g.nodes[i];
        cout << "Node " << i
                  << " (" << nd.row << "," << nd.col << ")"
                  << " color=" << nd.color
                  << " nbrs=" << nd.nbrs.size()
                  << "\n";
    }
}
