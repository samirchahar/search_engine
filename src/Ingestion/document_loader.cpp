#include <iostream>
#include <fstream>
#include <string>
#include <filesystem>

using namespace std;
namespace fs = filesystem;

// This function reads all .txt files from the given folder
void load_documents(const string& folder_path) {
    for (const auto& entry : fs::directory_iterator(folder_path)) {

        // Check if the file extension is .txt
        if (entry.path().extension() == ".txt") {

            ifstream file(entry.path());
            string line;

            cout << "\n--- Reading: "
                 << entry.path().filename()
                 << " ---" << endl;

            // Read file line by line
            while (getline(file, line)) {
                cout << line << endl;
            }

            file.close();
        }
    }
}
