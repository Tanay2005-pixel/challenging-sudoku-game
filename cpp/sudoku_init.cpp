#include "sudoku.h"
#include <cmath>
#include <vector>
using namespace std;

Cfg makeCfg(int size) {
    Cfg c;
    c.n    = size;
    c.bsiz = (int)sqrt(size);
    if (c.bsiz * c.bsiz != c.n) {
        cout << "Error: size must be 4, 9, 16 ...\n";
        exit(1);
    }
    return c;
}

SGraph makeGraph(Cfg cfg) {
    SGraph g;
    g.cfg = cfg;
    g.nodes.resize(cfg.n * cfg.n);
    return g;
}

vector<int> getValid(vector<vector<int>>& b, Cfg& cfg, int row, int col) {
    int n    = cfg.n;
    int bsiz = cfg.bsiz;
    vector<bool> used(n + 1, false);
    for (int c = 0; c < n; c++)
        if (b[row][c]) used[b[row][c]] = true;
    for (int r = 0; r < n; r++)
        if (b[r][col]) used[b[r][col]] = true;
    int br = (row / bsiz) * bsiz;
    int bc = (col / bsiz) * bsiz;
    for (int r = br; r < br + bsiz; r++)
        for (int c = bc; c < bc + bsiz; c++)
            if (b[r][c]) used[b[r][c]] = true;
    vector<int> vals;
    for (int v = 1; v <= n; v++)
        if (!used[v]) vals.push_back(v);
    return vals;
}

pair<int, int> pickCell(vector<vector<int>>& b, Cfg& cfg) {
    int n    = cfg.n;
    int best = n + 1;
    int br   = -1;
    int bc   = -1;
    for (int r = 0; r < n; r++) {
        for (int c = 0; c < n; c++) {
            if (b[r][c] != 0) continue;
            int cnt = (int)getValid(b, cfg, r, c).size();
            if (cnt < best) {
                best = cnt;
                br   = r;
                bc   = c;
                if (best == 0) return {br, bc};
            }
        }
    }
    return {br, bc};
}
