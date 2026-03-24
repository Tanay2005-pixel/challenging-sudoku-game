#include "sudoku.h"
#include <algorithm>
#include <random>
#include <numeric>
#include <functional>

using namespace std;
bool fill( vector<vector<int>>& b, Cfg& cfg, mt19937& rng) {
    pair<int,int> cell = pickCell(b, cfg);
    int row = cell.first;
    int col = cell.second;
    if (row == -1) return true;

    vector<int> vals = getValid(b, cfg, row, col);
    if (vals.empty()) return false;

    shuffle(vals.begin(), vals.end(), rng);

    for (int i = 0; i < (int)vals.size(); i++) {
        b[row][col] = vals[i];
        if (fill(b, cfg, rng)) return true;
        b[row][col] = 0;
    }
    return false;
}

bool oneOnly(vector<vector<int>> b, Cfg& cfg) {
    int cnt = 0;

    function<void()> go = [&]() {
        if (cnt > 1) return;
        pair<int,int> cell = pickCell(b, cfg);
        int row = cell.first;
        int col = cell.second;
        if (row == -1) { cnt++; return; }

        vector<int> vals = getValid(b, cfg, row, col);
        for (int i = 0; i < (int)vals.size(); i++) {
            b[row][col] = vals[i];
            go();
            b[row][col] = 0;
            if (cnt > 1) return;
        }
    };
    go();
    return cnt == 1;
}

vector<vector<int>> genPuzzle(Cfg& cfg, int dif) {
    int n = cfg.n;
    vector<vector<int>> b(n, vector<int>(n, 0));

    mt19937 rng(random_device{}());
    fill(b, cfg, rng);

    int total  = n * n;
    int remove = 0;
    if (dif == EASY)   remove = total * 33 / 100;
    if (dif == MEDIUM) remove = total * 50 / 100;
    if (dif == HARD)   remove = total * 61 / 100;

    vector<int> pos(total);
    iota(pos.begin(), pos.end(), 0);
    shuffle(pos.begin(), pos.end(), rng);

    int done = 0;
    for (int i = 0; i < (int)pos.size(); i++) {
        if (done >= remove) break;
        int r   = pos[i] / n;
        int c   = pos[i] % n;
        int bak = b[r][c];
        b[r][c] = 0;
        if (oneOnly(b, cfg)) {
            done++;
        } else {
            b[r][c] = bak;
        }
    }

    return b;
}
