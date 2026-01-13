#ifndef DOCUMENT_LOADER_H
#define DOCUMENT_LOADER_H

#include <string>
#include <vector>

using namespace std;

class DocumentLoader {
    public:
    //this class loads all .txt files from a folder.
    vector<string> loadDocuments(const string& folderPath);
};

#endif