#include "sudoku.h"
#include <iostream>
#include <iomanip>
#include <vector>
using namespace std;
SGraph buildGraph(vector<vector<int>>& b, Cfg& cfg);
bool   isValidColor(vector<vector<int>>& b, Cfg& cfg);
void   printGraph(SGraph& g);

vector<vector<int>> genPuzzle(Cfg& cfg, int dif);
bool  solve(vector<vector<int>>& b, Cfg& cfg);
bool  isDone(vector<vector<int>>& b, Cfg& cfg);
int   getHint(vector<vector<int>>& b, Cfg& cfg, int row, int col);

void addPlayer(PGraph& pg, Player p);
void addEdge(PGraph& pg, int id1, int id2);
vector<Player> recommend(PGraph& pg, int pid, int topN);
void printPGraph(PGraph& pg);

void printBoard(vector<vector<int>>& b, Cfg& cfg) {
    int n    = cfg.n;
    int bsiz = cfg.bsiz;
    int w    = (n >= 10) ? 3 : 2;

    for (int r = 0; r < n; r++) {
        if (r % bsiz == 0) {
            for (int i = 0; i < n * w + bsiz + 1; i++) cout << "-";
            cout << "\n";
        }
        for (int c = 0; c < n; c++) {
            if (c % bsiz == 0) cout << "|";
            int v = b[r][c];
            if (v == 0) cout << setw(w) << ".";
            else        cout << setw(w) << v;
        }
        cout << "|\n";
    }
    for (int i = 0; i < n * w + bsiz + 1; i++) cout << "-";
    cout << "\n";
}

void showMenu() {
    cout << "\n============================= \n";
    cout << "       SUDOKU MENU\n";
    cout << "============================= \n";
    cout << " 1. Generate Puzzle\n";
    cout << " 2. Solve Current Puzzle\n";
    cout << " 3. Get Hint\n";
    cout << " 4. Validate Board\n";
    cout << " 5. Show Graph Info\n";
    cout << " 6. Player Recommendations\n";
    cout << " 0. Exit\n";
    cout << "============================= \n";
    cout << "Enter choice: ";
}

int askSize() {
    int sz;
    cout << "Enter board size (4, 9, 16): ";
    cin >> sz;
    return sz;
}

int askDifficulty() {
    int dif;
    cout << "Choose difficulty:\n";
    cout << " 1. Easy\n";
    cout << " 2. Medium\n";
    cout << " 3. Hard\n";
    cout << "Enter choice: ";
    cin >> dif;
    if (dif == 1) return EASY;
    if (dif == 2) return MEDIUM;
    if (dif == 3) return HARD;
    cout << "Invalid choice, using Easy.\n";
    return EASY;
}

int main() {
    cout << "Welcome to Sudoku!\n";

    int choice;
    bool hasPuzzle = false;

    vector<vector<int>> puzzle;
    vector<vector<int>> solved;
    Cfg cfg = makeCfg(9);

    PGraph pg;
    Player p1; p1.id = 1; p1.name = "Alice";   p1.wins = 10; p1.loss = 2; p1.online = true;
    Player p2; p2.id = 2; p2.name = "Bob";     p2.wins = 7;  p2.loss = 5; p2.online = true;
    Player p3; p3.id = 3; p3.name = "Charlie"; p3.wins = 3;  p3.loss = 8; p3.online = false;
    Player p4; p4.id = 4; p4.name = "Diana";   p4.wins = 9;  p4.loss = 1; p4.online = true;
    Player p5; p5.id = 5; p5.name = "Eve";     p5.wins = 4;  p5.loss = 6; p5.online = true;
    addPlayer(pg, p1);
    addPlayer(pg, p2);
    addPlayer(pg, p3);
    addPlayer(pg, p4);
    addPlayer(pg, p5);
    addEdge(pg, 1, 2);
    addEdge(pg, 1, 3);
    addEdge(pg, 2, 4);
    addEdge(pg, 2, 5);
    addEdge(pg, 3, 4);

    while (true) {
        showMenu();
        cin >> choice;

        if (choice == 0) {
            cout << "Goodbye!\n";
            break;
        }

        else if (choice == 1) {
            int sz  = askSize();
            cfg     = makeCfg(sz);
            int dif = askDifficulty();
            cout << "\nGenerating puzzle...\n";
            puzzle    = genPuzzle(cfg, dif);
            hasPuzzle = true;
            cout << "\nYour Puzzle:\n";
            printBoard(puzzle, cfg);
        }

        else if (choice == 2) {
            if (!hasPuzzle) {
                cout << "No puzzle yet. Please generate one first (option 1).\n";
            } else {
                solved = puzzle;
                cout << "\nSolving...\n";
                if (solve(solved, cfg)) {
                    cout << "Solved!\n";
                    printBoard(solved, cfg);
                } else {
                    cout << "This puzzle has no solution.\n";
                }
            }
        }

        else if (choice == 3) {
            if (!hasPuzzle) {
                cout << "No puzzle yet. Please generate one first (option 1).\n";
            } else {
                int row, col;
                cout << "Enter row (0 to " << cfg.n - 1 << "): ";
                cin >> row;
                cout << "Enter col (0 to " << cfg.n - 1 << "): ";
                cin >> col;

                if (row < 0 || row >= cfg.n || col < 0 || col >= cfg.n) {
                    cout << "Invalid row or col.\n";
                } else if (puzzle[row][col] != 0) {
                    cout << "That cell is already filled with " << puzzle[row][col] << ".\n";
                } else {
                    int h = getHint(puzzle, cfg, row, col);
                    if (h == -1)
                        cout << "No hint available.\n";
                    else
                        cout << "Hint: cell (" << row << ", " << col << ") = " << h << "\n";
                }
            }
        }

        else if (choice == 4) {
            if (!hasPuzzle) {
                cout << "No puzzle yet. Please generate one first (option 1).\n";
            } else {
                cout << "\nCurrent puzzle:\n";
                printBoard(puzzle, cfg);
                if (isValidColor(puzzle, cfg))
                    cout << "Board is VALID (no conflicts).\n";
                else
                    cout << "Board is INVALID (conflicts found).\n";
                if (isDone(puzzle, cfg))
                    cout << "Board is COMPLETE (all cells filled).\n";
                else
                    cout << "Board is INCOMPLETE (empty cells remain).\n";
            }
        }

        else if (choice == 5) {
            if (!hasPuzzle) {
                cout << "No puzzle yet. Please generate one first (option 1).\n";
            } else {
                SGraph sg = buildGraph(puzzle, cfg);
                cout << "\nGraph Info:\n";
                cout << "Total nodes : " << sg.nodes.size() << "\n";
                cout << "Node 0 nbrs : " << sg.nodes[0].nbrs.size() << "\n";
                cout << "\nShow all nodes? (1 = yes, 0 = no): ";
                int show;
                cin >> show;
                if (show == 1) printGraph(sg);
            }
        }

        else if (choice == 6) {
            cout << "\nPlayers in the system:\n";
            printPGraph(pg);
            int pid, topN;
            cout << "\nEnter player ID to get recommendations for: ";
            cin >> pid;
            cout << "How many recommendations? ";
            cin >> topN;
            vector<Player> recs = recommend(pg, pid, topN);
            if (recs.empty()) {
                cout << "No recommendations found.\n";
            } else {
                cout << "Recommended players:\n";
                for (int i = 0; i < (int)recs.size(); i++)
                    cout << "  -> " << recs[i].name << " (wins = " << recs[i].wins << ")\n";
            }
        } else {
            cout << "Invalid choice. Please enter 0 to 6.\n";
        }
    }

    return 0;
}
