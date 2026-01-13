#include <iostream>
#include "Ingestion/document_loader.h"

using namespace std;

int main (){
    DocumentLoader loader;
    vector<string> docs = loader.loadDocuments("data/documents");
    cout << "Search Engine Starting..." << endl;
    cout << "Loaded documents: " << docs.size() << endl;

    for (int i=0; i<docs.size(); i++){
        cout << "Document " << i+1 << ":\n";
        cout << docs[i] << "\n\n";
    }

    return 0;
}