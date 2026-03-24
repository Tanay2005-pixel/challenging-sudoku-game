#include "sudoku.h"
#include <vector>
using namespace std;
bool solve(vector<vector<int>>& b, Cfg& cfg) {
    pair<int,int> cell = pickCell(b, cfg);
    int row = cell.first;
    int col = cell.second;
    if (row == -1) return true;

    vector<int> vals = getValid(b, cfg, row, col);
    if (vals.empty()) return false;

    for (int i = 0; i < (int)vals.size(); i++) {
        b[row][col] = vals[i];
        if (solve(b, cfg)) return true;
        b[row][col] = 0;
    }
    return false;
}

bool isDone(vector<vector<int>>& b, Cfg& cfg) {
    int n = cfg.n;
    for (int r = 0; r < n; r++)
        for (int c = 0; c < n; c++)
            if (b[r][c] == 0) return false;
    return true;
}

int getHint(vector<vector<int>>& b, Cfg& cfg, int row, int col) {
    if (b[row][col] != 0) return -1;
    vector<vector<int>> copy = b;
    if (solve(copy, cfg)) return copy[row][col];
    return -1;
}
