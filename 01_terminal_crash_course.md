# Terminal Crash Course

## Navigation
* List the contents of your current directory
    ```bash
    ls
    ```
* List the all contents in your current directory including hidden files
    ```bash
    ls -a
    ```
* To open the current folder in GUI
    ```bash
    start .
    ```
* To open the parent folder of the current folder in GUI
    ```bash
    start ..
    ```
* To find the contents of a directory/folder inside the current directory
    ```bash
    ls <directory name / folder name>
    ```
* To open the directory/folder inside the current directory in GUI
    ```bash
    start <director name / folder name>
    ```
* To find the contents of a directory that is not the current directory or the immediate child of the current directory
    ```bash
    ls <path of the directory>
    ```
* To open the folder that is not the current directory or the immediate child of the current directory
    ```bash
    start <path of the directory>
    ```
* To find the current directory path
    pwd represents "print working directory"
    ```bash
    pwd
    ``` 
* To make an immediate child folder as the current working directory
    ```bash
    cd <name of the child folder>
    ```
* To make the parent folder as the current working directory
    ```bash
    cd ..
    ```
* To mkae a folder that is not immediate parent or child of the current directory, but present in the same folder chain as the current working directory
    ```bash
    cd <relative or absolute path of the folder>
    ```
* To make a folder that is not present in the folder chain of the current folder as the current working directory
    ```bash
    cd <absolute path of the folder>
    ```

## Creating Files and Folders
* Creating a file (if you don't want the file to have any extension, you don't have to mention it, but generally  that is not the case.)
    ```bash
    touch <file name with extension>
    ```

    examples:
    ```bash
    # for creating a single file
    touch new_file.txt

    # for creating multiple files
    touch new_file_01.txt new_file_02.txt

    # for creating a file with file name having spaces
    touch "new file"
    ```
    * The file(s) created will be present in the current working directory
    * To create file(s) in some other directory which is not the current directory
    ```bash
    touch <relation filepath / absolute filepath>
    ```
* Create a new folder
    ```bash
    mkdir <folder name>
    ```

    examples:
    ```bash
    # For creating a single folder
    mkdir new_folder

    # For creating multile folders at a time
    mkdir new_folder_01 new_folder_02

    # For creating a folder with folder name having spaces
    mkdir "new folder"

    # Similarly, you can create multiple folders with folder names having spaces and no spaces
    mkdir "new folder 01" new_folder_02 "new_folder_03"
    # All the above 3 folders will be created. Even though new_folder_03 does not have any spaces, it will still workout
    ```

## Deleting Files and Folders
*** Deleting files and folders using the below commands is permenant, and you won't get the deleted items back. So, be careful ***
* Deleting a file that is present in the current working directory
    ```bash
    rm <filename with extension (if exists)>
    ```

    examples:
    ```bash
    # Deleting a file that is not present in th curent working directory
    rm <full file path or relation file path>

    # Deleting multiple files in the current working directory
    rm <filename_01> <filename_02> "<filename 03 (if the filename has spaces)>"

    # For deleting multiple files in different scenarios
    rm filename_01 "file name 02" newfolder/filename03 "new folder/filename 04" "newfolder/filename05
    ```

* Deleting a folder that is present in the current working directory
    ```bash
    rm -rf <folder name>
    # rf stands for recursive force
    ```

    examples:
    ```bash
    # Deleting a folder that is not present in th curent working directory
    rm -rf <full folder path or relation folder path>

    # Deleting multiple folders in the current working directory
    rm -rf <folder_name_01> <folder_name_02> "<folder name 03 (if the folder name has spaces)>"

    # For deleting multiple folders in different scenarios
    rm -rf folder_name_01 "folder name 02" newfolder/folder03 "new folder/folder 04" "newfolder/folder05"
    ```