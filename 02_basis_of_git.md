# Git Repository

## What is Git Repository (Repo)?
A git repo is a workspace that tracks and manages files within a folder.

## Git Status
> git status

<code>git status</code> gives information on the current status of a git repository and its contents

## Git init
>git init

Use <code>git init</code> to create a new git repository.
* Before we can do anything git-related, we must initialize a git repo first.
* This is something you do once per project. Intialize the repo in the top level folder that contains your project.

⚠️ **DO NOT INIT A REPO INSIDE OF A REPO!**
* Before running <code>git init</code>, use <code>git status</code> to verify that you are not currently inside a git repo.

## Commit

### The Basic Git Workflow

<br><img src="../src/img/basic_git_workflow.png" width=500><br>

* A commit is a checkpoint in time that has information of changes in our repository.
* It is different from saving the files
* A change happens when you save the updated files
* To create a checkpoint for these changes, we have to commit the changes.
* It is a two step process (git add, git commit)
* This two step process allows us commit specific changes that we want to have in a particular checkpoint/commit rather than committing all the changes that happened in the project till then (you can also commit all the changes that happened in the project till then, but it provides this flexibility of committing specific changes.)

### Staging changing with Git add
>git add

* We add <code>git add</code> command to stage changes to be committed.
* It is the way of telling, "please include these changes in our next commit"

#### Example
* Let's say, we have 10 files in our project
* We initialized the project with <git init> and we can see that we initialized the repo using <git status>
* The filenames of these 10 files are: a.txt, b.txt, c.txt, d.txt, e.txt, f.txt, g.txt, h.txt, i.txt, j.txt
* we made some changes in a.txt, b.txt, c.txt, d.txt, e.txt
* The changes done in a.txt, b.txt are related to each other, that means we can look at them in a group
* And the changes done in the rest 3 files (c.txt, d.txt, e.txt) are different from the first two files, but these three changes are also related to each other and grouped together.
* Using <git status> command now (after doing the changes in these 5 files) will give the following result
```terminal
On branch master
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   a.txt
        modified:   b.txt
        modified:   c.txt
        modified:   d.txt
        modified:   e.txt

no changes added to commit (use "git add" and/or "git commit -a")
```
* Now, we can make two commits, for committing changes in all the 5 files
* In the first commit, we will commit the changes in the a.txt and b.txt using the following commands
> git add a.txt

> git add b.txt

> git commit -m "custom message for changes in the first two files"

* In the second commit, we will commit the changes in the c.txt, d.txt, and e.txt using the following commands
* We can either add the files in the staging area individually, as we previously.
* Or we can add all the 3 files at a time as shown in the below command, with space separations between the file names.
>git add c.txt d.txt e.txt

> git commit -m "custom message for changes in the next three files"

### Git Commit
>git commit -m "my message"


* Running <code>git commit</code> will commit all staged changes. It also opens up a text editor(vim) and prompts you for a commit message. This can be overwhelming when you're starting out, so instead you can use <code>git commit</code>
* When making a commit, we need to provide a commit message that summarizes the changes and work snapshotted in the commit.
* if you want to commit all the changes in the repo (like updated files, new files, deleted files etc.), without typing all the names of the files that has got these changes. We can simply use the below command
> git add .
* This command will add all the files that has got some changes into the staging area, it won't touch the files that has not changes.
#### Example
* In the previous files with filenames starting from a.txt to j.txt
* Let's make some changes in the files a.txt and b.txt, and check the status using <code>git status</code>
```terminal
On branch master
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   a.txt
        modified:   b.txt

no changes added to commit (use "git add" and/or "git commit -a")
```
* Now, to add all the files that has got some changes (in this case the two files a.txt and b.txt), we will use the following command
> git add .
* Let's check what all files are present in the staging area
> git status
```terminal
On branch master
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        modified:   a.txt
        modified:   b.txt
```
* Finally, we will commit the changes with a commit message that summarizes the changes in the files
> git commit -m "custom message summarizing the changes"

## Shortcut to commit all the changes
Use the below command to add all the changes and commit with a commit message
> git commit -a -m "my message"
The above command will not add the untracked files

### Git log
> git log
* This command will retreive information of all the commits in the repo
* It shows information about each commit by displaying the following categories of information
    * commit hash (we'll learn about it later)
    * who committed it (name of the author)
    * when did they commit it (datetime of the commit)
    * message for the commit
* To get out of git log results, click "q" which means quit.

### Exercise

[Click Here](https://www.notion.so/Committing-Basics-Exercise-3dc1ef1873ce45e68cedd2265710d7d8)
