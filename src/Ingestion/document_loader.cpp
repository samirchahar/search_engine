#include "document_loader.h"
#include <filesystem>
#include <fstream>

using namespace std;
namespace fs = filesystem;

//here, loadDocuments function belongs to DocumentLoader class
vector<string> DocumentLoader::loadDocuments(const string& folderPath){
    vector<string> documents;

    //now loop through all the files in the folder
    for (const auto& entry : fs::directory_iterator(folderPath)){
        //only process the .txt files now
        if (entry.path().extension() == ".txt"){
            ifstream file (entry.path());
            string content, line;
            //read the file line by line now
            while (getline(file, line)){
                content += line + " "; //put it into content
            }
            file.close(); //release system resources
            documents.push_back(content); //pushback into documents 
        }
    }
    return documents; //has all the lines 
}
