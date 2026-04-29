#include "sudoku.h"
#include <iostream>
#include <iomanip>
#include <vector>
#include <string>
#include <sstream>
#include <cstring>

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



void outputBoard(const vector<vector<int>>& board) {
    cout << "[";
    for (size_t i = 0; i < board.size(); i++) {
        if (i > 0) cout << ",";
        cout << "[";
        for (size_t j = 0; j < board[i].size(); j++) {
            if (j > 0) cout << ",";
            cout << board[i][j];
        }
        cout << "]";
    }
    cout << "]";
}

void output1DBoard(const vector<int>& board) {
    cout << "[";
    for (size_t i = 0; i < board.size(); i++) {
        if (i > 0) cout << ",";
        cout << board[i];
    }
    cout << "]";
}

vector<vector<int>> flat1DTo2D(const vector<int>& flat, int size) {
    vector<vector<int>> board(size, vector<int>(size));
    for (int i = 0; i < size; i++) {
        for (int j = 0; j < size; j++) {
            board[i][j] = flat[i * size + j];
        }
    }
    return board;
}

void handleGenerate(int size, int difficulty) {
    Cfg cfg = makeCfg(size);
    vector<vector<int>> puzzle = genPuzzle(cfg, difficulty);
    
    vector<int> flat;
    for (int i = 0; i < size; i++) {
        for (int j = 0; j < size; j++) {
            flat.push_back(puzzle[i][j]);
        }
        
    }
    
    cout << "{\"status\":\"ok\",\"puzzle\":";
    output1DBoard(flat);
    cout << "}";
}

void handleHint(int size, const vector<int>& board, int row, int col) {
    Cfg cfg = makeCfg(size);
    vector<vector<int>> board2d = flat1DTo2D(board, size);
    
    int hint = getHint(board2d, cfg, row, col);
    
    cout << "{\"status\":\"ok\",\"hint\":" << hint << "}";
}

void handleValidate(int size, const vector<int>& board) {
    Cfg cfg = makeCfg(size);
    vector<vector<int>> board2d = flat1DTo2D(board, size);
    
    bool valid = isValidColor(board2d, cfg);
    bool complete = isDone(board2d, cfg);
    cout << "{\"status\":\"ok\",\"valid\":" << (valid ? "true" : "false");
    cout << ",\"complete\":" << (complete ? "true" : "false") << "}";
}

void handleSolve(int size, const vector<int>& board) {
    Cfg cfg = makeCfg(size);
    vector<vector<int>> board2d = flat1DTo2D(board, size);
    
    bool success = solve(board2d, cfg);
    
    if (!success) {
        cout << "{\"status\":\"error\",\"message\":\"No solution found\"}";
        return;
    }
    
    vector<int> flat;
    for (int i = 0; i < size; i++) {
        for (int j = 0; j < size; j++) {
            flat.push_back(board2d[i][j]);
        }
    }
    
    cout << "{\"status\":\"ok\",\"solution\":";
    output1DBoard(flat);
    cout << "}";
}

string trim(const string& str) {
    size_t first = str.find_first_not_of(" \t\n\r");
    if (first == string::npos) return "";
    size_t last = str.find_last_not_of(" \t\n\r");
    return str.substr(first, last - first + 1);
}

int extractInt(const string& json, const string& key) {
    string searchKey = "\"" + key + "\"";
    size_t pos = json.find(searchKey);
    if (pos == string::npos) return -1;
    
    pos = json.find(":", pos);
    if (pos == string::npos) return -1;
    
    string numStr = "";
    for (size_t i = pos + 1; i < json.size(); i++) {
        char c = json[i];
        if (isdigit(c)) numStr += c;
        else if (numStr.length() > 0) break;
    }
    return numStr.empty() ? -1 : stoi(numStr);
}

string extractString(const string& json, const string& key) {
    string searchKey = "\"" + key + "\"";
    size_t pos = json.find(searchKey);
    if (pos == string::npos) return "";
    
    pos = json.find("\"", pos + searchKey.length());
    if (pos == string::npos) return "";
    
    size_t endPos = json.find("\"", pos + 1);
    if (endPos == string::npos) return "";
    return json.substr(pos + 1, endPos - pos - 1);
}

vector<int> extractArray(const string& json, const string& key) {
    vector<int> result;
    string searchKey = "\"" + key + "\"";
    size_t pos = json.find(searchKey);
    if (pos == string::npos) return result;
    
    pos = json.find("[", pos);
    if (pos == string::npos) return result;
    size_t endPos = json.find("]", pos);
    if (endPos == string::npos) return result;
    
    string arrStr = json.substr(pos + 1, endPos - pos - 1);
    stringstream ss(arrStr);
    string num;
    
    while (getline(ss, num, ',')) {
        num = trim(num);
        if (!num.empty() && isdigit(num[0])) {
            result.push_back(stoi(num));
        }
    }
    
    return result;
}

int main(int argc, char* argv[]) {
    string jsonInput;
    string line;
    while (getline(cin, line)) {
        jsonInput += line;
    }
    
    if (jsonInput.empty()) {
        cout << "{\"status\":\"error\",\"message\":\"No input provided\"}";
        return 1;
    }
    
    try {
        string op = extractString(jsonInput, "op");
        
        if (op == "generate") {
            int size = extractInt(jsonInput, "size");
            int difficulty = extractInt(jsonInput, "difficulty");
            
            if (size < 4 || difficulty < 1 || difficulty > 3) {
                cout << "{\"status\":\"error\",\"message\":\"Invalid parameters\"}";
                return 1;
            }
            
            handleGenerate(size, difficulty);
        }
        else if (op == "hint") {
            int size = extractInt(jsonInput, "size");
            int row = extractInt(jsonInput, "row");
            int col = extractInt(jsonInput, "col");
            vector<int> board = extractArray(jsonInput, "board");
            
            if (board.empty() || row < 0 || col < 0) {
                cout << "{\"status\":\"error\",\"message\":\"Invalid parameters\"}";
                return 1;
            }
            handleHint(size, board, row, col);
        }
        else if (op == "validate") {
            int size = extractInt(jsonInput, "size");
            vector<int> board = extractArray(jsonInput, "board");
            
            if (board.empty()) {
                cout << "{\"status\":\"error\",\"message\":\"Invalid parameters\"}";
                return 1;
            }
            
            handleValidate(size, board);
        }
        else if (op == "solve") {
            int size = extractInt(jsonInput, "size");
            vector<int> board = extractArray(jsonInput, "board");
            
            if (board.empty()) {
                cout << "{\"status\":\"error\",\"message\":\"Invalid parameters\"}";
                return 1;
            }
            
            handleSolve(size, board);
        }
        else {
            cout << "{\"status\":\"error\",\"message\":\"Unknown operation: " << op << "\"}";
            return 1;
        }
    }
    catch (const exception& e) {
        cout << "{\"status\":\"error\",\"message\":\"" << e.what() << "\"}";
        return 1;
    }
    
    return 0;
}