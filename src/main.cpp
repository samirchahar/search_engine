#include <iostream>
#include <string>
using namespace std;

void load_documents(const string& folder_path);

int main (){
    cout << "Search Engine Starting..." << endl;

    load_documents("../data/documents");
    
    return 0;
}