#ifndef SUDOKU_H
#define SUDOKU_H

#include <vector>
#include <string>
#include <iostream>

using namespace std;
#define EASY   1
#define MEDIUM 2
#define HARD   3

struct Cfg {
    int n;
    int bsiz;
};

Cfg makeCfg(int size);

struct Cell {
    int row;
    int col;
    int color;
    vector<int> nbrs;
};

struct SGraph {
    vector<Cell> nodes;
    Cfg cfg;
};

SGraph makeGraph(Cfg cfg);

struct Player {
    int         id;
    string name;
    int         wins;
    int         loss;
    bool        online;
};

struct Edge {
    int to;
    int wt;
};

struct PGraph {
    vector<Player>            plist;
    vector<vector<Edge>> adj;
};

#endif
vector<int>   getValid(vector<vector<int>>& b, Cfg& cfg, int row, int col);
pair<int,int> pickCell(vector<vector<int>>& b, Cfg& cfg);
