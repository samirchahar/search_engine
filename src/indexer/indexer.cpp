// src/indexer/indexer.cpp
// Inverted index with positional tracking.
// Tracks word positions per document to support phrase search.
//
// Input protocol:
//   ADD <docid> <word1> <word2> ... <wordN>   — index a document
//   SEARCH <word1> <word2> ...                — keyword search
//   PHRASE <word1> <word2> ...                — phrase search
//   END                                       — exit

#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <algorithm>

using namespace std;

// word -> { docid -> [positions] }
unordered_map<string, unordered_map<string, vector<int>>> inv_index;

// Convert a word to lowercase
string to_lower(const string& word) {
    string result = word;
    transform(result.begin(), result.end(), result.begin(), ::tolower);
    return result;
}

// Add a document to the index
void add_document(const string& docid, const vector<string>& words) {
    for (int i = 0; i < (int)words.size(); i++) {
        string word = to_lower(words[i]);
        inv_index[word][docid].push_back(i);  // store position
    }
}

// Keyword search: return docs containing ALL query words
// Score = total number of occurrences across all query words
void search(const vector<string>& query_words) {
    unordered_set<string> candidates;
    bool first = true;

    for (const auto& raw_word : query_words) {
        string word = to_lower(raw_word);

        if (inv_index.find(word) == inv_index.end()) {
            cout << "RESULTS 0" << endl;
            return;
        }

        if (first) {
            for (const auto& pair : inv_index[word]) {
                candidates.insert(pair.first);
            }
            first = false;
        } else {
            unordered_set<string> intersection;
            for (const auto& docid : candidates) {
                if (inv_index[word].count(docid)) {
                    intersection.insert(docid);
                }
            }
            candidates = intersection;
        }
    }

    // Score = total frequency across all query words
    unordered_map<string, int> scores;
    for (const auto& docid : candidates) {
        int score = 0;
        for (const auto& raw_word : query_words) {
            string word = to_lower(raw_word);
            score += inv_index[word][docid].size();
        }
        scores[docid] = score;
    }

    // Sort by score descending
    vector<pair<string, int>> sorted_results(scores.begin(), scores.end());
    sort(sorted_results.begin(), sorted_results.end(),
        [](const auto& a, const auto& b) { return a.second > b.second; });

    cout << "RESULTS " << sorted_results.size() << endl;
    for (const auto& pair : sorted_results) {
        cout << pair.first << " " << pair.second << endl;
    }
}

// Phrase search: return docs where all words appear consecutively
void phrase_search(const vector<string>& query_words) {
    if (query_words.empty()) {
        cout << "RESULTS 0" << endl;
        return;
    }

    // Start with docs containing the first word
    string first_word = to_lower(query_words[0]);
    if (inv_index.find(first_word) == inv_index.end()) {
        cout << "RESULTS 0" << endl;
        return;
    }

    // For each candidate doc, check if words appear consecutively
    unordered_map<string, int> scores;

    for (const auto& pair : inv_index[first_word]) {
        const string& docid = pair.first;
        const vector<int>& first_positions = pair.second;

        // For each starting position of the first word
        for (int start_pos : first_positions) {
            bool match = true;

            // Check each subsequent word appears at start_pos + offset
            for (int i = 1; i < (int)query_words.size(); i++) {
                string word = to_lower(query_words[i]);

                if (inv_index.find(word) == inv_index.end() ||
                    inv_index[word].find(docid) == inv_index[word].end()) {
                    match = false;
                    break;
                }

                const vector<int>& positions = inv_index[word][docid];
                int expected_pos = start_pos + i;

                // Check if expected position exists
                if (find(positions.begin(), positions.end(), expected_pos) == positions.end()) {
                    match = false;
                    break;
                }
            }

            if (match) {
                scores[docid]++;
            }
        }
    }

    // Sort by score descending
    vector<pair<string, int>> sorted_results(scores.begin(), scores.end());
    sort(sorted_results.begin(), sorted_results.end(),
        [](const auto& a, const auto& b) { return a.second > b.second; });

    cout << "RESULTS " << sorted_results.size() << endl;
    for (const auto& pair : sorted_results) {
        cout << pair.first << " " << pair.second << endl;
    }
}

int main() {
    string line;
    while (getline(cin, line)) {
        if (line.empty()) continue;

        istringstream iss(line);
        string command;
        iss >> command;

        if (command == "ADD") {
            string docid;
            iss >> docid;
            vector<string> words;
            string word;
            while (iss >> word) {
                words.push_back(word);
            }
            add_document(docid, words);

        } else if (command == "SEARCH") {
            vector<string> query_words;
            string word;
            while (iss >> word) {
                query_words.push_back(word);
            }
            search(query_words);

        } else if (command == "PHRASE") {
            vector<string> query_words;
            string word;
            while (iss >> word) {
                query_words.push_back(word);
            }
            phrase_search(query_words);

        } else if (command == "END") {
            break;
        }
    }
    return 0;
}